import logging
import re
import unicodedata
import requests
from datetime import datetime, timezone

# ==================== XỬ LÝ CHUỖI ====================

def _remove_accents(text):
    """Bỏ dấu tiếng Việt khỏi chuỗi."""
    normalized = unicodedata.normalize("NFD", text)
    no_accents = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    no_accents = no_accents.replace("đ", "d").replace("Đ", "D")
    return no_accents


def slugify_channel_name(subject_code, display_name=None):
    """Chuyển tên môn học thành tên kênh hợp lệ cho Discord.

    Nếu có display_name: format 'viết-tắt-tên-csc10014'
        Ví dụ: ('CSC10014', 'Nhập Môn Trí Tuệ Nhân Tạo') → 'nmttnt-csc10014'
    Nếu không có display_name: chỉ dùng subject_code
        Ví dụ: ('CSC10014', None) → 'csc10014'
    """
    code_slug = _remove_accents(subject_code).lower()
    code_slug = re.sub(r'[^a-z0-9]+', '-', code_slug).strip('-')

    if display_name:
        abbr = abbreviate_name(display_name)
        if abbr:
            return f"{abbr.lower()}-{code_slug}"

    return code_slug if code_slug else "general"


def extract_display_name(fullname):
    """Trích tên tiếng Việt từ fullname của Moodle API.

    Ví dụ:
        'CQ2526HK2_CSC10014_CQ2024/2 - Nhập Môn Trí Tuệ Nhân Tạo'
            → 'Nhập Môn Trí Tuệ Nhân Tạo'
        'CQ2526HK2_CSC10014_CQ2024/2'
            → None (không có tên TV)
    """
    if not fullname:
        return None

    # Pattern: tìm phần sau dấu " - " (tên tiếng Việt)
    match = re.search(r'\s*-\s+(.+)$', fullname)
    if match:
        name = match.group(1).strip()
        # Bỏ qua nếu tên chỉ chứa mã lớp (CQ..., CLC..., VP...)
        if re.match(r'^(CQ|CLC|VP|CTTT)\d', name):
            return None
        return name if name else None

    return None


def abbreviate_name(display_name):
    """Tạo viết tắt từ tên tiếng Việt (lấy chữ cái đầu mỗi từ).

    Ví dụ:
        'Nhập Môn Trí Tuệ Nhân Tạo' → 'NMTTNT'
        'Toán Rời Rạc'              → 'TRR'
        'Lập Trình Hướng Đối Tượng' → 'LTHDT'
    """
    if not display_name:
        return None

    # Bỏ dấu trước khi lấy chữ cái đầu
    clean = _remove_accents(display_name)
    words = clean.split()
    if not words:
        return None

    abbr = "".join(w[0].upper() for w in words if w and w[0].isalpha())
    return abbr if abbr else None

def extract_subject(category):
    """Trích xuất tên môn học từ trường CATEGORIES của ICS.
    Hỗ trợ nhiều format:
        'CQ2526HK2_CSC10014_CQ2024/2' → 'CSC10014'
        'CSC10014'                     → 'CSC10014'
        'Tư duy tính toán - CQ2024/2'  → 'Tư duy tính toán'
        'Toán Rời Rạc'                 → 'Toán Rời Rạc'
        ''  hoặc None                  → 'General'
    """
    if not category or category.strip() == "":
        return "General"

    # Pattern 1: Mã môn chuẩn FIT dạng _CSC10014_ (3-4 chữ + 5 số, bao quanh bởi _)
    match = re.search(r'_([A-Z]{2,5}\d{4,6})_', category)
    if match:
        return match.group(1)

    # Pattern 2: Mã môn đứng riêng hoặc đầu/cuối chuỗi (CSC10014, MTH00003, ...)
    # Bỏ qua các đuôi khóa học như CQ, CLC, VP, CTTT
    matches = re.finditer(r'\b([A-Z]{2,5}\d{4,6})\b', category)
    for match in matches:
        code = match.group(1)
        if not code.startswith(('CQ', 'CLC', 'VP', 'CTTT')):
            return code

    # Pattern 3: Không tìm được mã môn → dùng nguyên category làm tên
    # Xóa các đuôi định dạng khóa học (ví dụ: " - CQ2024/2")
    clean_cat = re.sub(r'\s*-\s*(CQ|CLC|VP|CTTT)\d{4}.*$', '', category)
    return clean_cat.strip()

# ==================== PARSE ICS ====================

def fetch_and_parse_events(calendar_url):
    """Fetch ICS and parse events. Returns list of event dicts or None on failure."""
    try:
        logging.info("Fetching calendar ICS file...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(calendar_url, headers=headers, timeout=15)

        if response.status_code != 200:
            logging.error(f"Failed to load calendar. HTTP Status: {response.status_code}")
            return None

        ics_data = response.text
    except Exception as e:
        logging.error(f"Error fetching calendar: {e}")
        return None

    events = []
    vevent_blocks = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', ics_data, re.DOTALL)

    for block in vevent_blocks:
        uid_match = re.search(r'\nUID:(.*?)\n', block)
        summary_match = re.search(r'\nSUMMARY:(.*?)\n', block)
        dtend_match = re.search(r'\nDTEND:(.*?)\n', block)
        cat_match = re.search(r'\nCATEGORIES:(.*?)\n', block)

        if uid_match and summary_match and dtend_match:
            uid = uid_match.group(1).strip()
            summary = summary_match.group(1).strip()
            dtend_str = dtend_match.group(1).strip()
            category = cat_match.group(1).strip() if cat_match else "General"

            subject = extract_subject(category)

            try:
                dtend = datetime.strptime(dtend_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                events.append({
                    "uid": uid,
                    "summary": summary,
                    "deadline": dtend,
                    "subject": subject
                })
            except Exception as e:
                logging.error(f"Error parsing date {dtend_str}: {e}")

    logging.info(f"Found {len(events)} events in calendar.")
    return events

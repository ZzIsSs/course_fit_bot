import logging
import re
import unicodedata
import requests
from datetime import datetime, timezone

# ==================== XỬ LÝ CHUỖI ====================

def slugify_channel_name(name):
    """Chuyển tên môn học thành tên kênh hợp lệ cho Discord.
    Bỏ dấu tiếng Việt, chuyển thường, thay ký tự đặc biệt bằng '-'.
    Ví dụ: 'Toán Rời Rạc' → 'toan-roi-rac'
           'CSC10014' → 'csc10014'
    """
    # Bỏ dấu tiếng Việt
    normalized = unicodedata.normalize("NFD", name)
    no_accents = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    no_accents = no_accents.replace("đ", "d").replace("Đ", "D")
    # Chuyển thường, thay ký tự đặc biệt bằng '-'
    slug = no_accents.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug if slug else "general"

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

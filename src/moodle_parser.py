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
        'Phương pháp lập trình hướng đối tượng - CQ2024/3'
            → 'Phương pháp lập trình hướng đối tượng'
    """
    if not fullname:
        return None

    # Xóa các đuôi mã lớp (như - CQ2024/3) ở cuối chuỗi
    clean_name = re.sub(r'\s*-\s*(CQ|CLC|VP|CTTT)\d{4}.*$', '', fullname).strip()

    # Nếu chuỗi còn lại có dạng "Mã Môn - Tên Môn"
    if ' - ' in clean_name:
        parts = clean_name.split(' - ')
        # Trả về phần sau cùng (giả định tên môn thường nằm sau mã môn)
        return parts[-1].strip()

    return clean_name if clean_name else None


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


def get_current_semester(dt=None):
    """Tính toán học kỳ và năm học theo thời gian thực (hoặc datetime truyền vào).

    Quy tắc nghiệp vụ:
    - Tháng 9 đến Tháng 1: Học kỳ 1 (HK1). (Nếu tháng 1: thuộc năm học bắt đầu từ năm trước).
    - Tháng 2 đến Tháng 6: Học kỳ 2 (HK2).
    - Tháng 7 đến Tháng 8: Học kỳ Hè (HK3 / Hè).

    Returns:
        dict: {
            'semester': 1 | 2 | 3,
            'academicYear': '2026 - 2027',
            'academic_year': '2026 - 2027',
            'label': 'Học kỳ 1 (2026 - 2027)'
        }
    """
    if dt is None:
        dt = datetime.now()
    elif isinstance(dt, str):
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d/%m/%Y %H:%M', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S'):
            try:
                dt = datetime.strptime(dt.split('+')[0].split('.')[0], fmt)
                break
            except ValueError:
                continue
        if isinstance(dt, str):
            dt = datetime.now()

    month = dt.month
    year = dt.year

    if month >= 9:
        semester = 1
        start_year = year
        end_year = year + 1
        label = f"Học kỳ 1 ({start_year} - {end_year})"
    elif month == 1:
        semester = 1
        start_year = year - 1
        end_year = year
        label = f"Học kỳ 1 ({start_year} - {end_year})"
    elif 2 <= month <= 6:
        semester = 2
        start_year = year - 1
        end_year = year
        label = f"Học kỳ 2 ({start_year} - {end_year})"
    else:  # 7 <= month <= 8
        semester = 3
        start_year = year - 1
        end_year = year
        label = f"Học kỳ Hè ({start_year} - {end_year})"

    acad_year = f"{start_year} - {end_year}"
    return {
        "semester": semester,
        "academicYear": acad_year,
        "academic_year": acad_year,
        "label": label
    }


def parse_moodle_semester_code(raw_code):
    """Bóc tách thông tin học kỳ, năm học, và khóa học từ chuỗi mã Moodle.

    Hỗ trợ linh hoạt:
    - Tiền tố: CQ, CLC, VP, CTTT, KTT, VHVL hoặc không có tiền tố.
    - Định dạng năm học: 2425HK1, 2024_2025_1, 2024_2025_HK1, 2425_1, 2425-2, v.v.
    - Mã khóa học / lớp: CQ2024/1, CLC2024/2, 2024/1...
    """
    if not raw_code:
        return None

    prefix_match = re.search(r'\b(CQ|CLC|VP|CTTT|KTT|VHVL)', raw_code)
    prefix = prefix_match.group(1) if prefix_match else None

    # Pattern 1: Năm 4 chữ số: 2024_2025_1 hoặc 2024_2025_HK1 hoặc 2024-2025-2
    p1 = re.search(r'(?:CQ|CLC|VP|CTTT|KTT|VHVL)?_?(20\d{2})[_\-](20\d{2})[_\-]?(?:HK)?([123])', raw_code, re.IGNORECASE)
    # Pattern 2: Năm 2 chữ số với chữ HK: 2425HK1 hoặc CQ2425HK2
    p2 = re.search(r'(?:CQ|CLC|VP|CTTT|KTT|VHVL)?_?(\d{2})(\d{2})\s*HK\s*([123])', raw_code, re.IGNORECASE)
    # Pattern 3: Năm 2 chữ số với ký tự phân cách: 2425_1 hoặc 2425-2
    p3 = re.search(r'(?:CQ|CLC|VP|CTTT|KTT|VHVL)?_?(\d{2})(\d{2})[_\-](?:HK)?([123])', raw_code, re.IGNORECASE)

    start_year = None
    end_year = None
    hk = None

    if p1:
        start_year = int(p1.group(1))
        end_year = int(p1.group(2))
        hk = int(p1.group(3))
    elif p2:
        start_year = 2000 + int(p2.group(1))
        end_year = 2000 + int(p2.group(2))
        hk = int(p2.group(3))
    elif p3:
        start_year = 2000 + int(p3.group(1))
        end_year = 2000 + int(p3.group(2))
        hk = int(p3.group(3))

    if not start_year or not hk:
        return None

    # Tìm cohort year nếu có (vd: CQ2024/1 hoặc CLC2024/2 hoặc 2024/1)
    cohort_match = re.search(r'(?:CQ|CLC|VP|CTTT|KTT|VHVL)?_?(20\d{2})/\d+', raw_code)
    cohort_year = int(cohort_match.group(1)) if cohort_match else None

    semester_index = None
    if cohort_year and hk in (1, 2):
        ky = (start_year - cohort_year) * 2 + hk
        if ky >= 1:
            semester_index = ky

    label = f"Học kỳ {hk} ({start_year} - {end_year})" if hk in (1, 2) else f"Học kỳ Hè ({start_year} - {end_year})"

    return {
        "prefix": prefix,
        "academic_year": f"{start_year} - {end_year}",
        "academicYear": f"{start_year} - {end_year}",
        "semester": hk,
        "semester_label": label,
        "label": label,
        "cohort_year": cohort_year,
        "semester_index": semester_index
    }


def extract_semester_index(raw_code):
    """Tính 'kì thứ mấy' (học kỳ riêng của sinh viên, kì 1 = học kỳ đầu tiên nhập học)
    từ chuỗi mã gốc Moodle.

    Hỗ trợ linh hoạt các tiền tố (CQ, CLC, VP, CTTT...) và các dạng mã năm học
    (2425HK1, 2024_2025_1...). Trả về None nếu không đủ dữ liệu tính toán.
    """
    info = parse_moodle_semester_code(raw_code)
    if info and info.get('semester_index'):
        return info['semester_index']
    return None


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
                    "subject": subject,
                    "category_raw": category,
                })
            except Exception as e:
                logging.error(f"Error parsing date {dtend_str}: {e}")

    logging.info(f"Found {len(events)} events in calendar.")
    return events

import re
from datetime import datetime


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

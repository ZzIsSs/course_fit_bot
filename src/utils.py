from datetime import timezone, datetime


def ensure_tz(dt):
    """Đảm bảo datetime có timezone (mặc định UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def parse_due_time(text, local_tz):
    """Parse chuỗi hạn chót người dùng nhập, hỗ trợ có hoặc không có giờ.

    Định dạng hỗ trợ (giờ theo local_tz):
        'dd/mm/yyyy HH:MM'  'dd/mm HH:MM'   (có giờ)
        'dd/mm/yyyy'        'dd/mm'         (không giờ -> mặc định 23:59)

    Trả về datetime UTC, hoặc None nếu không parse được.
    """
    text = text.strip()
    now_local = datetime.now(local_tz)
    formats = (
        ("%d/%m/%Y %H:%M", True, True),
        ("%d/%m %H:%M", False, True),
        ("%d/%m/%Y", True, False),
        ("%d/%m", False, False),
    )
    for fmt, has_year, has_time in formats:
        try:
            dt = datetime.strptime(text, fmt)
            if not has_year:
                dt = dt.replace(year=now_local.year)
            if not has_time:
                dt = dt.replace(hour=23, minute=59)
            return dt.replace(tzinfo=local_tz).astimezone(timezone.utc)
        except ValueError:
            continue
    return None

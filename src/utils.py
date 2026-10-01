from datetime import timezone, datetime
from typing import Optional


def ensure_tz(dt: datetime) -> datetime:
    """Đảm bảo datetime có timezone (mặc định UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def parse_due_time(text: str, local_tz: timezone) -> Optional[datetime]:
    """Parse chuỗi hạn chót người dùng nhập, hỗ trợ có hoặc không có giờ.

    Định dạng hỗ trợ (giờ theo local_tz):
        'dd/mm/yyyy HH:MM'  'dd/mm HH:MM'   (có giờ)
        'dd/mm/yyyy'        'dd/mm'         (không giờ -> mặc định 23:59)

    Xử lý an toàn:
        - Năm nhuận: Tránh strptime fallback về 1900 làm lỗi 29/02.
        - Year rollover: Nhập ngày đầu năm (T1, T2) vào cuối năm (T10-T12)
          sẽ tự động tính cho năm kế tiếp.

    Trả về datetime UTC, hoặc None nếu không parse được.
    """
    if not text or not isinstance(text, str):
        return None

    clean_text = " ".join(text.strip().split())
    if not clean_text:
        return None

    now_local = datetime.now(local_tz)
    formats = (
        ("%d/%m/%Y %H:%M", True, True),
        ("%d/%m %H:%M", False, True),
        ("%d/%m/%Y", True, False),
        ("%d/%m", False, False),
    )

    for fmt, has_year, has_time in formats:
        # Nếu không có năm, thử với năm hiện tại; nếu cuối năm thì cho phép thử năm sau
        candidate_years = [now_local.year]
        if not has_year and now_local.month >= 10:
            candidate_years.append(now_local.year + 1)

        for y in candidate_years:
            try:
                parse_text = clean_text
                parse_fmt = fmt
                if not has_year:
                    # Tách phần ngày và giờ, chèn năm candidate vào trước khi parse
                    # để tránh strptime ngầm định dùng năm 1900 (gây lỗi ngày 29/02)
                    parts = parse_text.split()
                    date_part = parts[0]
                    time_part = f" {parts[1]}" if len(parts) > 1 else ""
                    parse_text = f"{date_part}/{y}{time_part}"
                    parse_fmt = fmt.replace("%d/%m", "%d/%m/%Y")

                dt = datetime.strptime(parse_text, parse_fmt)
                if not has_time:
                    dt = dt.replace(hour=23, minute=59, second=0, microsecond=0)

                dt_aware = dt.replace(tzinfo=local_tz)

                # Nếu không nhập năm, và thời điểm parse rơi vào quá khứ trong khi đang cuối năm
                # và vẫn còn candidate năm sau thì nhường cho vòng lặp kế tiếp
                if not has_year and dt_aware < now_local and y == now_local.year and now_local.month >= 10 and dt.month <= 3:
                    continue

                return dt_aware.astimezone(timezone.utc)
            except (ValueError, IndexError):
                continue

    return None

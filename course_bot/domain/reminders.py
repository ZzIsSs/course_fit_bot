"""Quyết định loại thông báo deadline cần gửi (thuần, không I/O)."""
from datetime import timedelta

NEW = "NEW"
THREE_DAYS = "3_DAYS"
ONE_DAY = "1_DAY"

# Loại thông báo -> cột cờ trong bảng deadlines
NOTIFIED_FIELDS = {NEW: "notified_new", THREE_DAYS: "reminded_3d", ONE_DAY: "reminded_1d"}


def decide_reminder(deadline, due_time, now):
    """Chọn loại thông báo cho deadline, hoặc None nếu không cần gửi.

    Mỗi lần chạy chỉ gửi tối đa 1 loại, theo thứ tự NEW -> 3_DAYS -> 1_DAY.
    Vì vậy deadline mới mà còn < 1 ngày sẽ nhận NEW, rồi 3_DAYS, rồi 1_DAY
    ở các lần chạy kế tiếp.

    Args:
        deadline: dòng deadline trong DB (cần notified_new, reminded_3d, reminded_1d).
        due_time: hạn chót (datetime có timezone).
        now: thời điểm hiện tại (datetime có timezone).
    """
    time_left = due_time - now
    if time_left.total_seconds() < 0:
        return None
    if not deadline['notified_new']:
        return NEW
    if time_left <= timedelta(days=3) and not deadline['reminded_3d']:
        return THREE_DAYS
    if time_left <= timedelta(days=1) and not deadline['reminded_1d']:
        return ONE_DAY
    return None

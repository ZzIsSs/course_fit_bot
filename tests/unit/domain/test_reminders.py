"""Unit test cho domain/reminders.py: khung thời gian nhắc deadline."""
from datetime import datetime, timedelta, timezone

import pytest

from course_bot.domain.reminders import (
    NEW, NOTIFIED_FIELDS, ONE_DAY, THREE_DAYS, decide_reminder,
)

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)


def row(notified_new=False, reminded_3d=False, reminded_1d=False):
    return {"notified_new": notified_new, "reminded_3d": reminded_3d, "reminded_1d": reminded_1d}


ALL_SENT = row(True, True, True)
NEW_SENT = row(True)
THREE_SENT = row(True, True)


@pytest.mark.parametrize("deadline, left, expected", [
    # Chưa báo mới: luôn NEW (miễn chưa quá hạn), kể cả khi còn rất ít thời gian
    (row(), timedelta(days=30), NEW),
    (row(), timedelta(hours=1), NEW),
    (row(), timedelta(0), NEW),
    # Biên 3 ngày: <= 3 ngày mới nhắc
    (NEW_SENT, timedelta(days=3, seconds=1), None),
    (NEW_SENT, timedelta(days=3), THREE_DAYS),
    (NEW_SENT, timedelta(days=1, hours=1), THREE_DAYS),
    # Chưa nhắc 3 ngày mà đã < 1 ngày: vẫn nhắc 3_DAYS trước (1 loại mỗi lần chạy)
    (NEW_SENT, timedelta(hours=2), THREE_DAYS),
    # Biên 1 ngày
    (THREE_SENT, timedelta(days=1, seconds=1), None),
    (THREE_SENT, timedelta(days=1), ONE_DAY),
    (THREE_SENT, timedelta(minutes=5), ONE_DAY),
    # Đã gửi đủ
    (ALL_SENT, timedelta(hours=1), None),
    # Quá hạn: không gửi gì, kể cả khi chưa báo mới
    (row(), -timedelta(seconds=1), None),
    (THREE_SENT, -timedelta(days=2), None),
])
def test_decide_reminder(deadline, left, expected):
    assert decide_reminder(deadline, NOW + left, NOW) == expected


def test_sequence_for_deadline_added_with_less_than_one_day_left():
    """Mô phỏng các lần chạy liên tiếp: NEW -> 3_DAYS -> 1_DAY -> hết."""
    deadline = row()
    due = NOW + timedelta(hours=10)
    sent = []
    for minutes in range(0, 120, 30):
        now = NOW + timedelta(minutes=minutes)
        msg_type = decide_reminder(deadline, due, now)
        if msg_type:
            sent.append(msg_type)
            deadline[NOTIFIED_FIELDS[msg_type]] = True
    assert sent == [NEW, THREE_DAYS, ONE_DAY]


def test_notified_fields():
    assert NOTIFIED_FIELDS == {NEW: "notified_new", THREE_DAYS: "reminded_3d", ONE_DAY: "reminded_1d"}

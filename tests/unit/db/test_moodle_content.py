# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from unittest.mock import patch

from course_bot.db.repositories.moodle_content import get_known_modules_for_course


def test_get_known_modules_timezone():
    # Giả lập 1 timestamp UTC cụ thể
    expected_epoch = 1727013141  # 2024-09-22 13:52:21 UTC
    dt_utc = datetime.fromtimestamp(expected_epoch, tz=timezone.utc)
    dt_naive = dt_utc.replace(tzinfo=None)  # Giống như Postgres timestamp without time zone trả về

    mock_rows = [
        {'lms_module_id': '101', 'time_modified': dt_naive},
        {'lms_module_id': '102', 'time_modified': dt_utc},
        {'lms_module_id': '103', 'time_modified': expected_epoch},
    ]

    with patch('course_bot.db.repositories.moodle_content.fetch_all', return_value=mock_rows):
        result = get_known_modules_for_course(None, 1)

    print("Result:", result)
    assert result['101'] == expected_epoch, f"Expected {expected_epoch}, got {result['101']}"
    assert result['102'] == expected_epoch, f"Expected {expected_epoch}, got {result['102']}"
    assert result['103'] == expected_epoch, f"Expected {expected_epoch}, got {result['103']}"
    print("ALL TESTS PASSED! Naive datetime correctly normalized to UTC.")


if __name__ == '__main__':
    test_get_known_modules_timezone()


def test_recent_announcements_read_forum_discussions():
    """Tab "Bảng tin" đọc forum_discussions (bảng announcements chưa có code nào ghi)."""
    from course_bot.db.repositories.moodle_content import get_recent_announcements_with_course

    with patch('course_bot.db.repositories.moodle_content.fetch_all', return_value=[]) as mock_fetch:
        assert get_recent_announcements_with_course(None, limit=5) == []

    sql = " ".join(mock_fetch.call_args[0][1].split())
    assert "FROM forum_discussions f" in sql
    assert "FROM announcements" not in sql
    # Giữ tên cột cũ cho frontend
    for column in ("AS announcements_id", "AS announcements_name", "AS source_url",
                   "f.created_time", "c.course_name", "AS course_display_name", "f.author"):
        assert column in sql
    assert "discuss.php?d=' || f.lms_discussion_id" in sql
    assert mock_fetch.call_args[0][2] == (5,)

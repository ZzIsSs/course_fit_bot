"""Unit test cho course_bot/db/repositories/deadlines.py (mock fetch_all, không cần DB)."""
from unittest.mock import patch

from course_bot.db.repositories.deadlines import get_tracked_deadlines


def test_get_tracked_deadlines_skips_deadlines_overdue_more_than_3_days():
    with patch("course_bot.db.repositories.deadlines.fetch_all", return_value=[]) as mock_fetch:
        assert get_tracked_deadlines(None) == []

    sql = " ".join(mock_fetch.call_args[0][1].split())
    assert "d.completed = false" in sql
    assert "d.discord_message_id IS NOT NULL" in sql
    assert "d.due_time >= now() - interval '3 days'" in sql

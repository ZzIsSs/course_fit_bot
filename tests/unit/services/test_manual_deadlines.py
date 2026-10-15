# -*- coding: utf-8 -*-
"""Unit tests cho thêm deadline thủ công: services/manual_deadlines.py và các hàm nó dựa vào."""
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from course_bot.core.time_utils import parse_due_time, ensure_tz
from course_bot.domain.messages import sanitize_discord_text
from course_bot.web.routes.discord_interactions import _public, _handle_add_deadline
from course_bot.db.repositories.courses import get_or_create_course
from course_bot.db.repositories.deadlines import insert_deadline_manual
from course_bot.core.time_utils import LOCAL_TZ
from course_bot.services import manual_deadlines as svc


class TestAddDeadlineRefactor(unittest.TestCase):

    def test_parse_due_time_standard(self):
        """Kiểm tra parse định dạng chuẩn đầy đủ ngày giờ và chỉ ngày."""
        res1 = parse_due_time("25/12/2026 23:59", LOCAL_TZ)
        self.assertIsNotNone(res1)
        self.assertEqual(res1.year, 2026)
        self.assertEqual(res1.month, 12)
        self.assertEqual(res1.day, 25)
        # 23:59 GMT+7 -> 16:59 UTC
        self.assertEqual(res1.hour, 16)
        self.assertEqual(res1.minute, 59)

        res2 = parse_due_time("25/12/2026", LOCAL_TZ)
        self.assertIsNotNone(res2)
        # Mặc định 23:59 GMT+7 -> 16:59 UTC
        self.assertEqual(res2.hour, 16)
        self.assertEqual(res2.minute, 59)

    def test_parse_due_time_leap_year(self):
        """Kiểm tra giải quyết triệt để lỗi Leap Year Trap khi nhập 29/02 không có năm."""
        # Giả lập năm hiện tại là 2024 (năm nhuận)
        fake_now = datetime(2024, 2, 1, 10, 0, tzinfo=LOCAL_TZ)
        with patch("course_bot.core.time_utils.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.strptime = datetime.strptime
            
            res = parse_due_time("29/02", LOCAL_TZ)
            self.assertIsNotNone(res)
            self.assertEqual(res.year, 2024)
            self.assertEqual(res.month, 2)
            self.assertEqual(res.day, 29)

    def test_parse_due_time_year_rollover(self):
        """Kiểm tra Year Rollover: nhập ngày tháng 1 vào cuối năm (tháng 12) -> tự nhảy sang năm sau."""
        fake_now = datetime(2026, 12, 28, 10, 0, tzinfo=LOCAL_TZ)
        with patch("course_bot.core.time_utils.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.strptime = datetime.strptime

            res = parse_due_time("05/01 23:59", LOCAL_TZ)
            self.assertIsNotNone(res)
            self.assertEqual(res.year, 2027)
            self.assertEqual(res.month, 1)
            self.assertEqual(res.day, 5)

    def test_sanitize_discord_text(self):
        """Kiểm tra vô hiệu hóa Mention Injection và khoảng trắng thừa."""
        raw = "  @everyone Làm bài tập   nhanh  @here <@&987654>  "
        clean = sanitize_discord_text(raw)
        self.assertNotIn("@everyone", clean)
        self.assertNotIn("@here", clean)
        self.assertIn("@\u200beveryone", clean)
        self.assertIn("@\u200bhere", clean)
        self.assertIn("@\u200b&role", clean)
        self.assertEqual(clean, "@\u200beveryone Làm bài tập nhanh @\u200bhere @\u200b&role")

    def test_public_allowed_mentions(self):
        """Kiểm tra phản hồi public luôn có allowed_mentions rỗng."""
        resp = _public("Nội dung thông báo")
        self.assertEqual(resp["type"], 4)
        self.assertEqual(resp["data"]["allowed_mentions"], {"parse": []})

    def test_insert_deadline_manual_idempotent(self):
        """Kiểm tra cơ chế chống duplicate cấp nghiệp vụ."""
        mock_conn = MagicMock()

        due_time = datetime(2026, 10, 15, 16, 59, tzinfo=timezone.utc)

        # Lần 1: Chưa có bài tập trong DB -> fetch_one trả về None cho check, trả về ID cho insert
        with patch("course_bot.db.repositories.deadlines.fetch_one") as mock_fetch:
            mock_fetch.side_effect = [
                None,                       # check existing -> None
                {"deadlines_id": 101}       # insert -> ID 101
            ]
            res_id = insert_deadline_manual(
                mock_conn, courses_id=1, deadline_name="Bài tập 1",
                lms_deadlines_id="manual-123", due_time=due_time,
                source_url="url", added_by="Nguyen"
            )
            self.assertEqual(res_id, 101)

        # Lần 2: Đã có bài tập cùng môn, tên, hạn chót trong DB -> trả về None (bỏ qua duplicate)
        with patch("course_bot.db.repositories.deadlines.fetch_one") as mock_fetch:
            mock_fetch.return_value = {"deadlines_id": 101}  # check existing -> tìm thấy 101
            res_id = insert_deadline_manual(
                mock_conn, courses_id=1, deadline_name="Bài tập 1",
                lms_deadlines_id="manual-456", due_time=due_time,
                source_url="url", added_by="Nguyen"
            )
            self.assertIsNone(res_id)



class TestManualDeadlineService(unittest.TestCase):
    """Quy tắc chuẩn hoá dùng chung cho Web, Discord và API bên thứ 3."""

    def test_clean_name(self):
        self.assertEqual(svc.clean_name("  Bài <@&1>  @everyone\x00 1 "), "Bài @\u200b&role @\u200beveryone 1")
        self.assertEqual(svc.clean_name(None), "")
        self.assertEqual(len(svc.clean_name("x" * 300)), 250)

    def test_clean_course_sanitizes_before_upper(self):
        self.assertEqual(svc.clean_course("  csc   10014 "), "CSC 10014")
        # "@everyone".upper() == "@EVERYONE" sẽ lọt bộ lọc nếu viết hoa trước
        self.assertEqual(svc.clean_course("@everyone"), "@\u200bEVERYONE")
        self.assertEqual(svc.clean_course(None), "")
        self.assertEqual(len(svc.clean_course("m" * 150)), 100)

    def test_clean_added_by(self):
        self.assertEqual(svc.clean_added_by("  An   Nguyen ", "X"), "An Nguyen")
        self.assertEqual(svc.clean_added_by("   ", "Web Dashboard"), "Web Dashboard")
        self.assertEqual(svc.clean_added_by(None, "External API"), "External API")
        self.assertEqual(svc.clean_added_by("@here", "X"), "@\u200bhere")
        self.assertEqual(len(svc.clean_added_by("u" * 120, "X")), 95)

    def test_parse_due(self):
        self.assertEqual(svc.parse_due(" 25/12/2026 23:59 ").isoformat(), "2026-12-25T16:59:00+00:00")
        self.assertEqual(svc.parse_due("25/12/2026").isoformat(), "2026-12-25T16:59:00+00:00")
        self.assertIsNone(svc.parse_due("ngày mai"))
        self.assertIsNone(svc.parse_due(None))

    def test_add_manual_deadline(self):
        conn = MagicMock()
        due = datetime(2026, 12, 25, 16, 59, tzinfo=timezone.utc)
        with patch("course_bot.services.manual_deadlines.get_or_create_course", return_value=3) as course,              patch("course_bot.services.manual_deadlines.insert_deadline_manual", return_value=42) as insert:
            res = svc.add_manual_deadline(conn, "CSC10014", "Bài 1", due, "manual-1",
                                          source_url="u", added_by="An", source="external")
        self.assertEqual(res, 42)
        course.assert_called_once_with(conn, "CSC10014")
        insert.assert_called_once_with(conn, 3, "Bài 1", "manual-1", due,
                                       source_url="u", added_by="An", source="external")

    def test_add_manual_deadline_default_source(self):
        with patch("course_bot.services.manual_deadlines.get_or_create_course", return_value=3),              patch("course_bot.services.manual_deadlines.insert_deadline_manual") as insert:
            svc.add_manual_deadline(MagicMock(), "A", "B", None, "manual-1", source_url="u", added_by="An")
        self.assertEqual(insert.call_args[1]["source"], "manual")

    def test_toggle_completed(self):
        with patch("course_bot.services.manual_deadlines.toggle_deadline_completed") as toggle:
            svc.toggle_completed("conn", 9, True, "An")
        toggle.assert_called_once_with("conn", 9, True, "An")

if __name__ == "__main__":
    unittest.main()

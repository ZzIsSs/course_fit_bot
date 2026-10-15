"""
Characterization test cho jobs/notify.py -> run_main_bot.

Chốt: chọn loại tin (NEW / 3_DAYS / 1_DAY), nội dung tin nhắn, cờ DB được cập
nhật, cách tìm/tạo kênh môn và các bước sau khi gửi. Mọi I/O đều bị mock.
"""
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from course_bot.jobs import notify

M = "course_bot.jobs.notify"
SUBJECT = "CSC10014"
DISPLAY = "Nhập Môn Trí Tuệ Nhân Tạo"
NEW_CHAN = "nmttnt-csc10014"   # slugify_channel_name(SUBJECT, DISPLAY)
OLD_CHAN = "csc10014"          # slugify_channel_name(SUBJECT)
CATEGORY_RAW = "CQ2526HK2_CSC10014_CQ2024/2"   # extract_semester_index -> 4

ENV = {
    "bot_token": "tok", "guild_id": "g", "calendar_url": "ics", "database_url": "db",
    "moodle_token": None, "notion_token": None, "notion_db_id": None,
    "google_sa_json": None, "google_sa_file": None, "google_cal_id": None,
}


def deadline_row(notified_new=False, reminded_3d=False, reminded_1d=False, **extra):
    return {"deadlines_id": 11, "notified_new": notified_new, "reminded_3d": reminded_3d,
            "reminded_1d": reminded_1d, **extra}


def moodle_event(time_left, uid="123@courses.fit.hcmus.edu.vn"):
    due = (datetime.now(timezone.utc) + time_left).replace(microsecond=0)
    return {"uid": uid, "summary": "Bài tập 1", "deadline": due,
            "subject": SUBJECT, "category_raw": CATEGORY_RAW}


@pytest.fixture
def bot():
    names = [
        "load_env", "get_bot_user", "fetch_and_parse_events", "get_guild_channels", "get_db",
        "check_completions", "crawl_moodle_deadlines", "get_pending_manual_deadlines",
        "get_deadline_by_lms_id", "get_or_create_course", "insert_deadline",
        "get_course_display_name", "get_course_discord_category", "set_course_discord_category",
        "resolve_category", "create_channel", "update_deadline_notified", "send_message",
        "add_reaction", "create_scheduled_event", "update_deadline_discord_info",
        "insert_notification", "check_moodle_updates",
    ]
    with ExitStack() as stack:
        m = {n: stack.enter_context(patch(f"{M}.{n}")) for n in names}
        m["load_env"].return_value = dict(ENV)
        m["get_bot_user"].return_value = {"id": "bot"}
        m["get_guild_channels"].return_value = [
            {"name": NEW_CHAN, "id": "chan-new", "type": 0},
            {"name": "kì 4", "id": "cat-4", "type": 4},
        ]
        m["get_pending_manual_deadlines"].return_value = []
        m["get_course_display_name"].return_value = DISPLAY
        m["send_message"].return_value = {"id": "msg-1"}
        m["create_scheduled_event"].return_value = {"id": "evt-1"}
        m["conn"] = m["get_db"].return_value.__enter__.return_value
        yield m


def run(bot, event, row):
    bot["fetch_and_parse_events"].return_value = [event]
    bot["get_deadline_by_lms_id"].return_value = row
    notify.run_main_bot()


# ==================== Chọn loại tin nhắn ====================

@pytest.mark.parametrize("flags, time_left, expected", [
    ({}, timedelta(days=10), "NEW"),
    ({"notified_new": True}, timedelta(days=10), None),
    ({"notified_new": True}, timedelta(days=2, hours=23), "3_DAYS"),
    ({"notified_new": True, "reminded_3d": True}, timedelta(days=2), None),
    ({"notified_new": True, "reminded_3d": True}, timedelta(hours=23), "1_DAY"),
    ({"notified_new": True, "reminded_3d": True, "reminded_1d": True}, timedelta(hours=1), None),
    # Hành vi hiện tại (giữ nguyên ở Phase 8): elif chain chỉ gửi 1 loại mỗi lần chạy,
    # nên deadline mới còn < 1 ngày nhận NEW, rồi 3_DAYS, rồi 1_DAY ở các lần chạy sau.
    ({}, timedelta(hours=5), "NEW"),
    ({"notified_new": True}, timedelta(hours=5), "3_DAYS"),
    # Quá hạn: bỏ qua hoàn toàn
    ({}, timedelta(hours=-1), None),
])
def test_reminder_window(bot, flags, time_left, expected):
    run(bot, moodle_event(time_left), deadline_row(**flags))
    if expected is None:
        bot["send_message"].assert_not_called()
        bot["update_deadline_notified"].assert_not_called()
        return
    field = {"NEW": "notified_new", "3_DAYS": "reminded_3d", "1_DAY": "reminded_1d"}[expected]
    bot["update_deadline_notified"].assert_called_once_with(bot["conn"], 11, field)
    bot["send_message"].assert_called_once()


# ==================== Nội dung tin nhắn ====================

def _expected(header, event, url):
    local = event["deadline"].astimezone(timezone(timedelta(hours=7))).strftime("%d/%m/%Y %H:%M")
    return (f"@everyone {header}\n\n📌 **Môn:** {SUBJECT}\n📝 **Nội dung:** Bài tập 1\n"
            f"⏰ **Hạn chót:** {local}\n🔗 **Xem:** {url}"
            "\n\n✅ *React ✅ vào tin nhắn này khi đã hoàn thành!*")


MOODLE_URL = ("https://courses.fit.hcmus.edu.vn/calendar/view.php"
              "?view=day&course=1&time=upcoming#event_123")


@pytest.mark.parametrize("flags, time_left, header", [
    ({}, timedelta(days=10), "🚨 **DEADLINE MỚI** 🚨"),
    ({"notified_new": True}, timedelta(days=2), "⚠️ **NHẮC NHỞ: CÒN 3 NGÀY** ⚠️"),
    ({"notified_new": True, "reminded_3d": True}, timedelta(hours=20), "🆘 **KHẨN CẤP: CÒN 24 GIỜ** 🆘"),
])
def test_message_content(bot, flags, time_left, header):
    event = moodle_event(time_left)
    run(bot, event, deadline_row(**flags))
    bot["send_message"].assert_called_once_with("tok", "chan-new", _expected(header, event, MOODLE_URL))


def test_moodle_uid_without_numeric_id_uses_upcoming_url(bot):
    event = moodle_event(timedelta(days=10), uid="abc@x")
    run(bot, event, deadline_row())
    content = bot["send_message"].call_args[0][2]
    assert "🔗 **Xem:** https://courses.fit.hcmus.edu.vn/calendar/view.php?view=upcoming\n" in content


def test_manual_deadline_uses_stored_source_url(bot):
    due = (datetime.now(timezone.utc) + timedelta(days=10)).replace(microsecond=0)
    bot["fetch_and_parse_events"].return_value = []
    bot["get_pending_manual_deadlines"].return_value = [{
        "lms_deadlines_id": "manual-1", "deadline_name": "Bài tập 1",
        "due_time": due.replace(tzinfo=None), "course_name": SUBJECT,
    }]
    bot["get_deadline_by_lms_id"].return_value = deadline_row(source_url="Discord (thêm bởi An)")
    notify.run_main_bot()
    content = bot["send_message"].call_args[0][2]
    assert "🔗 **Xem:** Discord (thêm bởi An)" in content


# ==================== Sau khi gửi ====================

def test_after_send_new(bot):
    event = moodle_event(timedelta(days=10))
    run(bot, event, deadline_row())
    content = bot["send_message"].call_args[0][2]
    bot["add_reaction"].assert_called_once_with("tok", "chan-new", "msg-1")
    bot["create_scheduled_event"].assert_called_once_with("tok", "g", event)
    bot["update_deadline_discord_info"].assert_called_once_with(bot["conn"], 11, "msg-1", "chan-new", "evt-1")
    bot["insert_notification"].assert_called_once_with(bot["conn"], "deadline", content[:500], 11)
    bot["conn"].commit.assert_called()


def test_after_send_reminder_has_no_scheduled_event(bot):
    run(bot, moodle_event(timedelta(days=2)), deadline_row(notified_new=True))
    bot["create_scheduled_event"].assert_not_called()
    bot["update_deadline_discord_info"].assert_called_once_with(bot["conn"], 11, "msg-1", "chan-new", None)


def test_send_failure_skips_followups(bot):
    bot["send_message"].return_value = None
    run(bot, moodle_event(timedelta(days=10)), deadline_row())
    bot["update_deadline_notified"].assert_called_once()   # cờ được set TRƯỚC khi gửi
    bot["add_reaction"].assert_not_called()
    bot["update_deadline_discord_info"].assert_not_called()


def test_unknown_deadline_is_inserted_first(bot):
    event = moodle_event(timedelta(days=10))
    bot["fetch_and_parse_events"].return_value = [event]
    bot["get_deadline_by_lms_id"].side_effect = [None, deadline_row()]
    bot["get_or_create_course"].return_value = 5
    notify.run_main_bot()
    bot["insert_deadline"].assert_called_once_with(
        bot["conn"], 5, "Bài tập 1", event["uid"], event["deadline"], MOODLE_URL)
    bot["send_message"].assert_called_once()


# ==================== Tìm / tạo kênh môn ====================

def test_channel_new_name_exists(bot):
    run(bot, moodle_event(timedelta(days=10)), deadline_row())
    assert bot["send_message"].call_args[0][1] == "chan-new"
    bot["create_channel"].assert_not_called()


def test_channel_old_name_exists_is_used_without_rename(bot):
    bot["get_guild_channels"].return_value = [{"name": OLD_CHAN, "id": "chan-old", "type": 0}]
    with patch(f"{M}.rename_channel", create=True) as rename:
        run(bot, moodle_event(timedelta(days=10)), deadline_row())
    assert bot["send_message"].call_args[0][1] == "chan-old"
    rename.assert_not_called()
    bot["create_channel"].assert_not_called()


def test_channel_created_in_semester_category(bot):
    bot["get_guild_channels"].return_value = [{"name": "kì 4", "id": "cat-4", "type": 4}]
    bot["resolve_category"].return_value = "cat-4"
    bot["create_channel"].return_value = {"id": "chan-created"}
    run(bot, moodle_event(timedelta(days=10)), deadline_row())
    bot["resolve_category"].assert_called_once_with("tok", "g", {"kì 4": "cat-4"}, "kì 4")
    bot["create_channel"].assert_called_once_with("tok", "g", NEW_CHAN, parent_id="cat-4")
    bot["set_course_discord_category"].assert_called_once_with(bot["conn"], SUBJECT, "cat-4")
    assert bot["send_message"].call_args[0][1] == "chan-created"


def test_channel_created_with_manual_category_when_semester_unknown(bot):
    bot["get_guild_channels"].return_value = []
    bot["get_course_discord_category"].return_value = None
    bot["create_channel"].return_value = {"id": "chan-created"}
    event = moodle_event(timedelta(days=10))
    event["category_raw"] = ""
    run(bot, event, deadline_row())
    bot["resolve_category"].assert_not_called()
    bot["get_course_discord_category"].assert_called_once_with(bot["conn"], SUBJECT)
    bot["create_channel"].assert_called_once_with("tok", "g", NEW_CHAN, parent_id=None)
    bot["set_course_discord_category"].assert_not_called()


def test_channel_create_failure_skips_deadline(bot):
    bot["get_guild_channels"].return_value = []
    bot["create_channel"].return_value = None
    run(bot, moodle_event(timedelta(days=10)), deadline_row())
    bot["send_message"].assert_not_called()
    bot["update_deadline_notified"].assert_not_called()


def test_channel_map_cached_across_events(bot):
    """Kênh vừa tạo được thêm vào cache: event thứ 2 cùng môn không tạo lại."""
    bot["get_guild_channels"].return_value = []
    bot["create_channel"].return_value = {"id": "chan-created"}
    e1, e2 = moodle_event(timedelta(days=10), "1@x"), moodle_event(timedelta(days=9), "2@x")
    bot["fetch_and_parse_events"].return_value = [e1, e2]
    bot["get_deadline_by_lms_id"].return_value = deadline_row()
    notify.run_main_bot()
    assert bot["create_channel"].call_count == 1
    assert [c[0][1] for c in bot["send_message"].call_args_list] == ["chan-created", "chan-created"]

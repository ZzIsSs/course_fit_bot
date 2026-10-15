"""
Characterization test cho 2 bản tìm/tạo kênh môn ngoài notify:
- jobs/announcements.py -> _ensure_channel
- jobs/sync_channels.py -> sync_channels

(Bản trong notify nằm ở tests/unit/jobs/test_notify.py.)
"""
from contextlib import ExitStack
from unittest.mock import MagicMock, call, patch

import pytest

from course_bot.jobs import announcements, sync_channels as sync_mod

SUBJECT = "CSC10014"
DISPLAY = "Nhập Môn Trí Tuệ Nhân Tạo"
NEW_CHAN = "nmttnt-csc10014"
OLD_CHAN = "csc10014"


# ==================== announcements._ensure_channel ====================

@pytest.fixture
def ann():
    names = ["rename_channel", "resolve_category", "create_channel",
             "get_course_discord_category", "set_course_discord_category"]
    with ExitStack() as stack:
        yield {n: stack.enter_context(patch(f"course_bot.jobs.announcements.{n}")) for n in names}


def ensure(channel_map, semester_index=4, category_map=None):
    return announcements._ensure_channel(
        "tok", "g", channel_map, category_map if category_map is not None else {"kì 4": "cat-4"},
        "conn", SUBJECT, DISPLAY, semester_index)


def test_ann_new_name_exists(ann):
    assert ensure({NEW_CHAN: "c1"}) == "c1"
    ann["rename_channel"].assert_not_called()
    ann["create_channel"].assert_not_called()


def test_ann_old_name_is_renamed(ann):
    channel_map = {OLD_CHAN: "c-old"}
    assert ensure(channel_map) == "c-old"
    ann["rename_channel"].assert_called_once_with("tok", "c-old", NEW_CHAN)
    assert channel_map == {NEW_CHAN: "c-old"}


def test_ann_rename_failure_still_updates_cache(ann):
    """Hành vi hiện tại: không kiểm tra kết quả rename."""
    ann["rename_channel"].return_value = None
    channel_map = {OLD_CHAN: "c-old"}
    assert ensure(channel_map) == "c-old"
    assert channel_map == {NEW_CHAN: "c-old"}


def test_ann_creates_in_semester_category(ann):
    ann["resolve_category"].return_value = "cat-4"
    ann["create_channel"].return_value = {"id": "c-new"}
    channel_map = {}
    assert ensure(channel_map) == "c-new"
    ann["resolve_category"].assert_called_once_with("tok", "g", {"kì 4": "cat-4"}, "kì 4")
    ann["create_channel"].assert_called_once_with("tok", "g", NEW_CHAN, parent_id="cat-4")
    ann["set_course_discord_category"].assert_called_once_with("conn", SUBJECT, "cat-4")
    assert channel_map == {NEW_CHAN: "c-new"}


def test_ann_creates_with_manual_category(ann):
    ann["get_course_discord_category"].return_value = "cat-manual"
    ann["create_channel"].return_value = {"id": "c-new"}
    assert ensure({}, semester_index=None) == "c-new"
    ann["resolve_category"].assert_not_called()
    ann["create_channel"].assert_called_once_with("tok", "g", NEW_CHAN, parent_id="cat-manual")
    ann["set_course_discord_category"].assert_called_once_with("conn", SUBJECT, "cat-manual")


def test_ann_create_failure(ann):
    ann["create_channel"].return_value = None
    assert ensure({}) is None
    ann["set_course_discord_category"].assert_not_called()


def test_ann_without_display_name_uses_code_only(ann):
    channel_map = {OLD_CHAN: "c1"}
    assert announcements._ensure_channel("tok", "g", channel_map, {}, "conn", SUBJECT, None, 4) == "c1"
    ann["rename_channel"].assert_not_called()


# ==================== sync_channels ====================

ENV = {"bot_token": "tok", "guild_id": "g", "database_url": "db", "moodle_token": "mt"}


@pytest.fixture
def sync():
    names = ["load_env", "get_site_info", "get_enrolled_courses", "get_guild_channels", "get_db",
             "get_or_create_course", "update_course_chat_id", "rename_channel", "resolve_category",
             "create_channel", "get_course_discord_category", "set_course_discord_category"]
    with ExitStack() as stack:
        m = {n: stack.enter_context(patch(f"course_bot.jobs.sync_channels.{n}")) for n in names}
        m["load_env"].return_value = dict(ENV)
        m["get_site_info"].return_value = {"userid": 1, "fullname": "An"}
        m["conn"] = m["get_db"].return_value.__enter__.return_value
        yield m


def course(cid, code, name):
    return {"id": cid, "shortname": f"CQ2526HK2_{code}_CQ2024/2", "fullname": f"CQ2526HK2_{code}_CQ2024/2 - {name}"}


def test_sync_all_branches(sync):
    sync["get_enrolled_courses"].return_value = [
        course(1, "CSC10014", "Nhập Môn Trí Tuệ Nhân Tạo"),    # đã có tên mới
        course(2, "CSC10006", "Cơ Sở Dữ Liệu"),                 # có tên cũ -> rename OK
        course(3, "CSC10007", "Hệ Điều Hành"),                  # có tên cũ -> rename lỗi
        course(4, "CSC10008", "Mạng Máy Tính"),                 # chưa có -> tạo
        course(5, "CSC10009", "Hệ Thống Máy Tính"),             # chưa có -> tạo lỗi
        {"id": 6, "shortname": "", "fullname": "Thông báo chung"},   # không có mã -> bỏ qua
    ]
    sync["get_guild_channels"].return_value = [
        {"name": "nmttnt-csc10014", "id": "c1", "type": 0},
        {"name": "csc10006", "id": "c2", "type": 0},
        {"name": "csc10007", "id": "c3", "type": 0},
        {"name": "kì 4", "id": "cat-4", "type": 4},
    ]
    sync["get_or_create_course"].side_effect = lambda conn, code, **kw: {"CSC10014": 101, "CSC10006": 102,
                                                                        "CSC10007": 103, "CSC10008": 104,
                                                                        "CSC10009": 105}[code]
    sync["rename_channel"].side_effect = lambda tok, cid, name: {"id": cid} if cid == "c2" else None
    sync["resolve_category"].return_value = "cat-4"
    sync["create_channel"].side_effect = lambda tok, g, name, parent_id=None: (
        {"id": "c4"} if name.endswith("csc10008") else None)

    sync_mod.sync_channels()

    assert sync["update_course_chat_id"].call_args_list == [
        call(sync["conn"], 101, "c1"),
        call(sync["conn"], 102, "c2"),
        call(sync["conn"], 104, "c4"),
    ]
    assert [c[0][1:] for c in sync["rename_channel"].call_args_list] == [
        ("c2", "csdl-csc10006"), ("c3", "hdh-csc10007")]
    assert sync["create_channel"].call_count == 2
    sync["create_channel"].assert_any_call("tok", "g", "mmt-csc10008", parent_id="cat-4")
    sync["set_course_discord_category"].assert_called_once_with(sync["conn"], "CSC10008", "cat-4")
    assert sync["get_or_create_course"].call_count == 5   # khóa không có mã không ghi DB


def test_sync_uses_manual_category_when_semester_unknown(sync):
    sync["get_enrolled_courses"].return_value = [{"id": 1, "shortname": "CSC10014", "fullname": "Nhập Môn Trí Tuệ Nhân Tạo"}]
    sync["get_guild_channels"].return_value = []
    sync["get_or_create_course"].return_value = 101
    sync["get_course_discord_category"].return_value = "cat-manual"
    sync["create_channel"].return_value = {"id": "c9"}
    sync_mod.sync_channels()
    sync["resolve_category"].assert_not_called()
    sync["create_channel"].assert_called_once_with("tok", "g", "nmttnt-csc10014", parent_id="cat-manual")

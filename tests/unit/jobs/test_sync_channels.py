"""
Test cho jobs/sync_channels.py -> sync_channels.

Việc tìm/tạo kênh đi qua services/channel_resolver.py (test riêng ở
tests/unit/services/test_channel_resolver.py); ở đây chốt cách sync dùng kết quả:
cập nhật chat_id và thống kê.
"""
from contextlib import ExitStack
from unittest.mock import call, patch

import pytest

from course_bot.jobs import sync_channels as sync_mod

# ==================== sync_channels ====================

ENV = {"bot_token": "tok", "guild_id": "g", "database_url": "db", "moodle_token": "mt"}


@pytest.fixture
def sync():
    names = ["load_env", "get_site_info", "get_enrolled_courses", "get_guild_channels", "get_db",
             "get_or_create_course", "update_course_chat_id"]
    resolver_names = ["rename_channel", "resolve_category", "create_channel",
                      "get_course_discord_category", "set_course_discord_category"]
    with ExitStack() as stack:
        m = {n: stack.enter_context(patch(f"course_bot.jobs.sync_channels.{n}")) for n in names}
        m.update({n: stack.enter_context(patch(f"course_bot.services.channel_resolver.{n}"))
                  for n in resolver_names})
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

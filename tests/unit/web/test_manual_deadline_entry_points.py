"""
Characterization test cho 2 entry point thêm deadline thủ công (bản Web nằm trong
test_router.py): Discord /add_deadline và API bên thứ 3 (/api/add_deadline).

Chốt chuẩn hoá input, lms_id, source/added_by và response của từng nơi.
"""
import json
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from course_bot.web.routes import discord_interactions, external

DUE_UTC = "2026-12-25T16:59:00+00:00"   # 25/12/2026 23:59 giờ VN


@pytest.fixture
def db():
    def _make(module):
        stack = ExitStack()
        m = {n: stack.enter_context(patch(f"{module}.{n}"))
             for n in ("get_db", "get_or_create_course", "insert_deadline_manual")}
        m["conn"] = m["get_db"].return_value.__enter__.return_value
        m["get_or_create_course"].return_value = 3
        m["insert_deadline_manual"].return_value = 42
        m["stack"] = stack
        return m
    made = []
    def factory(module):
        m = _make(module)
        made.append(m)
        return m
    yield factory
    for m in made:
        m["stack"].close()


# ==================== Discord /add_deadline ====================

D = "course_bot.web.routes.discord_interactions"


def interaction(options, channel_id="chan-1", username="an", iid="9999"):
    return {
        "id": iid, "channel_id": channel_id,
        "member": {"user": {"username": username}},
        "data": {"name": "add_deadline", "options": [{"name": k, "value": v} for k, v in options.items()]},
    }


def test_discord_add_ok_and_sanitizes(db):
    m = db(D)
    resp = discord_interactions.handle_interaction(interaction(
        {"ten": "  Bài <@&123> @everyone  1 ", "han_chot": "25/12/2026 23:59", "mon": " csc 10014 "},
        username="@here An"), "db")
    m["get_or_create_course"].assert_called_once_with(m["conn"], "CSC 10014")
    args, kwargs = m["insert_deadline_manual"].call_args
    assert args[:3] == (m["conn"], 3, "Bài @​&role @​everyone 1")
    assert args[3] == "manual-9999"
    assert args[4].isoformat() == DUE_UTC
    assert kwargs == {"source_url": "Discord (thêm bởi @​here An)", "added_by": "@​here An"}
    assert resp["type"] == 4
    assert resp["data"]["allowed_mentions"] == {"parse": []}
    assert resp["data"]["content"].startswith("📌 **Deadline nội bộ mới**\n📚 Môn: **CSC 10014**\n")


def test_discord_add_course_from_channel(db):
    m = db(D)
    with patch(f"{D}.get_course_name_by_chat_id", return_value="CSC10006") as by_chat:
        discord_interactions.handle_interaction(interaction({"ten": "x", "han_chot": "25/12/2026"}), "db")
    by_chat.assert_called_once_with(m["conn"], "chan-1")
    m["get_or_create_course"].assert_called_once_with(m["conn"], "CSC10006")


def test_discord_add_unknown_course(db):
    m = db(D)
    with patch(f"{D}.get_course_name_by_chat_id", return_value=None):
        resp = discord_interactions.handle_interaction(interaction({"ten": "x", "han_chot": "25/12/2026"}), "db")
    assert resp["data"] == {"content": "❌ Không xác định được môn. Dùng lệnh trong kênh của môn, hoặc điền option `mon`.", "flags": 64}
    m["insert_deadline_manual"].assert_not_called()


@pytest.mark.parametrize("options", [{"ten": "x", "han_chot": "ngày mai"}, {"ten": " ", "han_chot": "25/12/2026"}])
def test_discord_add_invalid(db, options):
    m = db(D)
    resp = discord_interactions.handle_interaction(interaction(options), "db")
    assert resp["data"]["flags"] == 64
    assert resp["data"]["content"].startswith("❌ Hạn chót sai định dạng hoặc tên bài trống.")
    m["get_db"].assert_not_called()


def test_discord_add_duplicate(db):
    m = db(D)
    m["insert_deadline_manual"].return_value = None
    resp = discord_interactions.handle_interaction(interaction({"ten": "x", "han_chot": "25/12/2026", "mon": "A"}), "db")
    assert "_(xác nhận lặp lại — deadline này đã được lưu từ trước, không tạo trùng)_" in resp["data"]["content"]


def test_discord_add_limits(db):
    m = db(D)
    discord_interactions.handle_interaction(
        interaction({"ten": "t" * 300, "han_chot": "25/12/2026", "mon": "m" * 150}, username="u" * 120, iid="i" * 60), "db")
    args, kwargs = m["insert_deadline_manual"].call_args
    assert len(args[2]) == 250
    assert args[3] == "manual-" + "i" * 40
    assert kwargs["added_by"] == "u" * 95
    m["get_or_create_course"].assert_called_once_with(m["conn"], "M" * 100)


# ==================== API bên thứ 3 ====================

E = "course_bot.web.routes.external"


def add_external(body):
    return external.handle_add_deadline(json.dumps(body) if not isinstance(body, str) else body, "db")


def test_external_add_ok(db):
    m = db(E)
    status, resp = add_external({"ten": "  Nộp  báo cáo ", "han_chot": "25/12/2026 23:59",
                                 "mon": " csc 10014 ", "nguon": "  Google   Form ", "id": "abc"})
    assert status == 201
    assert resp == {"ok": True, "deadlines_id": 42, "mon": "CSC 10014", "han_chot_utc": DUE_UTC}
    m["get_or_create_course"].assert_called_once_with(m["conn"], "CSC 10014")
    args, kwargs = m["insert_deadline_manual"].call_args
    assert args[:4] == (m["conn"], 3, "Nộp báo cáo", "external-abc")
    assert kwargs == {"source_url": "API bên thứ 3 (Google Form)", "added_by": "Google Form", "source": "external"}


def test_external_mon_keeps_inner_spaces_and_mentions(db):
    """Hành vi hiện tại: không gộp khoảng trắng trong mon, không chặn mention."""
    m = db(E)
    add_external({"ten": "<@&1> @everyone", "han_chot": "25/12/2026", "mon": "csc  10014"})
    m["get_or_create_course"].assert_called_once_with(m["conn"], "CSC  10014")
    assert m["insert_deadline_manual"].call_args[0][2] == "<@&1> @everyone"


def test_external_defaults_and_generated_id(db):
    m = db(E)
    add_external({"ten": "x", "han_chot": "25/12/2026", "mon": "A"})
    args, kwargs = m["insert_deadline_manual"].call_args
    assert args[3].startswith("external-") and len(args[3]) == len("external-") + 36
    assert kwargs["added_by"] == "External API"


@pytest.mark.parametrize("body, error", [
    ("not-json", "Body không phải JSON hợp lệ."),
    ([1, 2], "Body JSON phải là một object."),
    ({"ten": "x", "han_chot": "25/12/2026"}, "Thiếu trường bắt buộc: ten, han_chot, mon."),
    ({"ten": "x", "han_chot": "mai", "mon": "A"}, "han_chot sai định dạng. VD: '25/12/2026 23:59' hoặc '25/12/2026'."),
])
def test_external_400(db, body, error):
    m = db(E)
    assert add_external(body) == (400, {"ok": False, "error": error})
    m["insert_deadline_manual"].assert_not_called()


def test_external_duplicate_and_db_error(db):
    m = db(E)
    m["insert_deadline_manual"].return_value = None
    assert add_external({"ten": "x", "han_chot": "25/12/2026", "mon": "A"}) == (
        200, {"ok": True, "duplicate": True, "message": "Deadline này đã tồn tại, bỏ qua trùng lặp."})
    m["get_or_create_course"].side_effect = RuntimeError("boom")
    assert add_external({"ten": "x", "han_chot": "25/12/2026", "mon": "A"}) == (
        500, {"ok": False, "error": "Lỗi CSDL khi thêm deadline: boom"})


def test_external_limits(db):
    m = db(E)
    add_external({"ten": "t" * 300, "han_chot": "25/12/2026", "mon": "m" * 150, "nguon": "n" * 120, "id": "i" * 60})
    args, kwargs = m["insert_deadline_manual"].call_args
    assert len(args[2]) == 250
    assert args[3] == "external-" + "i" * 40
    assert kwargs["added_by"] == "n" * 95
    m["get_or_create_course"].assert_called_once_with(m["conn"], "M" * 100)

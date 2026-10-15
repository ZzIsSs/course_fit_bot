"""
Characterization test cho HTTP handler của Vercel (`api/index.py` -> `handler`).

Chốt status, JSON, header CORS và thứ tự match route (theo `endswith`) trước khi
tách router thành web/router.py + web/routes/*. Mọi truy cập DB, chữ ký Discord
và API key đều bị mock: không có request nào ra ngoài.
"""
import io
import json
import os
from contextlib import ExitStack
from unittest.mock import ANY, MagicMock, patch

import pytest

from api.index import handler

# Tên được mock -> module đang giữ tên đó (cập nhật khi di chuyển code).
TARGETS = {
    "get_db": "api.index",
    "get_courses_with_deadline_counts": "api.index",
    "get_dashboard_stats": "api.index",
    "get_all_deadlines_with_course_details": "api.index",
    "get_recent_announcements_with_course": "api.index",
    "get_or_create_course": "api.index",
    "insert_deadline_manual": "api.index",
    "toggle_deadline_completed": "api.index",
    "verify_signature": "api.index",
    "handle_interaction": "api.index",
    "verify_api_key": "api.index",
    "handle_add_deadline": "api.index",
}

DATABASE_URL = os.environ["DATABASE_URL"]
CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-API-Key, X-Signature-Ed25519, X-Signature-Timestamp",
}


@pytest.fixture
def mocks():
    with ExitStack() as stack:
        m = {name: stack.enter_context(patch(f"{module}.{name}")) for name, module in TARGETS.items()}
        m["conn"] = m["get_db"].return_value.__enter__.return_value
        m["semester"] = stack.enter_context(
            patch("course_bot.domain.semester.get_current_semester", return_value="HK1 2026-2027"))
        yield m


class Response:
    def __init__(self, raw):
        head, _, self.body = raw.partition(b"\r\n\r\n")
        lines = head.decode("latin-1").split("\r\n")
        self.status = int(lines[0].split()[1])
        self.headers = dict(line.split(": ", 1) for line in lines[1:])

    def json(self):
        return json.loads(self.body.decode("utf-8"))


def request(method, path, body=b"", headers=None):
    """Gọi handler như Vercel nhưng không mở socket."""
    if isinstance(body, (dict, list)):
        body = json.dumps(body).encode("utf-8")
    elif isinstance(body, str):
        body = body.encode("utf-8")
    h = handler.__new__(handler)
    h.path = path
    h.command = method
    h.request_version = "HTTP/1.1"
    h.requestline = f"{method} {path} HTTP/1.1"
    h.client_address = ("test", 0)
    h.headers = {"Content-Length": str(len(body)), **(headers or {})}
    h.rfile = io.BytesIO(body)
    h.wfile = io.BytesIO()
    h.log_message = lambda *args: None
    getattr(h, f"do_{method}")()
    return Response(h.wfile.getvalue())


def assert_json_with_cors(resp, status):
    assert resp.status == status
    for k, v in CORS.items():
        assert resp.headers[k] == v
    assert resp.headers["Content-Type"] == "application/json; charset=utf-8"


# ==================== OPTIONS / GET ====================

def test_options_preflight(mocks):
    resp = request("OPTIONS", "/api/deadlines")
    assert resp.status == 200
    for k, v in CORS.items():
        assert resp.headers[k] == v
    assert "Content-Type" not in resp.headers
    assert resp.body == b""


@pytest.mark.parametrize("path", ["/", "/api", "/api/", "/api/health", "/api/health/"])
def test_health(mocks, path):
    resp = request("GET", path)
    assert_json_with_cors(resp, 200)
    assert resp.json() == {"ok": True, "service": "Course FIT HCMUS Bot API", "status": "online"}


@pytest.mark.parametrize("path", ["/api/courses", "/api/courses/", "/api/x/courses"])
def test_get_courses(mocks, path):
    mocks["get_courses_with_deadline_counts"].return_value = [{"courses_id": 1}]
    resp = request("GET", path)
    assert_json_with_cors(resp, 200)
    assert resp.json() == {"ok": True, "data": [{"courses_id": 1}]}
    mocks["get_db"].assert_called_once_with(DATABASE_URL)
    mocks["get_courses_with_deadline_counts"].assert_called_once_with(mocks["conn"])


def test_get_stats_adds_semester(mocks):
    mocks["get_dashboard_stats"].return_value = {"total_deadlines": 3}
    resp = request("GET", "/api/stats")
    assert_json_with_cors(resp, 200)
    assert resp.json() == {"ok": True, "data": {"total_deadlines": 3, "semester": "HK1 2026-2027"}}


def test_get_deadlines_with_course_filter_and_datetime(mocks):
    from datetime import datetime, timezone
    due = datetime(2026, 12, 31, 16, 59, tzinfo=timezone.utc)
    mocks["get_all_deadlines_with_course_details"].return_value = [{"deadlines_id": 7, "due_time": due}]
    resp = request("GET", "/api/deadlines?course=CSC10014")
    assert_json_with_cors(resp, 200)
    assert resp.json() == {
        "ok": True,
        "data": [{"deadlines_id": 7, "due_time": "2026-12-31T16:59:00+00:00"}],
        "total": 1,
    }
    mocks["get_all_deadlines_with_course_details"].assert_called_once_with(mocks["conn"], "CSC10014")


def test_get_deadlines_without_filter(mocks):
    mocks["get_all_deadlines_with_course_details"].return_value = []
    resp = request("GET", "/api/deadlines")
    assert resp.json() == {"ok": True, "data": [], "total": 0}
    mocks["get_all_deadlines_with_course_details"].assert_called_once_with(mocks["conn"], None)


def test_get_announcements(mocks):
    mocks["get_recent_announcements_with_course"].return_value = [{"announcements_id": 2}]
    resp = request("GET", "/api/announcements")
    assert_json_with_cors(resp, 200)
    assert resp.json() == {"ok": True, "data": [{"announcements_id": 2}]}
    mocks["get_recent_announcements_with_course"].assert_called_once_with(mocks["conn"])


@pytest.mark.parametrize("path, func, label", [
    ("/api/courses", "get_courses_with_deadline_counts", "courses"),
    ("/api/stats", "get_dashboard_stats", "stats"),
    ("/api/deadlines", "get_all_deadlines_with_course_details", "deadlines"),
    ("/api/announcements", "get_recent_announcements_with_course", "announcements"),
])
def test_get_db_error_returns_500(mocks, path, func, label):
    mocks[func].side_effect = RuntimeError("boom")
    resp = request("GET", path)
    assert_json_with_cors(resp, 500)
    assert resp.json() == {"ok": False, "error": f"Lỗi truy vấn {label}: boom"}


@pytest.mark.parametrize("path", ["/api/nope", "/api/interactions", "/api/deadlines/toggle"])
def test_get_unknown_route_404(mocks, path):
    resp = request("GET", path)
    assert_json_with_cors(resp, 404)
    assert resp.json() == {"ok": False, "error": f"Route not found: {path}"}


# ==================== POST /api/interactions ====================

SIG_HEADERS = {"X-Signature-Ed25519": "ab", "X-Signature-Timestamp": "123"}


def test_interactions_bad_signature_401_empty(mocks):
    mocks["verify_signature"].return_value = False
    resp = request("POST", "/api/interactions", '{"type":1}', SIG_HEADERS)
    assert resp.status == 401
    assert resp.body == b""
    assert "Access-Control-Allow-Origin" not in resp.headers
    mocks["verify_signature"].assert_called_once_with("ab", "123", '{"type":1}')
    mocks["handle_interaction"].assert_not_called()


def test_interactions_missing_signature_headers(mocks):
    mocks["verify_signature"].return_value = False
    request("POST", "/api/interactions", '{"type":1}')
    mocks["verify_signature"].assert_called_once_with("", "", '{"type":1}')


def test_interactions_ping(mocks):
    mocks["verify_signature"].return_value = True
    resp = request("POST", "/api/interactions", {"type": 1}, SIG_HEADERS)
    assert_json_with_cors(resp, 200)
    assert resp.json() == {"type": 1}
    mocks["handle_interaction"].assert_not_called()


def test_interactions_command(mocks):
    mocks["verify_signature"].return_value = True
    mocks["handle_interaction"].return_value = {"type": 4, "data": {"content": "ok"}}
    resp = request("POST", "/api/interactions/", {"type": 2, "data": {"name": "deadline"}}, SIG_HEADERS)
    assert_json_with_cors(resp, 200)
    assert resp.json() == {"type": 4, "data": {"content": "ok"}}
    mocks["handle_interaction"].assert_called_once_with({"type": 2, "data": {"name": "deadline"}}, DATABASE_URL)


@pytest.mark.parametrize("body, raises", [("not-json", False), ('{"type": 2}', True)])
def test_interactions_internal_error(mocks, body, raises):
    mocks["verify_signature"].return_value = True
    if raises:
        mocks["handle_interaction"].side_effect = RuntimeError("boom")
    resp = request("POST", "/api/interactions", body, SIG_HEADERS)
    assert_json_with_cors(resp, 200)
    assert resp.json() == {"type": 4, "data": {"content": "⚠️ Đã xảy ra lỗi nội bộ khi xử lý lệnh.", "flags": 64}}


# ==================== POST /api/add_deadline ====================

def test_add_deadline_bad_key(mocks):
    mocks["verify_api_key"].return_value = False
    resp = request("POST", "/api/add_deadline", {"ten": "x"}, {"X-API-Key": "wrong"})
    assert_json_with_cors(resp, 401)
    assert resp.json() == {"ok": False, "error": "API key không hợp lệ hoặc thiếu."}
    mocks["verify_api_key"].assert_called_once_with("wrong")
    mocks["handle_add_deadline"].assert_not_called()


def test_add_deadline_missing_key(mocks):
    mocks["verify_api_key"].return_value = False
    request("POST", "/api/add_deadline", "{}")
    mocks["verify_api_key"].assert_called_once_with("")


def test_add_deadline_ok(mocks):
    mocks["verify_api_key"].return_value = True
    mocks["handle_add_deadline"].return_value = (201, {"ok": True, "deadlines_id": 5})
    resp = request("POST", "/api/add_deadline", '{"ten": "x"}', {"X-API-Key": "k"})
    assert_json_with_cors(resp, 201)
    assert resp.json() == {"ok": True, "deadlines_id": 5}
    mocks["handle_add_deadline"].assert_called_once_with('{"ten": "x"}', DATABASE_URL)


# ==================== POST /api/deadlines ====================

VALID = {"mon": "  csc  10014 ", "ten": "  Bài   tập 1 ", "han_chot": " 25/12/2026 23:59 "}


def test_create_deadline_201_and_normalizes_input(mocks):
    mocks["get_or_create_course"].return_value = 3
    mocks["insert_deadline_manual"].return_value = 42
    resp = request("POST", "/api/deadlines", VALID)
    assert_json_with_cors(resp, 201)
    assert resp.json() == {"ok": True, "deadlines_id": 42, "message": "Thêm deadline thành công!"}
    mocks["get_or_create_course"].assert_called_once_with(mocks["conn"], "CSC 10014")
    args, kwargs = mocks["insert_deadline_manual"].call_args
    assert args[:3] == (mocks["conn"], 3, "Bài tập 1")
    assert args[3].startswith("manual-")
    assert args[4].isoformat() == "2026-12-25T16:59:00+00:00"  # 23:59 giờ VN, lưu UTC
    assert kwargs == {"source_url": "Thêm thủ công qua Web", "added_by": "Web Dashboard", "source": "manual"}


def test_create_deadline_optional_fields(mocks):
    mocks["insert_deadline_manual"].return_value = 1
    request("POST", "/api/deadlines", {**VALID, "nguoi_phu_trach": "  An  Nguyen ", "ghi_chu_url": " http://x "})
    _, kwargs = mocks["insert_deadline_manual"].call_args
    assert kwargs == {"source_url": "http://x", "added_by": "An Nguyen", "source": "manual"}


def test_create_deadline_duplicate_200(mocks):
    mocks["insert_deadline_manual"].return_value = None
    resp = request("POST", "/api/deadlines", VALID)
    assert_json_with_cors(resp, 200)
    assert resp.json() == {"ok": True, "duplicate": True, "message": "Deadline này đã tồn tại, không tạo trùng."}


@pytest.mark.parametrize("body, error", [
    ("not-json", "Body không phải JSON hợp lệ."),
    ({"mon": "A", "ten": "B"}, "Vui lòng điền đủ: mon, ten, han_chot."),
    ({"mon": " ", "ten": "B", "han_chot": "25/12/2026"}, "Vui lòng điền đủ: mon, ten, han_chot."),
    ({**VALID, "han_chot": "ngày mai"}, "Sai định dạng ngày. VD: '25/09/2026 23:59'."),
])
def test_create_deadline_400(mocks, body, error):
    resp = request("POST", "/api/deadlines", body)
    assert_json_with_cors(resp, 400)
    assert resp.json() == {"ok": False, "error": error}
    mocks["insert_deadline_manual"].assert_not_called()


def test_create_deadline_db_error_500(mocks):
    mocks["get_or_create_course"].side_effect = RuntimeError("boom")
    resp = request("POST", "/api/deadlines", VALID)
    assert_json_with_cors(resp, 500)
    assert resp.json() == {"ok": False, "error": "Lỗi DB khi thêm deadline: boom"}


# ==================== POST /api/deadlines/toggle ====================

def test_toggle_ok(mocks):
    resp = request("POST", "/api/deadlines/toggle", {"deadlines_id": 9, "completed": 1, "completed_by": "An"})
    assert_json_with_cors(resp, 200)
    assert resp.json() == {"ok": True, "deadlines_id": 9, "completed": True}
    mocks["toggle_deadline_completed"].assert_called_once_with(mocks["conn"], 9, True, "An")


def test_toggle_defaults(mocks):
    request("POST", "/api/deadlines/toggle/", {"deadlines_id": 9})
    mocks["toggle_deadline_completed"].assert_called_once_with(mocks["conn"], 9, False, "Web User")


@pytest.mark.parametrize("body, error", [
    ("not-json", "Body không phải JSON hợp lệ."),
    ({"completed": True}, "Thiếu deadlines_id"),
])
def test_toggle_400(mocks, body, error):
    resp = request("POST", "/api/deadlines/toggle", body)
    assert_json_with_cors(resp, 400)
    assert resp.json() == {"ok": False, "error": error}


def test_toggle_db_error_500(mocks):
    mocks["toggle_deadline_completed"].side_effect = RuntimeError("boom")
    resp = request("POST", "/api/deadlines/toggle", {"deadlines_id": 9})
    assert_json_with_cors(resp, 500)
    assert resp.json() == {"ok": False, "error": "Lỗi DB khi toggle deadline: boom"}


# ==================== POST: route khác ====================

@pytest.mark.parametrize("path", ["/api/nope", "/api/courses", "/api/stats", "/api"])
def test_post_unknown_route_404(mocks, path):
    resp = request("POST", path, "{}")
    assert_json_with_cors(resp, 404)
    assert resp.json() == {"ok": False, "error": f"Route not found: {path.rstrip('/')}"}


def test_post_nested_paths_match_by_suffix(mocks):
    """Router match bằng endswith: tiền tố bất kỳ vẫn vào đúng route."""
    mocks["verify_api_key"].return_value = False
    resp = request("POST", "/anything/add_deadline", "{}")
    assert resp.status == 401
    mocks["verify_api_key"].assert_called_once()

"""Vercel Unified API Entrypoint.

Điều hướng các request từ Vercel Serverless Functions:
- POST /api/interactions: Nhận và xử lý Slash Commands từ Discord (PING, /add_deadline, /deadline).
- POST /api/add_deadline: Endpoint cho API bên thứ 3 thêm deadline (X-API-Key).
- GET /api/courses: Lấy danh sách khóa học kèm số lượng deadline.
- GET /api/deadlines: Lấy danh sách bài tập (hỗ trợ lọc theo môn, trạng thái).
- POST /api/deadlines: Tạo deadline thủ công từ Web UI.
- POST /api/deadlines/toggle: Đánh dấu hoàn thành / bỏ hoàn thành deadline.
- GET /api/stats: Thống kê tổng quan cho Dashboard.
- GET /api/announcements: Lấy danh sách thông báo môn học.
- GET /: Health check endpoint.
"""
import os
import sys
import json
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Đảm bảo import được các module trong src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.database import get_db
from src.interactions import verify_signature, handle_interaction
from src.external_api import verify_api_key, handle_add_deadline
from src.utils import parse_due_time
from src.config import LOCAL_TZ
from src.db_queries import (
    get_or_create_course,
    insert_deadline_manual,
    toggle_deadline_completed,
    get_courses_with_deadline_counts,
    get_dashboard_stats,
    get_all_deadlines_with_course_details,
    get_recent_announcements_with_course,
)

DATABASE_URL = os.environ.get("DATABASE_URL")


def json_serializer(obj):
    """JSON serializer cho các đối tượng datetime."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Xử lý pre-flight CORS request cho Web Dashboard."""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Xử lý các GET request."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/")
        query_params = parse_qs(parsed_url.query)

        # 1. Health check
        if path in ("", "/api", "/api/health"):
            self._send_json(200, {"ok": True, "service": "Course FIT HCMUS Bot API", "status": "online"})
            return

        # 2. Danh sách môn học
        if path.endswith("/courses"):
            try:
                with get_db(DATABASE_URL) as conn:
                    courses = get_courses_with_deadline_counts(conn)
                self._send_json(200, {"ok": True, "data": courses})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": f"Lỗi truy vấn courses: {str(e)}"})
            return

        # 3. Thống kê Dashboard
        if path.endswith("/stats"):
            try:
                with get_db(DATABASE_URL) as conn:
                    stats = get_dashboard_stats(conn)
                self._send_json(200, {"ok": True, "data": stats})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": f"Lỗi truy vấn stats: {str(e)}"})
            return

        # 4. Danh sách Deadlines
        if path.endswith("/deadlines"):
            course = query_params.get("course", [None])[0]
            try:
                with get_db(DATABASE_URL) as conn:
                    deadlines = get_all_deadlines_with_course_details(conn, course)
                self._send_json(200, {"ok": True, "data": deadlines, "total": len(deadlines)})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": f"Lỗi truy vấn deadlines: {str(e)}"})
            return

        # 5. Danh sách Thông báo
        if path.endswith("/announcements"):
            try:
                with get_db(DATABASE_URL) as conn:
                    announcements = get_recent_announcements_with_course(conn)
                self._send_json(200, {"ok": True, "data": announcements})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": f"Lỗi truy vấn announcements: {str(e)}"})
            return

        self._send_json(404, {"ok": False, "error": f"Route not found: {path}"})

    def do_POST(self):
        """Điều hướng POST request dựa trên URL path."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/")

        # 1. Discord Interactions (Slash Commands)
        if path.endswith("/interactions"):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
            sig = self.headers.get("X-Signature-Ed25519", "")
            ts = self.headers.get("X-Signature-Timestamp", "")

            if not verify_signature(sig, ts, body):
                self.send_response(401)
                self.end_headers()
                return

            interaction = json.loads(body)
            result = {"type": 1} if interaction.get("type") == 1 else handle_interaction(interaction, DATABASE_URL)
            self._send_json(200, result)
            return

        # 2. Thêm deadline từ bên thứ 3 (API Key)
        if path.endswith("/add_deadline"):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
            api_key = self.headers.get("X-API-Key", "")

            if not verify_api_key(api_key):
                self._send_json(401, {"ok": False, "error": "API key không hợp lệ hoặc thiếu."})
                return

            status, result = handle_add_deadline(body, DATABASE_URL)
            self._send_json(status, result)
            return

        # 3. Thêm deadline thủ công từ Web UI
        if path.endswith("/deadlines") and not path.endswith("/toggle"):
            body_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(body_len).decode("utf-8")
            try:
                data = json.loads(body)
            except Exception:
                self._send_json(400, {"ok": False, "error": "Body không phải JSON hợp lệ."})
                return

            mon = (data.get("mon") or "").strip().upper()
            ten = (data.get("ten") or "").strip()
            han_chot = (data.get("han_chot") or "").strip()
            nguoi = (data.get("nguoi_phu_trach") or "Web Dashboard").strip()
            ghi_chu = (data.get("ghi_chu_url") or "").strip()

            if not mon or not ten or not han_chot:
                self._send_json(400, {"ok": False, "error": "Vui lòng điền đủ: mon, ten, han_chot."})
                return

            due_time = parse_due_time(han_chot, LOCAL_TZ)
            if due_time is None:
                self._send_json(400, {"ok": False, "error": "Sai định dạng ngày. VD: '25/09/2026 23:59'."})
                return

            lms_id = f"manual-{uuid.uuid4()}"
            try:
                with get_db(DATABASE_URL) as conn:
                    courses_id = get_or_create_course(conn, mon)
                    deadlines_id = insert_deadline_manual(
                        conn, courses_id, ten, lms_id, due_time,
                        source_url=ghi_chu if ghi_chu else "Thêm thủ công qua Web",
                        added_by=nguoi,
                        source="manual"
                    )
                self._send_json(201, {"ok": True, "deadlines_id": deadlines_id, "message": "Thêm deadline thành công!"})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": f"Lỗi DB khi thêm deadline: {str(e)}"})
            return

        # 4. Đánh dấu hoàn thành deadline từ Web UI
        if path.endswith("/deadlines/toggle"):
            body_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(body_len).decode("utf-8")
            try:
                data = json.loads(body)
            except Exception:
                self._send_json(400, {"ok": False, "error": "Body không phải JSON hợp lệ."})
                return

            deadlines_id = data.get("deadlines_id")
            completed = bool(data.get("completed"))
            completed_by = data.get("completed_by", "Web User")

            if not deadlines_id:
                self._send_json(400, {"ok": False, "error": "Thiếu deadlines_id"})
                return

            try:
                with get_db(DATABASE_URL) as conn:
                    toggle_deadline_completed(conn, deadlines_id, completed, completed_by)
                self._send_json(200, {"ok": True, "deadlines_id": deadlines_id, "completed": completed})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": f"Lỗi DB khi toggle deadline: {str(e)}"})
            return

        # Route không tồn tại
        self._send_json(404, {"ok": False, "error": f"Route not found: {path}"})

    def _set_cors_headers(self):
        """Thiết lập CORS headers cho phép gọi từ localhost:5173 và production."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key, X-Signature-Ed25519, X-Signature-Timestamp")

    def _send_json(self, status, payload):
        """Helper gửi response JSON có CORS và encoding chuẩn."""
        self.send_response(status)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False, default=json_serializer).encode("utf-8"))

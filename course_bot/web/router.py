"""Vercel Unified API Router.

Điều hướng các request từ Vercel Serverless Functions (api/index.py re-export `handler`):
- POST /api/interactions: Nhận và xử lý Slash Commands từ Discord (PING, /add_deadline, /deadline).
- POST /api/add_deadline: Endpoint cho API bên thứ 3 thêm deadline (X-API-Key).
- GET /api/courses: Lấy danh sách khóa học kèm số lượng deadline.
- GET /api/deadlines: Lấy danh sách bài tập (hỗ trợ lọc theo môn, trạng thái).
- POST /api/deadlines: Tạo deadline thủ công từ Web UI.
- POST /api/deadlines/toggle: Đánh dấu hoàn thành / bỏ hoàn thành deadline.
- GET /api/stats: Thống kê tổng quan cho Dashboard.
- GET /api/announcements: Lấy danh sách thông báo môn học.
- GET /: Health check endpoint.

Route được match bằng `endswith` theo đúng thứ tự bên dưới.
"""
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from course_bot.core.logging_setup import configure_logging
from course_bot.web.http_utils import read_body, send_json, set_cors_headers
from course_bot.web.routes import dashboard, discord_interactions, external

# Entry point của runtime Vercel: cấu hình logging một lần khi module được load.
configure_logging()

DATABASE_URL = os.environ.get("DATABASE_URL")


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Xử lý pre-flight CORS request cho Web Dashboard."""
        self.send_response(200)
        set_cors_headers(self)
        self.end_headers()

    def do_GET(self):
        """Xử lý các GET request."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/")
        query_params = parse_qs(parsed_url.query)

        # 1. Health check
        if path in ("", "/api", "/api/health"):
            send_json(self, 200, {"ok": True, "service": "Course FIT HCMUS Bot API", "status": "online"})
            return

        # 2. Danh sách môn học
        if path.endswith("/courses"):
            send_json(self, *dashboard.get_courses(DATABASE_URL))
            return

        # 3. Thống kê Dashboard
        if path.endswith("/stats"):
            send_json(self, *dashboard.get_stats(DATABASE_URL))
            return

        # 4. Danh sách Deadlines
        if path.endswith("/deadlines"):
            send_json(self, *dashboard.get_deadlines(DATABASE_URL, query_params))
            return

        # 5. Danh sách Thông báo
        if path.endswith("/announcements"):
            send_json(self, *dashboard.get_announcements(DATABASE_URL))
            return

        send_json(self, 404, {"ok": False, "error": f"Route not found: {path}"})

    def do_POST(self):
        """Điều hướng POST request dựa trên URL path."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/")

        # 1. Discord Interactions (Slash Commands)
        if path.endswith("/interactions"):
            status, payload = discord_interactions.handle_http(
                read_body(self),
                self.headers.get("X-Signature-Ed25519", ""),
                self.headers.get("X-Signature-Timestamp", ""),
                DATABASE_URL,
            )
            if payload is None:
                self.send_response(status)
                self.end_headers()
                return
            send_json(self, status, payload)
            return

        # 2. Thêm deadline từ bên thứ 3 (API Key)
        if path.endswith("/add_deadline"):
            body = read_body(self)
            send_json(self, *external.handle_http(body, self.headers.get("X-API-Key", ""), DATABASE_URL))
            return

        # 3. Thêm deadline thủ công từ Web UI
        if path.endswith("/deadlines") and not path.endswith("/toggle"):
            send_json(self, *dashboard.create_deadline(read_body(self), DATABASE_URL))
            return

        # 4. Đánh dấu hoàn thành deadline từ Web UI
        if path.endswith("/deadlines/toggle"):
            send_json(self, *dashboard.toggle_deadline(read_body(self), DATABASE_URL))
            return

        # Route không tồn tại
        send_json(self, 404, {"ok": False, "error": f"Route not found: {path}"})

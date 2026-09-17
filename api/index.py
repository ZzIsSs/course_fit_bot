"""Vercel Unified API Entrypoint.

Điều hướng các request từ Vercel Serverless Functions về đúng handler:
- POST /api/interactions: Nhận và xử lý Slash Commands từ Discord (PING, /add_deadline, /deadline).
- POST /api/add_deadline: Endpoint cho API bên thứ 3 thêm deadline.
- GET / hoặc /api: Health check endpoint.
"""
import os
import sys
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

# Đảm bảo import được các module trong src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.interactions import verify_signature, handle_interaction
from src.external_api import verify_api_key, handle_add_deadline

DATABASE_URL = os.environ.get("DATABASE_URL")


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Health check endpoint."""
        self._send_json(200, {"ok": True, "service": "Course FIT HCMUS Bot API", "status": "online"})

    def do_POST(self):
        """Điều hướng POST request dựa trên URL path."""
        path = urlparse(self.path).path.rstrip("/")

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

        # 2. Thêm deadline từ bên thứ 3 (Third-party API)
        if path.endswith("/add_deadline"):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
            api_key = self.headers.get("X-API-Key", "")

            if not verify_api_key(api_key):
                self._send_json(401, {"ok": False, "error": "API key không hợp lệ hoặc thiếu."})
                return

            status, result = handle_add_deadline(body, DATABASE_URL)
            self._send_json(status, result)
            return

        # Không tìm thấy route phù hợp
        self._send_json(404, {"ok": False, "error": f"Route not found: {path}"})

    def _send_json(self, status, payload):
        """Helper gửi response JSON."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

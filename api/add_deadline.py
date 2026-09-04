import os, sys, json
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.external_api import verify_api_key, handle_add_deadline

DATABASE_URL = os.environ.get('DATABASE_URL')


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8')
        api_key = self.headers.get('X-API-Key', '')

        if not verify_api_key(api_key):
            self._send(401, {"ok": False, "error": "API key không hợp lệ hoặc thiếu."})
            return

        status, result = handle_add_deadline(body, DATABASE_URL)
        self._send(status, result)

    def _send(self, status, payload):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))

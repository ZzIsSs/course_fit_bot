import os
import sys
import mimetypes
from urllib.parse import urlparse
from http.server import HTTPServer

if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Nạp .env
from dotenv import load_dotenv
load_dotenv()

# Thêm root vào sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from api.index import handler as ApiHandler

FRONTEND_DIST = os.path.join(ROOT_DIR, "frontend", "dist")


class UnifiedDevHandler(ApiHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Nếu là request API, để ApiHandler xử lý
        if path.startswith("/api"):
            super().do_GET()
            return

        # Phục vụ static frontend từ frontend/dist
        if os.path.exists(FRONTEND_DIST):
            rel_path = path.lstrip("/")
            file_path = os.path.join(FRONTEND_DIST, rel_path)

            if os.path.isfile(file_path):
                self._serve_file(file_path)
                return

            # Fallback về index.html cho SPA Routing
            index_path = os.path.join(FRONTEND_DIST, "index.html")
            if os.path.isfile(index_path):
                self._serve_file(index_path)
                return

        # Fallback về API health check nếu chưa build frontend
        super().do_GET()

    def _serve_file(self, file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_json(500, {"ok": False, "error": f"Lỗi đọc file tĩnh: {str(e)}"})


def main():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), UnifiedDevHandler)
    print(f"================================================================")
    print(f"🚀 Course FIT HCMUS Server đang chạy tại: http://localhost:{port}")
    print(f"📊 Web Dashboard: http://localhost:{port}/")
    print(f"⚡ API Health:    http://localhost:{port}/api/health")
    print(f"================================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng máy chủ.")


if __name__ == "__main__":
    main()

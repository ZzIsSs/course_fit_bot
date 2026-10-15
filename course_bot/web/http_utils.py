"""Tiện ích HTTP dùng chung cho router: đọc body, CORS, gửi JSON."""
import json
from datetime import datetime


def json_serializer(obj):
    """JSON serializer cho các đối tượng datetime."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def read_body(handler):
    """Đọc toàn bộ body request (theo Content-Length) dưới dạng chuỗi UTF-8."""
    return handler.rfile.read(int(handler.headers.get("Content-Length", 0))).decode("utf-8")


def set_cors_headers(handler):
    """Thiết lập CORS headers cho phép gọi từ localhost:5173 và production."""
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key, X-Signature-Ed25519, X-Signature-Timestamp")


def send_json(handler, status, payload):
    """Gửi response JSON có CORS và encoding chuẩn."""
    handler.send_response(status)
    set_cors_headers(handler)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps(payload, ensure_ascii=False, default=json_serializer).encode("utf-8"))

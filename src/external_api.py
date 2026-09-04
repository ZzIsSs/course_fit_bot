"""Xử lý request thêm deadline từ bên thứ 3 (Zapier, Google Form/Apps Script, script ngoài...).

Xác thực bằng API key tĩnh (header X-API-Key) — khác cơ chế chữ ký Discord
dùng cho api/interactions.py.
"""
import os
import hmac
import uuid
import json

from src.database import get_db
from src.db_queries import get_or_create_course, insert_deadline_manual
from src.utils import parse_due_time
from src.config import LOCAL_TZ

EXTERNAL_API_KEY = os.environ.get('EXTERNAL_API_KEY')

# Giới hạn độ dài "id" bên thứ 3 gửi lên, để "external-{id}" không vượt quá
# cột lms_deadlines_id varchar(50) trong DB.
_MAX_EXT_ID_LEN = 40


def verify_api_key(provided_key):
    """So sánh API key theo constant-time để tránh timing attack."""
    if not EXTERNAL_API_KEY or not provided_key:
        return False
    return hmac.compare_digest(provided_key, EXTERNAL_API_KEY)


def handle_add_deadline(body_text, database_url):
    """Parse JSON body và ghi deadline vào DB.

    Body JSON kỳ vọng:
        {
          "ten": "Nộp báo cáo tuần",
          "han_chot": "25/12/2026 23:59"  (hoặc "25/12/2026" -> mặc định 23:59),
          "mon": "CSC10014",
          "nguon": "Google Form",            // tuỳ chọn, hiển thị ở added_by
          "id": "form-response-abc123"       // tuỳ chọn, chống ghi trùng nếu gọi lại
        }

    Trả về: (status_code, response_dict)
    """
    try:
        data = json.loads(body_text)
    except (json.JSONDecodeError, TypeError):
        return 400, {"ok": False, "error": "Body không phải JSON hợp lệ."}

    if not isinstance(data, dict):
        return 400, {"ok": False, "error": "Body JSON phải là một object."}

    ten = (data.get('ten') or '').strip()
    han_chot_raw = (data.get('han_chot') or '').strip()
    mon = (data.get('mon') or '').strip().upper()
    nguon = (data.get('nguon') or 'External API').strip()
    ext_id = (data.get('id') or '').strip()[:_MAX_EXT_ID_LEN]

    if not ten or not han_chot_raw or not mon:
        return 400, {"ok": False, "error": "Thiếu trường bắt buộc: ten, han_chot, mon."}

    due_time = parse_due_time(han_chot_raw, LOCAL_TZ)
    if due_time is None:
        return 400, {"ok": False, "error": "han_chot sai định dạng. VD: '25/12/2026 23:59' hoặc '25/12/2026'."}

    # Chống trùng: dùng id bên thứ 3 gửi nếu có, không thì tự sinh uuid
    lms_id = f"external-{ext_id}" if ext_id else f"external-{uuid.uuid4()}"

    with get_db(database_url) as conn:
        courses_id = get_or_create_course(conn, mon)
        deadlines_id = insert_deadline_manual(
            conn, courses_id, ten, lms_id, due_time,
            source_url=f"API bên thứ 3 ({nguon})",
            added_by=nguon,
            source='external',
        )

    if deadlines_id is None:
        return 200, {"ok": True, "duplicate": True, "message": "Deadline này đã tồn tại, bỏ qua trùng lặp."}

    return 201, {
        "ok": True,
        "deadlines_id": deadlines_id,
        "mon": mon,
        "han_chot_utc": due_time.isoformat(),
    }

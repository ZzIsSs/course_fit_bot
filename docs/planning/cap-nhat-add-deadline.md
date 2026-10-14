# Cập nhật: Mặc định giờ 23:59 + API bên thứ 3 cho `add_deadline`

**Ngày:** 03/09/2026
**Phạm vi:** 2 thay đổi Nguyên yêu cầu, đã viết code + **kiểm tra chạy thực tế** (không chỉ đọc mắt) trước khi giao.

---

## ✅ Đã kiểm tra bằng cách nào

Toàn bộ code dưới đây được dựng lại trong môi trường sandbox, chạy qua:
- `py_compile` toàn bộ file → không lỗi cú pháp.
- Import thực tế tất cả module (`pynacl`, `psycopg2` thật) → không lỗi circular import / thiếu dependency.
- **11 test case logic** cho `parse_due_time` (đủ giờ / thiếu giờ / sai định dạng / khoảng trắng thừa / ngày-tháng không hợp lệ).
- **8 test case** cho endpoint API bên thứ 3 (request hợp lệ, thiếu trường, sai định dạng ngày, trùng lặp, JSON hỏng, JSON sai kiểu, xác thực API key, và **id quá dài bị cắt để không vỡ cột DB**).
- Test tích hợp `_handle_add_deadline` (lệnh `/add_deadline` trên Discord) với input chỉ có ngày, không có giờ → xác nhận tự động ra `23:59` và **không ghi DB** khi input sai.

Kết quả: **tất cả pass**, không phát hiện lỗi cần sửa thêm so với bản đề xuất trước đó — chỉ có 1 điều chỉnh nhỏ được thêm vào lúc kiểm tra (giới hạn độ dài `id` bên thứ 3 gửi lên, xem mục 2.3 bên dưới) để tránh lỗi tiềm ẩn khi ghi DB.

---

## 1. Deadline không ghi giờ → tự động 23:59

### 1.1 `src/utils.py` — thêm hàm `parse_due_time` (giữ nguyên `ensure_tz` cũ)

Đổi dòng import đầu file, và thêm hàm mới vào cuối file:

```python
from datetime import timezone, datetime


def ensure_tz(dt):
    """Đảm bảo datetime có timezone (mặc định UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def parse_due_time(text, local_tz):
    """Parse chuỗi hạn chót người dùng nhập, hỗ trợ có hoặc không có giờ.

    Định dạng hỗ trợ (giờ theo local_tz):
        'dd/mm/yyyy HH:MM'  'dd/mm HH:MM'   (có giờ)
        'dd/mm/yyyy'        'dd/mm'         (không giờ -> mặc định 23:59)

    Trả về datetime UTC, hoặc None nếu không parse được.
    """
    text = text.strip()
    now_local = datetime.now(local_tz)
    formats = (
        ("%d/%m/%Y %H:%M", True, True),
        ("%d/%m %H:%M", False, True),
        ("%d/%m/%Y", True, False),
        ("%d/%m", False, False),
    )
    for fmt, has_year, has_time in formats:
        try:
            dt = datetime.strptime(text, fmt)
            if not has_year:
                dt = dt.replace(year=now_local.year)
            if not has_time:
                dt = dt.replace(hour=23, minute=59)
            return dt.replace(tzinfo=local_tz).astimezone(timezone.utc)
        except ValueError:
            continue
    return None
```

### 1.2 `src/interactions.py` — dùng hàm chung thay vì `_parse_due_time` cục bộ

- **Xoá hẳn** định nghĩa `def _parse_due_time(text): ...` cũ trong file.
- Sửa import:
  ```python
  from src.utils import ensure_tz, parse_due_time
  from src.config import LOCAL_TZ
  ```
- Sửa dòng gọi trong `_handle_add_deadline`:
  ```python
  due_time = parse_due_time(_get_option(options, 'han_chot') or '', LOCAL_TZ)
  ```
- Sửa thông báo lỗi cho rõ:
  ```python
  if not name or due_time is None:
      return _ephemeral(
          "❌ Hạn chót sai định dạng. Ví dụ: `25/12/2026 23:59` "
          "hoặc chỉ `25/12/2026` (bot tự set 23:59)."
      )
  ```

### 1.3 `scripts/register_commands.py` — cập nhật mô tả option

```python
{"name": "han_chot", "description": "dd/mm/yyyy HH:MM (bỏ giờ = mặc định 23:59)", "type": 3, "required": True},
```

> ⚠️ Sau khi sửa, cần chạy lại `python scripts/register_commands.py` **1 lần** để Discord cập nhật mô tả lệnh mới (không bắt buộc để tính năng hoạt động, chỉ để hiển thị đúng gợi ý khi gõ lệnh).

### 1.4 Kết quả test thực tế

| Input | Kết quả (UTC) | Ghi chú |
|---|---|---|
| `25/12/2026 23:59` | `2026-12-25 16:59:00+00:00` | Đủ ngày + giờ |
| `25/12 23:59` | `2026-12-25 16:59:00+00:00` | Thiếu năm → tự lấy năm hiện tại |
| `25/12/2026` | `2026-12-25 16:59:00+00:00` | **Thiếu giờ → tự động 23:59 (16:59 UTC = 23:59 GMT+7)** |
| `25/12` | `2026-12-25 16:59:00+00:00` | Thiếu cả năm lẫn giờ |
| `  25/12/2026  ` | `2026-12-25 16:59:00+00:00` | Tự strip khoảng trắng thừa |
| `2026-12-25` | `None` | Sai định dạng (dùng `-` thay vì `/`) |
| `32/12/2026` | `None` | Ngày không hợp lệ |
| `25/13/2026` | `None` | Tháng không hợp lệ |
| `` (rỗng) | `None` | — |

---

## 2. API endpoint cho bên thứ 3 (Zapier, Google Form, script ngoài...)

### 2.1 Kiến trúc

Endpoint **tách biệt hoàn toàn** khỏi `/api/interactions` (endpoint đó bắt buộc chữ ký Discord, bên thứ 3 không ký được). Endpoint mới dùng **API key tĩnh** trong header `X-API-Key`, ghi thẳng vào bảng `deadlines` với `source='external'`. Cron `main.py` **không cần sửa gì** — đã tự nhặt mọi deadline có `source != 'moodle'` lên xử lý.

### 2.2 `src/db_queries.py` — 2 thay đổi nhỏ trong file hiện có

**Chỉ sửa 2 hàm này**, không đụng gì khác trong file:

```python
def insert_deadline_manual(conn, courses_id, deadline_name, lms_deadlines_id, due_time, source_url, added_by, source='manual'):
    """ON CONFLICT DO NOTHING: an toàn nếu request bị gửi lặp (retry)."""
    row = fetch_one(conn,
        """INSERT INTO deadlines (courses_id, deadline_name, lms_deadlines_id, due_time, source_url, source, added_by)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (lms_deadlines_id) DO NOTHING
           RETURNING deadlines_id""",
        (courses_id, deadline_name, lms_deadlines_id, due_time, source_url, source, added_by))
    return row['deadlines_id'] if row else None


def get_pending_manual_deadlines(conn):
    """Deadline thêm thủ công (Discord /add_deadline hoặc API bên thứ 3),
    chưa từng được cron xử lý lần đầu."""
    return fetch_all(conn,
        """SELECT d.*, c.course_name
           FROM deadlines d
           JOIN courses c ON d.courses_id = c.courses_id
           WHERE d.source != 'moodle' AND d.notified_new = false""")
```

*(Thay đổi: thêm tham số `source='manual'` mặc định — lời gọi cũ từ `interactions.py` không cần sửa gì vẫn chạy đúng; đổi điều kiện `WHERE` từ `source = 'manual'` thành `source != 'moodle'` để cron nhặt luôn cả deadline `source='external'`.)*

### 2.3 `src/external_api.py` (file mới)

```python
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
```

### 2.4 `api/add_deadline.py` (file mới) — entry point Vercel

```python
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
```

### 2.5 Kết quả test thực tế (8/8 pass)

| # | Test case | Input rút gọn | Kết quả |
|---|---|---|---|
| 1 | Request hợp lệ đầy đủ | `ten, han_chot: "25/12/2026", mon: "csc10014"` | `201`, tự viết hoa môn thành `CSC10014`, `source='external'` |
| 2 | Thiếu trường bắt buộc | thiếu `han_chot` | `400`, báo rõ thiếu trường nào |
| 3 | Sai định dạng ngày | `han_chot: "ngay-mai"` | `400` |
| 4 | Trùng lặp (gọi lại cùng `id`) | `id: "DUPLICATE"` | `200`, `duplicate: true`, không tạo dòng mới |
| 5 | JSON hỏng | `"khong phai json"` | `400` |
| 6 | Body JSON không phải object | `[1,2,3]` | `400` |
| 7 | Xác thực API key | key đúng/sai/rỗng/`None` | Đúng logic, dùng `hmac.compare_digest` chống timing attack |
| 8 | `id` quá dài (100 ký tự) | — | Tự cắt còn ≤ 50 ký tự trước khi ghi DB, **không vỡ cột `varchar(50)`** |

### 2.6 Việc cần làm để đưa vào hoạt động

1. [ ] Tạo API key ngẫu nhiên: `openssl rand -hex 32` (hoặc cách tạo chuỗi random dài bất kỳ).
2. [ ] Vercel → Settings → Environment Variables → thêm **`EXTERNAL_API_KEY`** = chuỗi vừa tạo.
3. [ ] Deploy lại — Vercel tự nhận `api/add_deadline.py` thành endpoint `https://<project>.vercel.app/api/add_deadline`.
4. [ ] Test bằng `curl`:
   ```bash
   curl -X POST https://<project>.vercel.app/api/add_deadline \
     -H "Content-Type: application/json" \
     -H "X-API-Key: <EXTERNAL_API_KEY của Nguyên>" \
     -d '{"ten":"Nộp báo cáo tuần","han_chot":"25/12/2026","mon":"CSC10014","nguon":"Google Form"}'
   ```
   Kỳ vọng: HTTP `201`, JSON có `deadlines_id`.
5. [ ] Kết nối Zapier/Google Apps Script/n8n: cấu hình webhook POST tới URL trên, header `X-API-Key` gắn cứng trong phần cấu hình bảo mật (không log ra public).
6. [ ] Chạy `python main.py` (hoặc `workflow_dispatch` mode `notify`) → xác nhận deadline `source='external'` được cron nhặt lên, gửi tin + tạo channel/thread/event như deadline thường.

### 2.7 Lưu ý bảo mật

API key này cho phép **bất kỳ ai có key** tạo deadline cho **bất kỳ môn nào** — không giới hạn phạm vi theo môn/người dùng. Với quy mô cá nhân/nhóm nhỏ thì ổn, nhưng:
- Không để lộ key ra chỗ public (URL Zapier chia sẻ công khai, commit lên GitHub, ảnh chụp màn hình...).
- Nếu nghi ngờ lộ key, đổi `EXTERNAL_API_KEY` trên Vercel là vô hiệu hoá ngay các tích hợp cũ (cần cập nhật lại key ở phía Zapier/Form).

---

## Checklist tổng hợp cả 2 thay đổi

1. [ ] Áp code mục 1.1–1.3 (mặc định 23:59) vào `src/utils.py`, `src/interactions.py`, `scripts/register_commands.py`.
2. [ ] Áp code mục 2.2–2.4 (API bên thứ 3) vào `src/db_queries.py` (2 hàm), thêm mới `src/external_api.py`, `api/add_deadline.py`.
3. [ ] Chạy `python main.py --progress` cục bộ để chắc chắn không lỗi import sau khi sửa `db_queries.py`.
4. [ ] Set `EXTERNAL_API_KEY` trên Vercel, deploy lại.
5. [ ] Test `/add_deadline` trên Discord với `han_chot` chỉ có ngày → xác nhận tin nhắn xác nhận hiện đúng `23:59`.
6. [ ] Test endpoint `/api/add_deadline` bằng `curl` như hướng dẫn mục 2.6 bước 4.
7. [ ] Chạy `python scripts/register_commands.py` 1 lần để cập nhật mô tả lệnh mới trên Discord.

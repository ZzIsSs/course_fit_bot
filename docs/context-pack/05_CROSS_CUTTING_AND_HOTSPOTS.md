# PHẦN 5: CROSS-CUTTING CONCERNS & ĐIỂM NÓNG KỸ THUẬT

> **File:** `05_CROSS_CUTTING_AND_HOTSPOTS.md`  
> **Ngữ cảnh sử dụng:** Đánh giá an toàn thông tin, quản lý tài nguyên cơ sở dữ liệu và kiểm kê toàn bộ nợ kỹ thuật (technical debt) trong mã nguồn.

---

## 1. Cơ chế Authentication & Authorization

Hệ thống sử dụng các cơ chế bảo vệ phân tách tùy thuộc vào kênh giao tiếp:

```text
Kênh giao tiếp               Phương thức xác thực                    Thư viện / Cơ chế
├── Discord Slash Commands   ├── Chữ ký số Ed25519                  ├── PyNaCl (VerifyKey)
├── External Webhooks        ├── Khóa tĩnh (X-API-Key)              ├── hmac.compare_digest
├── Discord Bot API          ├── Bearer Bot Token                   ├── Authorization: Bot <TOKEN>
├── Moodle REST API          ├── Web Service Token                  ├── wstoken query parameter
├── Google Calendar API      ├── Service Account OAuth2 JWT         ├── google.oauth2.service_account
├── Notion API               ├── Bearer Integration Token           ├── Authorization: Bearer <TOKEN>
└── Web Dashboard REST       └── Hiện tại: CÔNG KHAI (Unprotected)  └── CORS: *
```

### Chi tiết kỹ thuật:
1. **Discord Interactions (`api/interactions.py` -> `src/interactions.py`):**
   * Sử dụng thuật toán mã hóa bất đối xứng **Ed25519**.
   * Yêu cầu 2 headers: `X-Signature-Ed25519` và `X-Signature-Timestamp`.
   * Sử dụng `VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY)).verify(f'{timestamp}{body}'.encode(), bytes.fromhex(signature))` để chứng thực request thực sự đến từ máy chủ Discord. Nếu thất bại, lập tức ngắt với HTTP 401.
2. **Third-Party Ingestion Webhook (`api/add_deadline.py` -> `src/external_api.py`):**
   * Xác thực qua header `X-API-Key`.
   * Dùng hàm `hmac.compare_digest(provided_key, EXTERNAL_API_KEY)` nhằm chống tấn công **Timing Attack** (so sánh chuỗi với thời gian thực thi hằng số).
3. **Google Service Account Credentials (`src/google_calendar_sync.py`):**
   * Hỗ trợ nạp credentials linh hoạt từ JSON thô, chuỗi Base64 (`GOOGLE_SERVICE_ACCOUNT_JSON`), hoặc đường dẫn file (`GOOGLE_SERVICE_ACCOUNT_FILE`).
4. ⚠️ **Điểm nóng an ninh (Web Dashboard Endpoints):**
   * Toàn bộ các endpoints nghiệp vụ trong [`api/index.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/api/index.py) phục vụ Dashboard (`GET /api/courses`, `GET /api/deadlines`, `GET /api/stats`, `POST /api/deadlines`, `POST /api/deadlines/toggle`) **chưa được bảo vệ bởi bất kỳ cơ chế xác thực nào** (không có Session/Cookie, không có JWT bearer).
   * Headers phản hồi đang cho phép mọi domain (`Access-Control-Allow-Origin: *`). Bất kỳ ai biết được domain Vercel đều có thể thực hiện thao tác tick hoàn thành hoặc tạo deadline rác.

---

## 2. Quản lý kết nối Database & Async Pool

* **Driver & Cơ chế kết nối:**
  * Toàn bộ truy vấn sử dụng thư viện đồng bộ `psycopg2-binary`.
  * Được quản lý tập trung thông qua Context Manager `get_db(database_url)` trong [`src/database.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/database.py).
  * Quy trình thực thi:
    ```python
    @contextmanager
    def get_db(database_url):
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    ```
* ⚠️ **Điểm nóng kiến trúc trong môi trường Serverless:**
  * **Thiếu Connection Pooling:** Dự án mở và đóng kết nối TCP mới cho mỗi request HTTP trên Vercel.
  * Khi có đợt truy cập đồng thời vào Web Dashboard hoặc webhook bắn liên tục, số lượng kết nối tức thời có thể vượt quá ngưỡng `max_connections` của gói miễn phí Supabase (thường là 60-100 connections).
  * **Khuyến nghị kiến trúc:** Bắt buộc cấu hình `DATABASE_URL` trỏ vào **Transaction Pooler (Supavisor / PgBouncer trên cổng 6543)** của Supabase thay vì cổng direct connection `5432`.

---

## 3. Rà soát Nợ kỹ thuật (Technical Debt Scan)

### 3.1 Kiểm tra chú thích mã nguồn (`TODO`, `FIXME`, `HACK`)
* **Kết quả:** Không có bất kỳ thẻ `TODO`, `FIXME` hay `HACK` nào trong toàn bộ mã nguồn logic của dự án. Mã nguồn sạch, không lưu lại các đánh dấu nợ kỹ thuật dang dở.

### 3.2 Kiểm tra các lệnh `pass`
* [`src/config.py:24`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/config.py#L24):
  ```python
  try:
      from dotenv import load_dotenv
      load_dotenv()
  except ImportError:
      pass  # Bỏ qua an toàn trên GitHub Actions / Vercel
  ```
* [`scripts/notion_helper.py:16`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/scripts/notion_helper.py#L16), [`179`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/scripts/notion_helper.py#L179): Sử dụng trong script tiện ích console để bỏ qua lỗi import và lỗi prompt tương tác.
* [`scripts/run_server.py:11`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/scripts/run_server.py#L11): Bỏ qua lỗi import dotenv khi chạy dev server cục bộ.

### 3.3 Kiểm tra các khối bắt Exception rỗng / Nuốt lỗi
1. [`frontend/src/api/client.ts:19`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/frontend/src/api/client.ts#L19):
   ```typescript
   const errJson = await res.json().catch(() => null);
   ```
   * *Đánh giá:* **Hợp lý.** Dùng để tránh crash khi server phản hồi mã lỗi HTTP với định dạng text/plain thay vì JSON.
2. [`api/index.py:152`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/api/index.py#L152) & [`api/index.py:192`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/api/index.py#L192):
   ```python
   try:
       data = json.loads(body)
   except Exception:
       self._send_json(400, {"ok": False, "error": "Body không phải JSON hợp lệ."})
       return
   ```
   * *Đánh giá:* **An toàn.** Bắt lỗi parse body nhưng trả về mã lỗi 400 rõ ràng cho client.
3. [`src/interactions.py:30`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/interactions.py#L30):
   ```python
   except (BadSignatureError, Exception):
       return False
   ```
   * *Đánh giá:* **Chuẩn bảo mật.** Trả về `False` khi chữ ký không hợp lệ, ngăn chặn việc rò rỉ stack trace ra ngoài.
4. **Cô lập lỗi tích hợp ngoại vi (Resilience Pattern by Design):**
   * Trong [`src/google_calendar_sync.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/google_calendar_sync.py) và [`src/notion_sync.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/notion_sync.py), các hàm gọi API đều bọc trong `try...except Exception as e` và chỉ log `logging.warning()`.
   * *Đánh giá:* **Quyết định thiết kế chính xác.** Sự cố mạng hoặc lỗi quota từ Notion/Google Calendar không được phép làm gián đoạn chu trình chính: thông báo Discord và cập nhật database.

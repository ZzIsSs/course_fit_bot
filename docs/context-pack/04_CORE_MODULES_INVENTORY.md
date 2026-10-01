# PHẦN 4: BẢN ĐỒ CÁC MODULE TRỌNG YẾU (CORE MODULES INVENTORY)

> **File:** `04_CORE_MODULES_INVENTORY.md`  
> **Ngữ cảnh sử dụng:** Bảng danh mục chi tiết các file/module cốt lõi, trách nhiệm, số dòng mã (LOC) và độ phức tạp kỹ thuật.

---

## 1. Bảng kiểm kê Module cốt lõi (Core Modules Table)

| Tên File / Module | Trách nhiệm chính | Ước tính LOC | Mức độ phức tạp | Các hàm / Lớp chủ chốt |
| :--- | :--- | :---: | :---: | :--- |
| [`src/app.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/app.py) | Điều phối luồng xử lý toàn cục (Orchestrator): quét deadline, gửi thông báo theo cấp bậc, nhắc hạn 3 ngày/1 ngày, tổng kết hàng ngày, đồng bộ kênh Discord, đồng bộ Notion & Google Calendar. | 629 | **Cao** | `run_main_bot()`, `send_daily_summary()`, `send_progress_report()`, `sync_channels()`, `sync_notion()`, `sync_google_calendar()` |
| [`src/discord_api.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/discord_api.py) | Client Discord REST API v10: tạo/đổi tên kênh, tạo/resolve Category, gửi tin nhắn, thêm/quét reaction, tạo Scheduled Event, cơ chế retry tự động khi gặp Rate Limit (429), quét và dọn dẹp tin nhắn lặp. | 478 | **Cao** | `_request_with_retry()`, `send_message()`, `create_channel()`, `resolve_category()`, `create_scheduled_event()`, `deduplicate_channel_messages()` |
| [`src/db_queries.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/db_queries.py) | Tầng Data Access Object (DAO): chứa toàn bộ các câu lệnh SQL thuần cho `courses`, `deadlines`, `course_modules`, `forum_discussions`, thống kê dashboard. | 376 | **Trung bình** | `get_or_create_course()`, `insert_deadline()`, `insert_deadline_manual()`, `toggle_deadline_completed()`, `get_dashboard_stats()` |
| [`src/announcement_tracker.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/announcement_tracker.py) | Service theo dõi nội dung khóa học trên Moodle: quét cây nội dung, phát hiện bài giảng, slide, quiz mới hoặc bài đăng mới trên diễn đàn. | 303 | **Trung bình** | `check_moodle_updates()` |
| [`src/google_calendar_sync.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/google_calendar_sync.py) | Adapter tích hợp Google Calendar API v3: xác thực Service Account, chống trùng qua `extendedProperties`, đặt 3 mốc thông báo đẩy, cập nhật màu xanh và tiêu đề khi hoàn thành. | 284 | **Trung bình** | `GoogleCalendarSync`, `upsert_deadline()`, `mark_completed()`, `_parse_credentials()` |
| [`src/notion_sync.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/notion_sync.py) | Adapter tích hợp Notion REST API: tự động nhận diện schema database Notion (Dynamic schema inspection), tạo todo item và đồng bộ trạng thái tick hoàn thành hai chiều. | 250 | **Trung bình** | `NotionSync`, `_inspect_schema()`, `upsert_deadline()`, `mark_completed()` |
| [`src/moodle_parser.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/moodle_parser.py) | Tiện ích xử lý dữ liệu Moodle: phân tích iCalendar ICS, trích xuất mã môn, tính toán học kỳ hiện tại, loại bỏ dấu tiếng Việt và sinh slug tên kênh Discord. | 245 | **Trung bình** | `fetch_and_parse_events()`, `slugify_channel_name()`, `extract_subject()`, `get_current_semester()`, `extract_semester_index()` |
| [`api/index.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/api/index.py) | API Gateway thống nhất trên Vercel Serverless: xử lý CORS, phân luồng HTTP GET/POST cho Web Dashboard, Discord Webhook và Third-party Webhook. | 194 | **Trung bình** | `handler(BaseHTTPRequestHandler)`, `do_GET()`, `do_POST()`, `do_OPTIONS()` |
| [`src/interactions.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/interactions.py) | Xử lý Discord Interactions (Slash Commands): xác thực chữ ký mật mã Ed25519 bằng PyNaCl, phân phối xử lý lệnh `/add_deadline` và `/deadline`. | 105 | **Trung bình** | `verify_signature()`, `handle_interaction()`, `_handle_add_deadline()`, `_handle_deadline()` |
| [`src/moodle_api.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/moodle_api.py) | Client gọi API Moodle Web Services: ngụy trang User-Agent vượt WAF trường, lấy thông tin user, danh sách khóa học tham gia và bài đăng diễn đàn. | 93 | **Thấp** | `_call_api()`, `get_site_info()`, `get_enrolled_courses()`, `get_course_contents()`, `get_forum_discussions()` |
| [`src/external_api.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/external_api.py) | Xử lý request thêm deadline từ bên ngoài (Google Forms, Zapier): xác thực HMAC constant-time bằng `X-API-Key`, parse JSON và lưu vào DB. | 67 | **Thấp** | `verify_api_key()`, `handle_add_deadline()` |
| [`src/config.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/config.py) | Đọc, validate các biến môi trường cấu hình, thiết lập logging chuẩn và timezone mặc định UTC+7. | 59 | **Thấp** | `load_env()`, `LOCAL_TZ`, `DISCORD_API_BASE` |
| [`src/database.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/database.py) | Quản lý kết nối PostgreSQL qua psycopg2: cung cấp context manager `get_db()` tự động commit/rollback và đóng kết nối an toàn. | 53 | **Thấp** | `get_db()`, `execute()`, `fetch_one()`, `fetch_all()` |
| [`src/event_tracker.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/event_tracker.py) | Kiểm tra reaction `✅` trên tin nhắn Discord, kích hoạt chuỗi cập nhật hoàn thành trên DB, Discord Scheduled Event, Notion và Google Calendar. | 32 | **Thấp** | `check_completions()` |
| [`src/utils.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/src/utils.py) | Tiện ích phân tích hạn chót linh hoạt (`parse_due_time`) và gán múi giờ UTC (`ensure_tz`). | 32 | **Thấp** | `ensure_tz()`, `parse_due_time()` |

---

## 2. Danh mục Frontend Web Dashboard Module

| File / Component | Trách nhiệm chính | LOC | Mức độ phức tạp |
| :--- | :--- | :---: | :---: |
| [`frontend/src/App.tsx`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/frontend/src/App.tsx) | Root Component: quản lý state toàn cục, filter theo môn học/trạng thái, điều hướng tab view. | 376 | **Trung bình** |
| [`frontend/src/features/deadlines/AddDeadlineModal.tsx`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/frontend/src/features/deadlines/AddDeadlineModal.tsx) | Form thêm deadline thủ công với autocomplete môn học, date-picker và validation. | 235 | **Trung bình** |
| [`frontend/src/features/deadlines/DeadlineListView.tsx`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/frontend/src/features/deadlines/DeadlineListView.tsx) | Danh sách deadline hiển thị dạng bảng/card với hành động tick hoàn thành. | 134 | **Thấp** |
| [`frontend/src/features/deadlines/DeadlineKanbanView.tsx`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/frontend/src/features/deadlines/DeadlineKanbanView.tsx) | Giao diện Kanban kéo thả/phân cột: Cần làm (Todo), Khẩn cấp (< 24h), Đã xong (Done). | 92 | **Thấp** |
| [`frontend/src/api/client.ts`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/frontend/src/api/client.ts) | HTTP Client bọc fetch an toàn kèm xử lý AbortController và định kiểu TypeScript. | 106 | **Thấp** |
| [`frontend/src/utils/dateUtils.ts`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/frontend/src/utils/dateUtils.ts) | Tiện ích tính thời gian còn lại (countdown), định dạng ngày tiếng Việt, phân loại độ khẩn cấp. | 128 | **Thấp** |

# PHẦN 4: BẢN ĐỒ CÁC MODULE TRỌNG YẾU (CORE MODULES INVENTORY)

> **Cập nhật 2026-10-16:** đường dẫn và cây thư mục trong tài liệu này đã được cập nhật theo cấu trúc sau đợt tái cấu trúc (`course_bot/`, `frontend/src/{app,features,shared}`). Xem `docs/architecture/refactoring-blueprint.md`.

> **File:** `04_CORE_MODULES_INVENTORY.md`  
> **Ngữ cảnh sử dụng:** Bảng danh mục chi tiết các file/module cốt lõi, trách nhiệm, số dòng mã (LOC) và độ phức tạp kỹ thuật.

---

## 1. Bảng kiểm kê Module cốt lõi (Core Modules Table)

| Tên File / Module | Trách nhiệm chính | Ước tính LOC | Mức độ phức tạp | Các hàm / Lớp chủ chốt |
| :--- | :--- | :---: | :---: | :--- |
| [`course_bot/jobs/`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/course_bot/jobs/) | Điều phối luồng xử lý toàn cục (Orchestrator): quét deadline, gửi thông báo theo cấp bậc, nhắc hạn 3 ngày/1 ngày, tổng kết hàng ngày, đồng bộ kênh Discord, đồng bộ Notion & Google Calendar. | 791 | **Cao** | `run_main_bot()`, `send_daily_summary()`, `send_progress_report()`, `sync_channels()`, `sync_notion()`, `sync_google_calendar()` |
| [`course_bot/integrations/discord/rest.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/course_bot/integrations/discord/rest.py) | Client Discord REST API v10: tạo/đổi tên kênh, tạo/resolve Category, gửi tin nhắn, thêm/quét reaction, tạo Scheduled Event, cơ chế retry tự động khi gặp Rate Limit (429), quét và dọn dẹp tin nhắn lặp. | 559 | **Cao** | `_request_with_retry()`, `send_message()`, `create_channel()`, `resolve_category()`, `create_scheduled_event()`, `deduplicate_channel_messages()` |
| [`course_bot/db/repositories/`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/course_bot/db/repositories/) | Tầng Data Access Object (DAO): chứa toàn bộ các câu lệnh SQL thuần cho `courses`, `deadlines`, `course_modules`, `forum_discussions`, thống kê dashboard. | 501 | **Trung bình** | `get_or_create_course()`, `insert_deadline()`, `insert_deadline_manual()`, `toggle_deadline_completed()`, `get_dashboard_stats()` |
| [`course_bot/services/announcement_tracker.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/course_bot/services/announcement_tracker.py) | Service theo dõi nội dung khóa học trên Moodle: quét cây nội dung, phát hiện bài giảng, slide, quiz mới hoặc bài đăng mới trên diễn đàn. | 335 | **Trung bình** | `check_moodle_updates()` |
| [`course_bot/integrations/google_calendar/client.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/course_bot/integrations/google_calendar/client.py) | Adapter tích hợp Google Calendar API v3: xác thực Service Account, chống trùng qua `extendedProperties`, đặt 3 mốc thông báo đẩy, cập nhật màu xanh và tiêu đề khi hoàn thành. | 345 | **Trung bình** | `GoogleCalendarSync`, `upsert_deadline()`, `mark_completed()`, `_parse_credentials()` |
| [`course_bot/integrations/notion/client.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/course_bot/integrations/notion/client.py) | Adapter tích hợp Notion REST API: tự động nhận diện schema database Notion (Dynamic schema inspection), tạo todo item và đồng bộ trạng thái tick hoàn thành hai chiều. | 300 | **Trung bình** | `NotionSync`, `_inspect_schema()`, `upsert_deadline()`, `mark_completed()` |
| [`course_bot/integrations/moodle/ics_feed.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/course_bot/integrations/moodle/ics_feed.py) | Tiện ích xử lý dữ liệu Moodle: phân tích iCalendar ICS, trích xuất mã môn, tính toán học kỳ hiện tại, loại bỏ dấu tiếng Việt và sinh slug tên kênh Discord. | 58 | **Trung bình** | `fetch_and_parse_events()`, `slugify_channel_name()`, `extract_subject()`, `get_current_semester()`, `extract_semester_index()` |
| [`api/index.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/api/index.py) | API Gateway thống nhất trên Vercel Serverless: xử lý CORS, phân luồng HTTP GET/POST cho Web Dashboard, Discord Webhook và Third-party Webhook. | 10 | **Trung bình** | `handler(BaseHTTPRequestHandler)`, `do_GET()`, `do_POST()`, `do_OPTIONS()` |
| [`course_bot/web/routes/discord_interactions.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/course_bot/web/routes/discord_interactions.py) | Xử lý Discord Interactions (Slash Commands): xác thực chữ ký mật mã Ed25519 bằng PyNaCl, phân phối xử lý lệnh `/add_deadline` và `/deadline`. | 166 | **Trung bình** | `verify_signature()`, `handle_interaction()`, `_handle_add_deadline()`, `_handle_deadline()` |
| [`course_bot/integrations/moodle/webservice.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/course_bot/integrations/moodle/webservice.py) | Client gọi API Moodle Web Services: ngụy trang User-Agent vượt WAF trường, lấy thông tin user, danh sách khóa học tham gia và bài đăng diễn đàn. | 209 | **Thấp** | `_call_api()`, `get_site_info()`, `get_enrolled_courses()`, `get_course_contents()`, `get_forum_discussions()` |
| [`course_bot/web/routes/external.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/course_bot/web/routes/external.py) | Xử lý request thêm deadline từ bên ngoài (Google Forms, Zapier): xác thực HMAC constant-time bằng `X-API-Key`, parse JSON và lưu vào DB. | 98 | **Thấp** | `verify_api_key()`, `handle_add_deadline()` |
| [`course_bot/core/config.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/course_bot/core/config.py) | Đọc, validate các biến môi trường cấu hình, thiết lập logging chuẩn và timezone mặc định UTC+7. | 68 | **Thấp** | `load_env()`, `LOCAL_TZ`, `DISCORD_API_BASE` |
| [`course_bot/db/connection.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/course_bot/db/connection.py) | Quản lý kết nối PostgreSQL qua psycopg2: cung cấp context manager `get_db()` tự động commit/rollback và đóng kết nối an toàn. | 81 | **Thấp** | `get_db()`, `execute()`, `fetch_one()`, `fetch_all()` |
| [`course_bot/services/completion_tracker.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/course_bot/services/completion_tracker.py) | Kiểm tra reaction `✅` trên tin nhắn Discord, kích hoạt chuỗi cập nhật hoàn thành trên DB, Discord Scheduled Event, Notion và Google Calendar. | 43 | **Thấp** | `check_completions()` |
| [`course_bot/core/time_utils.py`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/course_bot/core/time_utils.py) | Tiện ích phân tích hạn chót linh hoạt (`parse_due_time`) và gán múi giờ UTC (`ensure_tz`). | 77 | **Thấp** | `ensure_tz()`, `parse_due_time()` |

---

## 2. Danh mục Frontend Web Dashboard Module

| File / Component | Trách nhiệm chính | LOC | Mức độ phức tạp |
| :--- | :--- | :---: | :---: |
| [`frontend/src/app/App.tsx`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/frontend/src/app/App.tsx) | Root Component: layout + điều hướng tab. Dữ liệu nằm ở `app/useDashboardData.ts` và hook của từng feature (`useDeadlines`, `useDeadlineFilters`, ...). | 215 | **Trung bình** |
| [`frontend/src/features/deadlines/AddDeadlineModal.tsx`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/frontend/src/features/deadlines/AddDeadlineModal.tsx) | Form thêm deadline thủ công với autocomplete môn học, date-picker và validation. | 253 | **Trung bình** |
| [`frontend/src/features/deadlines/DeadlineListView.tsx`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/frontend/src/features/deadlines/DeadlineListView.tsx) | Danh sách deadline hiển thị dạng bảng/card với hành động tick hoàn thành. | 143 | **Thấp** |
| [`frontend/src/features/deadlines/DeadlineKanbanView.tsx`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/frontend/src/features/deadlines/DeadlineKanbanView.tsx) | Giao diện Kanban kéo thả/phân cột: Cần làm (Todo), Khẩn cấp (< 24h), Đã xong (Done). | 98 | **Thấp** |
| [`frontend/src/shared/api/client.ts`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/frontend/src/shared/api/client.ts) | HTTP Client bọc fetch an toàn kèm xử lý AbortController và định kiểu TypeScript. | 115 | **Thấp** |
| [`frontend/src/shared/utils/dateUtils.ts`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/frontend/src/shared/utils/dateUtils.ts) | Tiện ích tính thời gian còn lại (countdown), định dạng ngày tiếng Việt, phân loại độ khẩn cấp. | 142 | **Thấp** |

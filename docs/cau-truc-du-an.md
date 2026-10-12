# Cấu trúc thư mục dự án `course_fit_bot` (Phiên bản đầy đủ)
> **Dành cho:** Nguyên  
> **Cập nhật:** Đã bổ sung toàn bộ kiến trúc Serverless, Frontend Dashboard, và module Crawler Moodle mới.

---

Vui lòng tham khảo tài liệu chi tiết đầy đủ tại: **[`CAU_TRUC_DU_AN.md`](file:///e:/coder/OnlyC(ode)/Notification%20Project/CAU_TRUC_DU_AN.md)** ở thư mục gốc của dự án.

## 1. Sơ đồ phân cấp thư mục chính

```text
Notification Project/
├── .github/workflows/           # CI/CD: notify.yml (chạy mỗi 30p), daily_summary.yml (7h sáng)
├── api/                         # Vercel Serverless Functions: index.py, interactions.py, add_deadline.py
├── src/                         # Core Python Backend:
│   ├── app.py                   # Master Orchestrator (chạy luồng kiểm tra, thông báo, sync)
│   ├── moodle_deadline_crawler.py # Cào Assignment, Quiz, Event từ Moodle API & Auto-complete nộp bài
│   ├── moodle_api.py            # Client gọi Moodle Web Service API (wstoken)
│   ├── moodle_parser.py         # Parse ICS, trích xuất mã môn, tính học kỳ, slug tên kênh
│   ├── announcement_tracker.py  # Quét slide, tài liệu, bài giảng và bài đăng diễn đàn mới
│   ├── discord_api.py           # Discord REST API v10 client
│   ├── interactions.py          # Xử lý Slash Command /add_deadline, /deadline
│   ├── external_api.py          # Xử lý webhook bên thứ ba
│   ├── event_tracker.py         # Bắt reaction ✅ để đánh dấu hoàn thành
│   ├── google_calendar_sync.py  # Đồng bộ Google Calendar
│   ├── notion_sync.py           # Đồng bộ Notion Database
│   ├── database.py              # PostgreSQL Connection Context Manager
│   ├── db_queries.py            # DAO Queries
│   ├── config.py                # Environment configs & Timezone UTC+7
│   └── utils.py                 # Datetime parsing & timezone utilities
├── frontend/                    # Web Dashboard (React 18 + Vite + Tailwind CSS)
│   ├── src/components/          # UI components (Modal, Button, ProgressBar, Toast...)
│   ├── src/features/            # Deadlines (Kanban, List), Courses, Dashboard, Announcements
│   └── src/api/                 # API Client gọi Vercel backend
├── migrations/                  # Script CSDL PostgreSQL (Supabase): 001 -> 005
├── scripts/                     # Scripts hỗ trợ dev & vận hành
├── tests/                       # Unit tests & Integration tests
├── docs/                        # Tài liệu đặc tả kỹ thuật chi tiết
├── main.py                      # CLI Runner chính
├── requirements.txt             # Thư viện Python phụ thuộc
└── vercel.json                  # Cấu hình routing deploy Vercel
```

## 2. Bảng vai trò các module cốt lõi

| Module / Thư mục | Trách nhiệm chính |
| :--- | :--- |
| [`src/app.py`](file:///e:/coder/OnlyC(ode)/Notification%20Project/src/app.py) | Điều phối chu trình quét deadline, chuỗi nhắc 3 ngày / 1 ngày, gửi summary & progress report. |
| [`src/moodle_deadline_crawler.py`](file:///e:/coder/OnlyC(ode)/Notification%20Project/src/moodle_deadline_crawler.py) | Cào trực tiếp bài tập (`mod_assign`) và quiz (`mod_quiz`) từ Moodle API; tự động đánh dấu hoàn thành khi sinh viên nộp bài. |
| [`src/announcement_tracker.py`](file:///e:/coder/OnlyC(ode)/Notification%20Project/src/announcement_tracker.py) | Theo dõi tài liệu upload mới (slide, PDF) và bài viết diễn đàn. |
| [`src/discord_api.py`](file:///e:/coder/OnlyC(ode)/Notification%20Project/src/discord_api.py) | Tạo kênh, phân loại category theo học kỳ, gửi tin nhắn, tạo Scheduled Event. |
| [`api/index.py`](file:///e:/coder/OnlyC(ode)/Notification%20Project/api/index.py) | REST API phục vụ Web Dashboard hoạt động trên Vercel. |
| [`frontend/`](file:///e:/coder/OnlyC(ode)/Notification%20Project/frontend/) | Giao diện Web SPA quản trị bài tập (hỗ trợ kéo thả Kanban, lọc môn học). |

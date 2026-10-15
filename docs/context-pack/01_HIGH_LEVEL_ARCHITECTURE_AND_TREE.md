# PHẦN 1: CẤU TRÚC THƯ MỤC CẤP CAO & PHÂN TẦNG KIẾN TRÚC

> **Cập nhật 2026-10-16:** đường dẫn và cây thư mục trong tài liệu này đã được cập nhật theo cấu trúc sau đợt tái cấu trúc (`course_bot/`, `frontend/src/{app,features,shared}`). Xem `docs/architecture/refactoring-blueprint.md`.

> **File:** `01_HIGH_LEVEL_ARCHITECTURE_AND_TREE.md`  
> **Ngữ cảnh sử dụng:** Cung cấp cấu trúc dự án và sơ đồ phân tầng trách nhiệm các thư mục.

---

## 1. Cây thư mục cấp cao (High-Level Directory Tree)

Cây thư mục đại diện (độ sâu tối đa 3 cấp), đã loại trừ các thư mục rác, build artifacts, lock và cache (`node_modules`, `.git`, `venv`, `__pycache__`, `dist`, logs/locks):

```text
Notification Project/
├── .github/workflows/            # notify.yml (mỗi 30 phút), daily_summary.yml (06:55), ci.yml (test + build)
├── api/
│   └── index.py                  # Entry point Vercel duy nhất: re-export `handler` từ course_bot/web/router.py
├── course_bot/                   # Package backend (Python)
│   ├── cli.py                    # argparse: --summary, --progress, ... -> jobs/*
│   ├── core/                     # Tầng lá: config.py (env), logging_setup.py, time_utils.py (LOCAL_TZ, parse_due_time)
│   ├── domain/                   # Logic thuần, không I/O
│   │   ├── course_naming.py      # extract_subject, extract_display_name, slugify_channel_name
│   │   ├── semester.py           # get_current_semester, extract_semester_index
│   │   ├── reminders.py          # decide_reminder: NEW / 3_DAYS / 1_DAY
│   │   └── messages.py           # Mẫu tin nhắn deadline, build_event_url, sanitize_discord_text
│   ├── db/
│   │   ├── connection.py         # get_db, execute, fetch_one, fetch_all (psycopg2)
│   │   └── repositories/         # SQL theo bảng: courses, deadlines, moodle_content, notifications
│   ├── integrations/             # Client mỏng cho dịch vụ ngoài (không DB, không nghiệp vụ)
│   │   ├── discord/              # rest.py (REST v10, retry 429), signature.py (Ed25519)
│   │   ├── moodle/               # webservice.py (Moodle Web Services), ics_feed.py (tải + parse .ics)
│   │   ├── notion/client.py
│   │   └── google_calendar/client.py
│   ├── services/                 # Use-case dùng chung cho nhiều entry point
│   │   ├── channel_resolver.py   # Tìm / rename / tạo kênh môn trong category "kì N"
│   │   ├── manual_deadlines.py   # Chuẩn hoá + thêm deadline thủ công (Web, Discord, API bên thứ 3)
│   │   ├── completion_tracker.py # React ✅ -> đánh dấu hoàn thành
│   │   ├── deadline_crawler.py   # Thu thập assignment / quiz / calendar từ Moodle API, auto-complete
│   │   └── announcement_tracker.py # Phát hiện tài liệu / bài đăng diễn đàn mới
│   ├── jobs/                     # Runtime A (cron/CLI): mỗi chế độ của main.py một file
│   │   ├── notify.py             # (mặc định) quét deadline, gửi thông báo + nhắc nhở
│   │   ├── reports.py            # --summary, --progress
│   │   ├── announcements.py      # --announcements
│   │   ├── crawl_deadlines.py    # --crawl-deadlines
│   │   ├── sync_channels.py      # --sync-channels
│   │   ├── sync_external.py      # --sync-notion, --sync-gcal
│   │   └── dedup.py              # --dedup
│   └── web/                      # Runtime B (Vercel HTTP): không import jobs/, Notion, Google Calendar
│       ├── router.py             # BaseHTTPRequestHandler + điều hướng /api/*
│       ├── http_utils.py         # JSON, CORS, đọc body
│       └── routes/               # dashboard.py, discord_interactions.py (/interactions), external.py (/add_deadline)
├── frontend/                     # Web Dashboard (Vite + React + TypeScript + Tailwind)
│   └── src/
│       ├── app/                  # App.tsx, main.tsx, layout/ (Header, Sidebar, BottomNav), useDashboardData, useTheme
│       ├── features/             # announcements, courses, dashboard, deadlines, settings (view + hook dữ liệu)
│       ├── shared/               # ui/, api/client.ts, types/, utils/, hooks/
│       └── index.css
├── migrations/                   # SQL schema (001, 002, 004, 005; không có 003, xem NOTES.md)
├── scripts/                      # Công cụ chạy tay: python -m scripts.<nhóm>.<tên>
│   ├── ops/                      # register_commands, set_category, clean_bot_messages, rename_all_channels, ...
│   ├── dev/                      # run_server (API + dist local), start.ps1, check_url, dump_moodle_data, notion_helper
│   ├── debug/                    # Kiểm tra với token thật (gọi Discord / Moodle thật)
│   └── termux/setup_termux.sh    # Cài máy trạm Android (cron + 10 widget)
├── tests/                        # pytest: unit/ (core, domain, db, integrations, services, jobs, web) + smoke/bundle/import-direction
├── docs/                         # architecture/, guides/, planning/, design/, context-pack/
├── main.py                       # Entry point CLI (GitHub Actions, Termux): gọi course_bot.cli.main()
├── pyproject.toml / requirements.txt
├── vercel.json                   # Build frontend/, rewrite /api/* -> api/index.py
└── .vercelignore                 # Loại main.py, cli.py, jobs/, Notion, Google Calendar, scripts/, tests/, docs/ khỏi bundle
```

---

## 2. Phân tầng kiến trúc (Architectural Layers Breakdown)

Hệ thống được thiết kế theo mô hình lai (Hybrid Architecture) kết hợp **Layered Architecture** và **Ports & Adapters (Hexagonal)**:

| Tầng kiến trúc | Thư mục / File đại diện | Chức năng & Trách nhiệm chính |
| :--- | :--- | :--- |
| **1. Ingestion / Gateway Layer** | `api/index.py` (→ `course_bot/web/router.py`)<br/>`main.py` | Tiếp nhận tín hiệu từ các nguồn bên ngoài: HTTP request từ Vercel Serverless, Webhook từ Discord, Webhook từ Zapier/Google Form, và CLI invocation từ GitHub Actions runner. |
| **2. Presentation / UI Layer** | `frontend/src/` | Giao diện Web Dashboard React SPA dành cho người dùng cuối: hiển thị tiến độ hoàn thành, thống kê tỷ lệ, lọc danh sách deadline theo môn/trạng thái và form tạo deadline thủ công. |
| **3. Application / Orchestration Layer** | `course_bot/jobs/`<br/>`course_bot/services/completion_tracker.py` | Tầng điều phối trung tâm: quản lý vòng đời deadline (mới -> nhắc 3 ngày -> nhắc 1 ngày -> hoàn thành), điều phối các tiến trình kiểm tra định kỳ, đối soát reaction để hoàn thành nhiệm vụ. |
| **4. Domain & Business Services Layer** | `course_bot/domain/`<br/>`course_bot/services/`<br/>`course_bot/integrations/moodle/ics_feed.py`<br/>`course_bot/web/routes/discord_interactions.py`<br/>`course_bot/web/routes/external.py` | Chứa các quy tắc nghiệp vụ đặc thù: bóc tách dữ liệu ICS, quy tắc đặt tên kênh Discord (`nmttnt-csc10014`), bóc tách học kỳ từ category, kiểm tra thay đổi tài liệu môn học (`course_modules`). |
| **5. Infrastructure & Adapters Layer** | `course_bot/integrations/discord/rest.py`<br/>`course_bot/integrations/moodle/webservice.py`<br/>`course_bot/integrations/notion/client.py`<br/>`course_bot/integrations/google_calendar/client.py` | Đóng gói toàn bộ việc tương tác với các hệ sinh thái bên ngoài (Discord REST API v10, Moodle REST API, Notion API v1, Google Calendar API v3). Bảo vệ luồng chính khỏi lỗi ngoại vi. |
| **6. Persistence / Data Access Layer (DAO)** | `course_bot/db/connection.py`<br/>`course_bot/db/repositories/`<br/>`migrations/` | Quản lý kết nối PostgreSQL (Supabase), đóng gói toàn bộ các truy vấn SQL thuần thông qua các hàm có kiểu rõ ràng, không phụ thuộc ORM cồng kềnh. |
| **7. Cross-cutting / Config & Helpers** | `course_bot/core/config.py`<br/>`course_bot/core/time_utils.py` | Kiểm tra biến môi trường, thiết lập logging chuẩn, chuyển đổi múi giờ đồng nhất `Asia/Ho_Chi_Minh` (UTC+7). |
| **8. Operations & Maintenance** | `scripts/`<br/>`.github/workflows/` | Tự động hóa CI/CD, đăng ký Slash Commands, rename hàng loạt kênh, cấu hình phân nhóm học kỳ. |

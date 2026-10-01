# PHẦN 1: CẤU TRÚC THƯ MỤC CẤP CAO & PHÂN TẦNG KIẾN TRÚC

> **File:** `01_HIGH_LEVEL_ARCHITECTURE_AND_TREE.md`  
> **Ngữ cảnh sử dụng:** Cung cấp cấu trúc dự án và sơ đồ phân tầng trách nhiệm các thư mục.

---

## 1. Cây thư mục cấp cao (High-Level Directory Tree)

Cây thư mục đại diện (độ sâu tối đa 3 cấp), đã loại trừ các thư mục rác, build artifacts, lock và cache (`node_modules`, `.git`, `venv`, `__pycache__`, `dist`, logs/locks):

```text
.
├── .github/
│   └── workflows/
│       └── notify.yml            # CI/CD & Scheduled Cron Jobs (GitHub Actions)
├── api/                          # Serverless Gateway & HTTP Endpoints (Vercel Functions)
│   ├── add_deadline.py           # Webhook nhận deadline từ hệ thống bên thứ 3 (X-API-Key)
│   ├── index.py                  # API Gateway tổng hợp: REST API Dashboard + Discord Router
│   └── interactions.py           # Discord Interaction Webhook endpoint (Slash Commands)
├── data/                         # Local Seed Data, Sample Datasets & Cache
│   ├── calendar.ics              # File mẫu iCalendar từ Moodle
│   ├── notion_template.csv       # File mẫu cấu trúc dữ liệu Notion Todo List
│   └── state.json                # Trạng thái cache cục bộ (legacy fallback)
├── docs/                         # Tài liệu đặc tả kỹ thuật, roadmap & hướng dẫn tích hợp
│   └── context-pack/             # Bộ tài liệu kiến trúc chuẩn hóa cho Prompt / AI
├── frontend/                     # Single Page Application Dashboard (React + Vite + TypeScript)
│   ├── src/
│   │   ├── api/                  # Tầng giao tiếp mạng Frontend (Fetch client wrappers)
│   │   ├── components/           # Reusable UI Components (Button, Modal, Toast, Badge, Layout)
│   │   ├── features/             # Feature views (Dashboard metrics, Deadlines, Courses, Settings)
│   │   ├── types/                # TypeScript Interfaces & Data contracts
│   │   ├── utils/                # Helper utilities (Date parser, Timezone converters)
│   │   ├── App.tsx               # Root App Component & Tab routing
│   │   └── main.tsx              # React DOM entrypoint
│   ├── index.html                # HTML entrypoint
│   ├── package.json              # Khai báo dependencies Frontend
│   └── vite.config.ts            # Cấu hình bundler Vite
├── migrations/                   # Database DDL & Schema Versioning (PostgreSQL)
│   ├── 001_create_database.sql   # Khởi tạo bảng courses, deadlines, announcements, modules,...
│   ├── 002_add_display_name.sql  # Bổ sung display_name cho courses
│   ├── 004_add_discord_category.sql # Bổ sung phân nhóm kênh theo học kỳ (Category ID)
│   └── 005_add_manual_deadline_support.sql # Bổ sung nguồn gốc (source, added_by) cho deadline
├── scripts/                      # Công cụ CLI bảo trì, DevOps & Quản trị hệ thống
│   ├── check_url.py              # Kiểm tra tính khả dụng của endpoint
│   ├── clean_bot_messages.py     # Dọn dẹp tin nhắn cũ của bot trên Discord
│   ├── discord_auto_channel.py   # Script quét và tạo channel tự động
│   ├── dump_moodle_data.py       # Xuất dữ liệu Moodle phục vụ debug
│   ├── notion_helper.py          # Script tiện ích kiểm tra & thiết lập bảng Notion
│   ├── register_commands.py      # Đăng ký Slash Commands với Discord REST API
│   ├── rename_all_channels.py    # Đồng bộ tên chuẩn hóa các kênh Discord
│   ├── run_server.py             # HTTP Server dev cục bộ cho API testing
│   └── set_category.py           # Gán học kỳ / Category thủ công cho môn học
├── src/                          # Backend Core Services & Infrastructure Adapters (Python)
│   ├── announcement_tracker.py   # Service giám sát tài liệu và diễn đàn Moodle
│   ├── app.py                    # Master Orchestrator (Pipeline xử lý cron, notify, nhắc hạn)
│   ├── config.py                 # Load biến môi trường & validate cấu hình
│   ├── database.py               # Quản lý kết nối PostgreSQL (Context Manager)
│   ├── db_queries.py             # Data Access Object (DAO) tập trung toàn bộ SQL Queries
│   ├── discord_api.py            # Client tương tác Discord REST API v10 (Rate-limit retry)
│   ├── event_tracker.py          # Listener theo dõi reaction Discord để tick hoàn thành
│   ├── external_api.py           # Logic xử lý API bên thứ 3 & HMAC auth
│   ├── google_calendar_sync.py   # Adapter đồng bộ Google Calendar API v3 (Service Account)
│   ├── interactions.py           # Xử lý Slash Commands & Xác thực chữ ký Ed25519
│   ├── moodle_api.py             # Client kết nối Moodle Web Services API
│   ├── moodle_parser.py          # Parser ICS, chuẩn hóa slug, trích xuất học kỳ
│   ├── notion_sync.py            # Adapter đồng bộ Notion Database API (Dynamic schema)
│   └── utils.py                  # Utilities chuẩn hóa thời gian và timezone UTC+7
├── tests/                        # Kiểm thử tự động (Unit & Integration tests)
├── main.py                       # CLI Execution Entrypoint cho GitHub Actions cron runner
├── pyproject.toml                # Cấu hình Python metadata & Vercel deployment
├── requirements.txt              # Khai báo dependencies Backend
└── vercel.json                   # Cấu hình build & routing serverless trên Vercel
```

---

## 2. Phân tầng kiến trúc (Architectural Layers Breakdown)

Hệ thống được thiết kế theo mô hình lai (Hybrid Architecture) kết hợp **Layered Architecture** và **Ports & Adapters (Hexagonal)**:

| Tầng kiến trúc | Thư mục / File đại diện | Chức năng & Trách nhiệm chính |
| :--- | :--- | :--- |
| **1. Ingestion / Gateway Layer** | `api/index.py`<br/>`api/interactions.py`<br/>`api/add_deadline.py`<br/>`main.py` | Tiếp nhận tín hiệu từ các nguồn bên ngoài: HTTP request từ Vercel Serverless, Webhook từ Discord, Webhook từ Zapier/Google Form, và CLI invocation từ GitHub Actions runner. |
| **2. Presentation / UI Layer** | `frontend/src/` | Giao diện Web Dashboard React SPA dành cho người dùng cuối: hiển thị tiến độ hoàn thành, thống kê tỷ lệ, lọc danh sách deadline theo môn/trạng thái và form tạo deadline thủ công. |
| **3. Application / Orchestration Layer** | `src/app.py`<br/>`src/event_tracker.py` | Tầng điều phối trung tâm: quản lý vòng đời deadline (mới -> nhắc 3 ngày -> nhắc 1 ngày -> hoàn thành), điều phối các tiến trình kiểm tra định kỳ, đối soát reaction để hoàn thành nhiệm vụ. |
| **4. Domain & Business Services Layer** | `src/announcement_tracker.py`<br/>`src/moodle_parser.py`<br/>`src/interactions.py`<br/>`src/external_api.py` | Chứa các quy tắc nghiệp vụ đặc thù: bóc tách dữ liệu ICS, quy tắc đặt tên kênh Discord (`nmttnt-csc10014`), bóc tách học kỳ từ category, kiểm tra thay đổi tài liệu môn học (`course_modules`). |
| **5. Infrastructure & Adapters Layer** | `src/discord_api.py`<br/>`src/moodle_api.py`<br/>`src/notion_sync.py`<br/>`src/google_calendar_sync.py` | Đóng gói toàn bộ việc tương tác với các hệ sinh thái bên ngoài (Discord REST API v10, Moodle REST API, Notion API v1, Google Calendar API v3). Bảo vệ luồng chính khỏi lỗi ngoại vi. |
| **6. Persistence / Data Access Layer (DAO)** | `src/database.py`<br/>`src/db_queries.py`<br/>`migrations/` | Quản lý kết nối PostgreSQL (Supabase), đóng gói toàn bộ các truy vấn SQL thuần thông qua các hàm có kiểu rõ ràng, không phụ thuộc ORM cồng kềnh. |
| **7. Cross-cutting / Config & Helpers** | `src/config.py`<br/>`src/utils.py` | Kiểm tra biến môi trường, thiết lập logging chuẩn, chuyển đổi múi giờ đồng nhất `Asia/Ho_Chi_Minh` (UTC+7). |
| **8. Operations & Maintenance** | `scripts/`<br/>`.github/workflows/` | Tự động hóa CI/CD, đăng ký Slash Commands, rename hàng loạt kênh, cấu hình phân nhóm học kỳ. |

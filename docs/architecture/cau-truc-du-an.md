# 🧭 TỔNG QUAN CẤU TRÚC DỰ ÁN — NOTIFICATION BOT (COURSE FIT HCMUS)

> **Cập nhật 2026-10-16:** đường dẫn và cây thư mục trong tài liệu này đã được cập nhật theo cấu trúc sau đợt tái cấu trúc (`course_bot/`, `frontend/src/{app,features,shared}`). Xem `docs/architecture/refactoring-blueprint.md`.

> **Dành cho:** Nguyên  
> **Cập nhật gần nhất:** Tháng 10/2026  
> **Kiến trúc:** 100% Serverless (GitHub Actions + Vercel + Supabase + Discord REST API v10)

---

## 📌 1. CÂY THƯ MỤC TỔNG THỂ

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

## 🧩 2. CHI TIẾT TỪNG TẦNG CHỨC NĂNG (ARCHITECTURE LAYERS)

### 🚀 Tầng 1: Thu thập Dữ liệu (Ingestion Layer)
* **Moodle REST API (`course_bot/services/deadline_crawler.py` & `course_bot/integrations/moodle/webservice.py`):**
  * Dùng `MOODLE_TOKEN` quét trực tiếp:
    1. `mod_assign_get_assignments`: Bắt trọn vẹn deadline bài tập (`duedate`, `cutoffdate`).
    2. `mod_quiz_get_quizzes_by_courses`: Bắt deadline đóng bài trắc nghiệm (`timeclose`).
    3. `core_calendar_get_action_events_by_timesort`: Bắt các sự kiện cần nộp bài khác.
    4. `mod_assign_get_submission_status`: **Tự động tick hoàn thành (Auto-complete)** khi phát hiện sinh viên đã nộp bài.
* **Moodle iCalendar (`course_bot/integrations/moodle/ics_feed.py`):**
  * Tải và parse file `.ics` từ `MOODLE_CALENDAR_URL` để lấy các sự kiện lịch tổng quát.
* **Discord Slash Command (`course_bot/web/routes/discord_interactions.py` + `api/interactions.py`):**
  * Lệnh `/add_deadline`: Cho phép Nguyên hoặc bạn bè nhập deadline trực tiếp trên Discord.
* **Web Dashboard (`frontend/` + `api/index.py`):**
  * Thêm deadline qua giao diện Web trực quan.
* **External Webhook (`course_bot/web/routes/external.py` + `api/add_deadline.py`):**
  * Đón nhận deadline gửi từ Google Forms hoặc Zapier.

---

### 🧠 Tầng 2: Điều phối & Nghiệp vụ (Orchestration & Business Logic)
* **`course_bot/jobs/`:**
  * Điều phối chạy tuần tự:
    1. Kiểm tra reaction `✅` từ người dùng (`check_completions`).
    2. Chạy Moodle API Crawler để lấy deadline bài tập/quiz mới nhất.
    3. Duyệt danh sách deadline (gộp cả Moodle và nhập tay):
       * Chưa báo $\rightarrow$ Gửi thông báo **MỚI**, tạo Scheduled Event Discord, đồng bộ sang Notion và Google Calendar.
       * Còn $\le 3$ ngày $\rightarrow$ Gửi thông báo **NHẮC NHỞ (3 NGÀY)**.
       * Còn $\le 24$ giờ $\rightarrow$ Gửi thông báo **KHẨN CẤP (24 GIỜ)**.
    4. Kiểm tra tài liệu, bài giảng và bài đăng diễn đàn mới (`check_moodle_updates`).

---

### 🗄️ Tầng 3: Lưu trữ Dữ liệu (Persistence Layer - Supabase PostgreSQL)
* **`course_bot/db/connection.py` & `course_bot/db/repositories/`:**
  * Quản lý kết nối an toàn với context manager `get_db()`.
  * Các bảng chính trong database:
    * `courses`: Lưu mã môn (CSC10014), tên tiếng Việt, channel ID Discord, category ID học kỳ.
    * `deadlines`: Lưu bài tập, hạn chót, trạng thái đã báo (new/3d/1d), trạng thái xong (`completed`), nguồn (`moodle` / `moodle_api` / `manual` / `external`).
    * `course_modules`: Lưu tài liệu, slide, folder đã quét để chống báo trùng.
    * `forum_discussions`: Lưu các bài đăng trên diễn đàn khoa.
    * `notifications`: Lịch sử các thông báo đã gửi.

---

### 🌐 Tầng 4: Đồng bộ & Thông báo Ngoại vi (Notification & Sync Layer)
* **Discord (`course_bot/integrations/discord/rest.py`):**
  * Tự tạo channel theo môn học chuẩn hóa: `#nmttnt-csc10014`.
  * Gom channel vào đúng Category học kỳ (vd: `KÌ 2`, `KÌ 3`).
  * Tạo Scheduled Events trên Discord để xem trên lịch server.
* **Google Calendar (`course_bot/integrations/google_calendar/client.py`):**
  * Tạo sự kiện có chuông báo điện thoại trước 24h, 3h, 30p.
  * Tự đổi màu xanh lá và thêm tiền tố `✅ [XONG]` khi hoàn thành.
* **Notion Todo List (`course_bot/integrations/notion/client.py`):**
  * Đẩy deadline vào bảng công việc trên Notion, tự tick checkbox khi làm xong.

---

### 💻 Tầng 5: Giao diện Web Quản trị (Frontend Dashboard)
* Nằm trong thư mục `frontend/`, chạy bằng Vite + React + Tailwind CSS.
* **Chức năng:**
  * Xem danh sách bài tập theo dạng List hoặc dạng bảng kéo thả **Kanban**.
  * Xem tiến độ hoàn thành (Progress Bar), bài gấp trong 24h, bài trễ hạn.
  * Thêm deadline thủ công nhanh chóng có gợi ý tên môn học.
  * Đánh dấu hoàn thành một chạm.

---

## 🛠️ 3. CÁC LỆNH CHẠY QUAN TRỌNG CHO NGUYÊN (CHEAT SHEET)

Nguyên có thể mở terminal tại thư mục dự án và chạy các lệnh sau:

| Lệnh | Ý nghĩa chức năng |
| :--- | :--- |
| `python main.py` | Chạy toàn bộ chu trình: kiểm tra hoàn thành, quét deadline Moodle, gửi thông báo Discord, sync Notion/GCal. |
| `python main.py --crawl-deadlines` | **[Mới]** Chỉ chạy riêng bộ quét Moodle REST API (kiểm tra bài tập, quiz, nộp bài). |
| `python main.py --summary` | Gửi báo cáo tóm tắt các deadline sắp tới vào kênh chat. |
| `python main.py --progress` | Gửi bảng đo tiến độ hoàn thành deadline hằng ngày. |
| `python main.py --announcements` | Chỉ kiểm tra tài liệu mới và bài đăng diễn đàn trên Moodle. |
| `python main.py --sync-channels` | Quét Moodle và tự động tạo/chuẩn hoá toàn bộ kênh môn học trên Discord. |
| `python main.py --sync-notion` | Đồng bộ toàn bộ danh sách deadline sang Notion Todo List. |
| `python main.py --sync-gcal` | Đồng bộ toàn bộ deadline sang Google Calendar. |
| `python main.py --dedup --dry-run` | Quét kiểm tra xem trên Discord có tin nhắn thông báo nào bị trùng lặp không. |
| `python -m scripts.ops.register_commands` | Đăng ký Slash Command (`/add_deadline`) lên server Discord. |

---

## 🔒 4. DANH SÁCH BIẾN MÔI TRƯỜNG CẦN THIẾT (.env)

Khi cấu hình trên máy tính cá nhân hoặc GitHub Secrets, Nguyên cần lưu ý các biến sau:

```ini
# Bắt buộc cho Bot hoạt động
DISCORD_BOT_TOKEN=MTA...               # Token của bot tạo từ Discord Developer Portal
DISCORD_SERVER_ID=123456789...          # ID server Discord của Nguyên
MOODLE_CALENDAR_URL=https://...         # Link xuất lịch .ics từ Moodle
DATABASE_URL=postgresql://postgres:...  # Link kết nối CSDL Supabase PostgreSQL

# Khuyên dùng để mở khóa toàn bộ tính năng cao cấp
MOODLE_TOKEN=abc123xyz...              # Token Web Service Moodle (để cào Quiz, Assignment, Slide)
DISCORD_PUBLIC_KEY=...                  # Public Key Discord (để nhận lệnh /add_deadline trên Vercel)
EXTERNAL_API_KEY=...                    # Key bảo mật nếu dùng Google Form / Zapier

# Tùy chọn (nếu muốn đồng bộ ra ứng dụng khác)
NOTION_API_TOKEN=secret_...             # Token tích hợp của Notion
NOTION_DATABASE_ID=...                  # ID database todo list trên Notion
GOOGLE_CALENDAR_ID=...@group.calendar.google.com # ID của Google Calendar
GOOGLE_SERVICE_ACCOUNT_JSON={...}       # Toàn bộ nội dung file JSON Service Account Google
```

---

## 🗺️ 5. BẢNG VAI TRÒ CÁC MODULE CỐT LÕI

| Module / Thư mục | Trách nhiệm chính |
| :--- | :--- |
| [`course_bot/jobs/`](../../course_bot/jobs/) | Điều phối chu trình quét deadline, chuỗi nhắc 3 ngày / 1 ngày, gửi summary & progress report. |
| [`course_bot/services/deadline_crawler.py`](../../course_bot/services/deadline_crawler.py) | Cào trực tiếp bài tập (`mod_assign`) và quiz (`mod_quiz`) từ Moodle API; tự động đánh dấu hoàn thành khi sinh viên nộp bài. |
| [`course_bot/services/announcement_tracker.py`](../../course_bot/services/announcement_tracker.py) | Theo dõi tài liệu upload mới (slide, PDF) và bài viết diễn đàn. |
| [`course_bot/integrations/discord/rest.py`](../../course_bot/integrations/discord/rest.py) | Tạo kênh, phân loại category theo học kỳ, gửi tin nhắn, tạo Scheduled Event. |
| [`api/index.py`](../../api/index.py) | REST API phục vụ Web Dashboard hoạt động trên Vercel. |
| [`frontend/`](../../frontend/) | Giao diện Web SPA quản trị bài tập (hỗ trợ kéo thả Kanban, lọc môn học). |

---

> 💡 **Ghi chú dành riêng cho Nguyên:**  
> Hệ thống hiện tại hoàn toàn tự động 24/7 nhờ **GitHub Actions** (chạy ngầm mỗi 30 phút) và **Vercel** (tiếp nhận lệnh Discord tức thì). Bạn không cần phải mở máy tính hay cắm sạc laptop để bot chạy!

# 🧭 TỔNG QUAN CẤU TRÚC DỰ ÁN — NOTIFICATION BOT (COURSE FIT HCMUS)
> **Dành cho:** Nguyên  
> **Cập nhật gần nhất:** Tháng 10/2026  
> **Kiến trúc:** 100% Serverless (GitHub Actions + Vercel + Supabase + Discord REST API v10)

---

## 📌 1. CÂY THƯ MỤC TỔNG THỂ

```text
Notification Project/
├── .github/                      # CI/CD & Lịch chạy ngầm tự động (GitHub Actions)
│   └── workflows/
│       ├── notify.yml            # [CHỦ CHỐT] Chạy mỗi 30p: quét deadline, thông báo, sync channels, gcal, notion
│       └── daily_summary.yml     # Chạy 7:00 sáng hàng ngày: gửi báo cáo tổng kết tiến độ và deadline hôm nay
│
├── api/                          # Backend API Serverless (Deploy trên Vercel)
│   ├── index.py                  # REST API Gateway phục vụ Web Dashboard (/api/stats, /api/deadlines, /api/courses)
│   ├── interactions.py           # Webhook đón Slash Command từ Discord (/add_deadline, /deadline)
│   └── add_deadline.py           # Webhook nhận deadline từ bên thứ ba (Google Forms, Zapier)
│
├── src/                          # TOÀN BỘ MÃ NGUỒN CỐT LÕI (PYTHON CORE)
│   ├── app.py                    # [BỘ NÃO] Master Orchestrator: điều phối toàn bộ chu trình thông báo và sync
│   ├── moodle_deadline_crawler.py# [MỚI] Quét trực tiếp Moodle REST API (Assignments, Quizzes, Auto-complete nộp bài)
│   ├── moodle_api.py             # Client gọi Moodle Web Services API (có User-Agent bypass WAF trường)
│   ├── moodle_parser.py          # Bóc tách iCalendar (.ics), tính học kỳ, slugify tên kênh Discord
│   ├── announcement_tracker.py   # Theo dõi bài giảng, slide, PDF, quiz mới và thảo luận diễn đàn (Forum)
│   ├── discord_api.py            # Client Discord REST API v10 (gửi tin, tạo kênh, tạo Event, chống rate-limit)
│   ├── interactions.py           # Bộ xử lý nghiệp vụ Slash Command (xác thực Ed25519 với PyNaCl)
│   ├── external_api.py           # Bộ xử lý nghiệp vụ nhận deadline từ Google Forms / Zapier (HMAC SHA256)
│   ├── event_tracker.py          # Lắng nghe reaction ✅ trên Discord để tự động đổi trạng thái hoàn thành
│   ├── google_calendar_sync.py   # Đồng bộ 2 chiều lên Google Calendar qua Service Account
│   ├── notion_sync.py            # Đồng bộ 2 chiều lên Notion Database Todo List
│   ├── database.py               # Quản lý kết nối PostgreSQL (Supabase) qua context manager
│   ├── db_queries.py             # Tầng DAO (chứa tất cả các câu truy vấn SQL chuẩn)
│   ├── config.py                 # Đọc và kiểm tra biến môi trường .env, múi giờ Việt Nam (UTC+7)
│   └── utils.py                  # Tiện ích chuẩn hoá múi giờ, phân tích ngày giờ linh hoạt
│
├── frontend/                     # WEB DASHBOARD (REACT + VITE + TAILWIND)
│   ├── src/
│   │   ├── api/client.ts         # HTTP Client gọi API Vercel an toàn
│   │   ├── types/index.ts        # Định nghĩa kiểu dữ liệu TypeScript
│   │   ├── utils/dateUtils.ts    # Tiện ích đếm ngược (countdown), format ngày tiếng Việt
│   │   ├── components/
│   │   │   ├── layout/           # Header.tsx, Sidebar.tsx
│   │   │   └── ui/               # Button, Modal, Checkbox, ProgressBar, Toast, Badge...
│   │   ├── features/
│   │   │   ├── dashboard/        # HeroProgressBanner, MetricCards
│   │   │   ├── deadlines/        # ListView, KanbanView, AddDeadlineModal, Toolbar, ItemCard
│   │   │   ├── courses/          # CoursesView (quản lý môn học)
│   │   │   ├── announcements/    # AnnouncementsView (thông báo tài liệu/diễn đàn)
│   │   │   └── settings/         # SettingsView (hướng dẫn cấu hình)
│   │   ├── App.tsx               # Component chính điều phối view và state toàn cục
│   │   └── main.tsx              # Entrypoint khởi tạo React DOM
│   ├── package.json              # Danh sách thư viện frontend
│   ├── vite.config.ts            # Cấu hình Vite build
│   └── tailwind.config.js        # Cấu hình giao diện Tailwind
│
├── migrations/                   # LỊCH SỬ NÂNG CẤP DATABASE (SUPABASE POSTGRESQL)
│   ├── 001_create_database.sql   # Tạo các bảng cơ sở: courses, deadlines, modules, forums, notifications
│   ├── 002_add_display_name.sql  # Thêm cột tên môn tiếng Việt (display_name)
│   ├── 004_add_discord_category.sql # Thêm quản lý Category theo từng học kỳ
│   ├── 005_add_manual_deadline_support.sql # Hỗ trợ deadline thủ công (source, added_by)
│   └── NOTES.md                  # Hướng dẫn chạy migration bằng Supabase SQL Editor
│
├── scripts/                      # TIỆN ÍCH DÀNH CHO BẢO TRÌ & DEV
│   ├── register_commands.py      # Đăng ký Slash Command lên Discord Developer Portal
│   ├── rename_all_channels.py    # Đổi tên hàng loạt kênh Discord theo chuẩn mới (vd: nmttnt-csc10014)
│   ├── discord_auto_channel.py   # Tạo tự động toàn bộ kênh Discord từ danh sách môn Moodle
│   ├── clean_bot_messages.py     # Quét và dọn dẹp các tin nhắn rác hoặc trùng lặp của Bot
│   ├── set_category.py           # Gán Category Discord cho môn học thủ công
│   ├── notion_helper.py          # Hỗ trợ tự động tạo Database trên Notion theo schema chuẩn
│   ├── dump_moodle_data.py       # Tải và dump mẫu JSON từ Moodle API để kiểm tra cấu trúc
│   ├── check_url.py              # Kiểm tra nhanh URL Calendar ICS hoặc Moodle API
│   ├── setup_termux.sh           # [MỚI] Tự động cài đặt & tạo 10 Widget máy trạm trên Termux (Android)
│   └── run_server.py             # Chạy local server giả lập Vercel để test API
│
├── tests/                        # BỘ TEST TỰ ĐỘNG (UNIT & INTEGRATION TESTS)
│   ├── test_bot.py               # Test luồng xử lý chính của Bot
│   ├── test_moodle.py            # Test parser Moodle ICS & API
│   ├── test_google_calendar_sync.py # Test đồng bộ Google Calendar
│   ├── test_deduplication.py     # Test cơ chế chống spam tin nhắn Discord
│   ├── test_semester_calculation.py # Test thuật toán tính học kỳ và năm học
│   └── ...                       # Các test case đặc thù khác
│
├── docs/                         # TÀI LIỆU DỰ ÁN CHI TIẾT
│   ├── context-pack/             # 6 tài liệu kiến trúc toàn diện (Data flow, Tech stack, Hotspots...)
│   ├── google-calendar-integration.md # Hướng dẫn cài đặt Google Calendar Service Account
│   ├── notion-todo-list-integration.md# Hướng dẫn kết nối Notion Database
│   ├── kiem-tra-moodle-api.md    # Hướng dẫn lấy và kiểm tra Token Moodle qua trình duyệt
│   └── ...                       # Các tài liệu thiết kế Figma, lộ trình tính năng
│
├── main.py                       # [RUNNER CHÍNH] File chạy dòng lệnh CLI của Bot
├── requirements.txt              # Các thư viện Python cần cài (requests, psycopg2, pynacl...)
├── vercel.json                   # Cấu hình routing deploy Vercel Serverless
├── README.md                     # Hướng dẫn cài đặt và sử dụng tổng quát
├── ROADMAP.md                    # Lộ trình phát triển tính năng
├── KE_HOACH_MAY_TRAM_NGUYEN.md   # Hướng dẫn thiết lập máy trạm cá nhân của Nguyên
└── TERMUX_WORKSTATION.md         # Hướng dẫn vận hành hệ thống trên Termux (Android)
```

---

## 🧩 2. CHI TIẾT TỪNG TẦNG CHỨC NĂNG (ARCHITECTURE LAYERS)

### 🚀 Tầng 1: Thu thập Dữ liệu (Ingestion Layer)
* **Moodle REST API (`src/moodle_deadline_crawler.py` & `src/moodle_api.py`):**
  * Dùng `MOODLE_TOKEN` quét trực tiếp:
    1. `mod_assign_get_assignments`: Bắt trọn vẹn deadline bài tập (`duedate`, `cutoffdate`).
    2. `mod_quiz_get_quizzes_by_courses`: Bắt deadline đóng bài trắc nghiệm (`timeclose`).
    3. `core_calendar_get_action_events_by_timesort`: Bắt các sự kiện cần nộp bài khác.
    4. `mod_assign_get_submission_status`: **Tự động tick hoàn thành (Auto-complete)** khi phát hiện sinh viên đã nộp bài.
* **Moodle iCalendar (`src/moodle_parser.py`):**
  * Tải và parse file `.ics` từ `MOODLE_CALENDAR_URL` để lấy các sự kiện lịch tổng quát.
* **Discord Slash Command (`src/interactions.py` + `api/interactions.py`):**
  * Lệnh `/add_deadline`: Cho phép Nguyên hoặc bạn bè nhập deadline trực tiếp trên Discord.
* **Web Dashboard (`frontend/` + `api/index.py`):**
  * Thêm deadline qua giao diện Web trực quan.
* **External Webhook (`src/external_api.py` + `api/add_deadline.py`):**
  * Đón nhận deadline gửi từ Google Forms hoặc Zapier.

---

### 🧠 Tầng 2: Điều phối & Nghiệp vụ (Orchestration & Business Logic)
* **`src/app.py`:**
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
* **`src/database.py` & `src/db_queries.py`:**
  * Quản lý kết nối an toàn với context manager `get_db()`.
  * Các bảng chính trong database:
    * `courses`: Lưu mã môn (CSC10014), tên tiếng Việt, channel ID Discord, category ID học kỳ.
    * `deadlines`: Lưu bài tập, hạn chót, trạng thái đã báo (new/3d/1d), trạng thái xong (`completed`), nguồn (`moodle` / `moodle_api` / `manual` / `external`).
    * `course_modules`: Lưu tài liệu, slide, folder đã quét để chống báo trùng.
    * `forum_discussions`: Lưu các bài đăng trên diễn đàn khoa.
    * `notifications`: Lịch sử các thông báo đã gửi.

---

### 🌐 Tầng 4: Đồng bộ & Thông báo Ngoại vi (Notification & Sync Layer)
* **Discord (`src/discord_api.py`):**
  * Tự tạo channel theo môn học chuẩn hóa: `#nmttnt-csc10014`.
  * Gom channel vào đúng Category học kỳ (vd: `KÌ 2`, `KÌ 3`).
  * Tạo Scheduled Events trên Discord để xem trên lịch server.
* **Google Calendar (`src/google_calendar_sync.py`):**
  * Tạo sự kiện có chuông báo điện thoại trước 24h, 3h, 30p.
  * Tự đổi màu xanh lá và thêm tiền tố `✅ [XONG]` khi hoàn thành.
* **Notion Todo List (`src/notion_sync.py`):**
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
| `python scripts/ops/register_commands.py` | Đăng ký Slash Command (`/add_deadline`) lên server Discord. |

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

> 💡 **Ghi chú dành riêng cho Nguyên:**  
> Hệ thống hiện tại hoàn toàn tự động 24/7 nhờ **GitHub Actions** (chạy ngầm mỗi 30 phút) và **Vercel** (tiếp nhận lệnh Discord tức thì). Bạn không cần phải mở máy tính hay cắm sạc laptop để bot chạy!

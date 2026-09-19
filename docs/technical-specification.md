# TÀI LIỆU KỸ THUẬT HỆ THỐNG (SYSTEM TECHNICAL SPECIFICATION)
## DỰ ÁN: COURSE FIT HCMUS - DEADLINE & ACADEMIC ACTIVITY HUB

---

### THÔNG TIN DỰ ÁN ĐẦU VÀO (PROJECT CONTEXT)
- **Tên dự án:** Course FIT HCMUS - Deadline & Academic Activity Hub (Discord Bot & Web Dashboard)
- **Mục tiêu cốt lõi:** Tự động hóa 100% việc theo dõi, đồng bộ và phân phối bài tập/deadline, tài liệu và thông báo từ hệ thống Moodle (courses.fit.hcmus.edu.vn) sang Discord Server, Google Calendar, Notion và một Web Dashboard tập trung; giải quyết triệt để vấn đề quên deadline, thất lạc thông báo bài giảng và thiếu công cụ quản lý tiến độ học tập nhóm/cá nhân.
- **Đối tượng sử dụng:** 
  1. Sinh viên Khoa CNTT - ĐH Khoa học Tự nhiên ĐHQG-HCM (Người dùng cuối theo dõi lịch học).
  2. Trưởng nhóm / Thành viên nhóm đồ án (Cần thêm deadline nội bộ, phân chia công việc).
  3. Quản trị viên hệ thống (Admin/Chủ dự án quản trị bot, cấu hình channel và danh mục môn học).
- **Định hướng Tech Stack:**
  - **Frontend:** React 18 / Vite + Tailwind CSS + Lucide Icons (Single Page Application, Dark/Light mode, Responsive).
  - **Backend:** Python 3.12 Serverless (Vercel Serverless Functions) cho REST/Interactions API + GitHub Actions (Cron Runner định kỳ mỗi 30 phút).
  - **Database:** PostgreSQL (Supabase Cloud) + Connection Pooler (`psycopg2-binary`).
  - **Cloud/Hosting/Integrations:** Vercel (Web & API Gateway), GitHub Actions (Cron scheduler), Discord REST API (Bot interactions, Channels, Scheduled Events, Auto-threads), Google Calendar API (Service Account), Notion API (Databases & Pages).
- **Các tính năng trọng tâm (MVP):**
  1. Crawl tự động file iCalendar (.ics) và Moodle REST API để phát hiện deadline, tài liệu học tập, bài đăng diễn đàn mới.
  2. Bot Discord thông minh: Tự động phân loại môn học vào đúng Category học kỳ, tạo kênh chuẩn format (`#nmttnt-csc10014`), tạo Scheduled Event, tự tạo Thread thảo luận bài tập, gửi nhắc nhở đa tầng (NEW, 3 ngày, 24 giờ, báo cáo tổng hợp 7h sáng).
  3. Web Frontend Dashboard: Hiển thị tiến độ hoàn thành, đếm ngược thời gian, bộ lọc môn học/trạng thái và đánh dấu hoàn thành bài tập trực tiếp.
  4. Quản lý Deadline nội bộ (Manual Deadlines) 2 chiều qua Discord Slash Command (`/add_deadline`), Web Form và External API Webhook.
  5. Đồng bộ trạng thái hoàn thành (Reactions ✅ trên Discord hoặc thao tác trên Web -> cập nhật Supabase, đổi màu xanh trên Google Calendar, đánh dấu checkbox trên Notion).

---

## PHẦN 1: TÀI LIỆU YÊU CẦU SẢN PHẨM (PRD)

### 1. Tóm tắt mục tiêu & Tiêu chí đo lường hoàn thành (Definition of Done - DoD)
- **Mục tiêu sản phẩm:** 
  - Giảm thiểu 100% trường hợp bỏ lỡ hạn nộp bài do quên hoặc giảng viên đổi lịch đột xuất.
  - Tối ưu thời gian tra cứu: từ trung bình 5 phút đăng nhập Moodle xuống còn 0 giây (thông báo chủ động qua Discord/điện thoại) hoặc 3 giây trên Web Dashboard.
  - Hỗ trợ học tập cộng tác: cung cấp không gian thảo luận chuyên biệt theo từng bài tập (Discord Auto-thread).
- **Definition of Done (DoD) cho toàn bộ hệ thống:**
  - [x] **Functionality:** Toàn bộ tính năng trong MVP Scope hoạt động ổn định, không có lỗi Unhandled Exception.
  - [x] **Performance:** 
    - Discord Interaction endpoint (`POST /api/interactions`) phản hồi ACK (`type: 1` hoặc `type: 4`) trong vòng `< 2.5 giây` (dưới ngưỡng 3s timeout của Discord).
    - Web REST API endpoint phản hồi dữ liệu trong vòng `< 800ms` với mạng tiêu chuẩn.
    - Thời gian chạy pipeline crawl cron trên GitHub Actions hoàn thành trong `< 60 giây`.
  - [x] **Data Integrity:** Không bao giờ gửi thông báo trùng lặp (Idempotent 100%) nhờ cơ chế so khớp `lms_deadlines_id`, `lms_module_id` và `lms_discussion_id` trong Supabase.
  - [x] **Reliability:** Lỗi phát sinh từ Moodle downtime hoặc Discord API rate limit được ghi nhận chi tiết vào bảng `error_logs` mà không làm crash tiến trình chính.
  - [x] **Security:** Không để lộ token trong mã nguồn (100% đọc từ biến môi trường); chữ ký Ed25519 từ Discord được xác thực chặt chẽ; API thêm deadline bên ngoài yêu cầu `X-API-Key`.

---

### 2. Phân rã tính năng (Feature Decomposition)

#### 2.1. MVP Scope (Bắt buộc có)
1. **Core Ingestion & Storage:**
   - Parser phân tích dữ liệu lịch Moodle (.ics) và Moodle Core Web Service JSON.
   - Database schema trên Supabase lưu trữ Courses, Deadlines, Announcements, Course Modules, Forum Discussions, Notifications, Error Logs.
2. **Discord Automated Workflow:**
   - Phân tích mã môn và tự động tạo Discord Text Channel trong đúng Category học kỳ.
   - Gửi tin nhắn Embed thông báo deadline mới kèm nút link Moodle.
   - Tự động tạo Discord Scheduled Event cho từng deadline.
   - Tự động tạo Thread thảo luận (`💬 Thảo luận: [Tên Bài Tập]`) bên dưới tin báo deadline mới.
   - Nhắc nhở thông minh: Khẩn cấp (< 24 giờ) kèm ping vai trò/mọi người, Nhắc nhở (Còn 3 ngày), Báo cáo tiến độ hằng ngày lúc 07:00 sáng.
   - Reaction tracking: Lắng nghe reaction `✅` trên tin nhắn Discord để cập nhật `completed = true`.
3. **Web Frontend Dashboard:**
   - Giao diện trực quan thống kê tổng số deadline, số bài cần nộp gấp, tỷ lệ hoàn thành (%).
   - Danh sách deadline kèm countdown timer, filter theo môn học, tìm kiếm, checkbox đánh dấu hoàn thành tức thì.
   - Form Thêm Deadline nội bộ (chọn môn học, tên bài tập, hạn chót có nút chọn nhanh 23:59, người phụ trách).
   - Trang danh sách môn học và bảng tin thông báo/tài liệu Moodle mới nhất.
4. **Manual Deadline Management:**
   - Slash Command `/add_deadline` trên Discord.
   - REST API endpoint `POST /api/add_deadline` với xác thực `X-API-Key`.
   - Form trực tiếp trên Web Dashboard.
5. **Đồng bộ 3 bên (Integrations):**
   - Google Calendar Sync: Tạo event, chuông nhắc điện thoại, tự đổi sang màu xanh lá khi xong.
   - Notion Todo List Sync: Tự tạo card deadline, đánh dấu checkbox hoàn thành.

#### 2.2. Backlog / Phase 2 (Mở rộng)
- **AI Summary (Gemini 2.5 Flash / 1.5 Pro):** Tự động tóm tắt nội dung thông báo dài từ giảng viên thành 2-3 gạch đầu dòng then chốt (TL;DR).
- **Multi-tenant / SaaS Platform:** Cho phép sinh viên khác đăng nhập tài khoản Moodle cá nhân qua OAuth/Token để quản lý lịch học riêng biệt.
- **Discord Role Pinging tự động:** Tự động tạo Role môn học và gán vai trò khi sinh viên tự click nhận role, tránh ping làm phiền người không học môn đó.
- **Push Notification qua Web Push / Telegram:** Bổ sung kênh nhận tin khẩn cấp qua Telegram Bot hoặc trình duyệt web di động.

---

### 3. Danh sách User Stories chi tiết

| ID | User Story | Acceptance Criteria (Điều kiện nghiệm thu) |
|---|---|---|
| **US-01** | Là một **Sinh viên**, tôi muốn **nhận thông báo tức thời trên Discord khi có bài tập mới trên Moodle** để **tôi chủ động sắp xếp thời gian làm bài mà không cần liên tục F5 trang web**. | **1.** Bot phát hiện bài tập mới trong chu kỳ quét 30 phút.<br>**2.** Tin nhắn gửi vào đúng channel môn học (ví dụ `#nmttnt-csc10014`).<br>**3.** Tin nhắn chứa Embed đẹp mắt: Tên bài tập, Hạn chót (giờ VN), Link nộp bài.<br>**4.** Tự động tạo Scheduled Event trên Discord.<br>**5.** Tự động tạo Thread thảo luận dưới tin nhắn. |
| **US-02** | Là một **Trưởng nhóm đồ án**, tôi muốn **thêm các mốc deadline nội bộ (nháp code, nộp báo cáo) qua Web hoặc Discord** để **cả nhóm cùng theo dõi và nhận thông báo chung luồng với Moodle**. | **1.** Nhập form qua Web hoặc gõ lệnh `/add_deadline`.<br>**2.** Hạn chót nếu không nhập giờ sẽ tự động gán mặc định là 23:59.<br>**3.** Deadline được lưu vào DB với `source = 'manual'`.<br>**4.** Lần chạy cron kế tiếp của bot sẽ gửi thông báo, tạo event và nhắc nhở y hệt deadline Moodle. |
| **US-03** | Là một **Thành viên nhóm**, tôi muốn **đánh dấu bài tập đã hoàn thành bằng cách thả cảm xúc `✅` trên Discord hoặc click checkbox trên Web** để **bảng tiến độ ghi nhận tôi đã xong và không tiếp tục nhắc nhở**. | **1.** Thả reaction `✅` vào tin nhắn Discord hoặc bấm checkbox trên Web Dashboard.<br>**2.** Cột `completed` đổi thành `true`, lưu tên người hoàn thành.<br>**3.** Event trên Google Calendar đổi sang màu Xanh lá.<br>**4.** Trang Notion Todo List được tích checkbox hoàn thành.<br>**5.** Báo cáo sáng 7h tăng % tiến độ hoàn thành. |
| **US-04** | Là một **Sinh viên**, tôi muốn **truy cập Web Dashboard để xem danh sách toàn bộ deadline trong tuần/tháng kèm đồng hồ đếm ngược** để **tôi có cái nhìn tổng quan về khối lượng bài vở sắp tới**. | **1.** Web tải dữ liệu trong `< 1 giây`.<br>**2.** Có bộ lọc: Tất cả, Khẩn cấp (< 24h), Đã xong, Quá hạn, và lọc theo Môn học.<br>**3.** Đếm ngược thời gian trực quan ("còn 14 giờ", "còn 2 ngày").<br>**4.** Giao diện mượt mà trên cả máy tính lẫn điện thoại, hỗ trợ Dark Mode. |
| **US-05** | Là một **Sinh viên**, tôi muốn **nhận được báo cáo tổng hợp tiến độ vào 7:00 sáng mỗi ngày trên Discord** để **tôi bắt đầu ngày mới với danh sách việc cần ưu tiên rõ ràng**. | **1.** Đúng 07:00 (giờ GMT+7), bot gửi tin nhắn vào kênh chung.<br>**2.** Hiển thị thanh tiến độ trực quan: `[████████░░] 80% (8/10 bài)`.<br>**3.** Liệt kê danh sách các bài tập còn hạn, phân nhóm rõ: Khẩn cấp (<24h), Sắp tới (1-3 ngày), Còn xa (>3 ngày). |

---

### 4. User Flow

```mermaid
flowchart TD
    Start([Moodle hoặc Người dùng tạo sự kiện]) --> TriggerCheck{Nguồn sự kiện?}
    
    TriggerCheck -->|Giảng viên đăng lên Moodle| MoodleSync[GitHub Actions Cron quét .ics & API]
    TriggerCheck -->|Người dùng tạo thủ công| WebDiscordInput[Nhập Web Form HOẶC gõ /add_deadline]
    
    WebDiscordInput --> InsertManual[Ghi vào Supabase: source='manual', notified_new=false]
    MoodleSync --> DetectNew[Đối chiếu Supabase: Phát hiện deadline/tài liệu mới]
    
    InsertManual --> CronProcess[Cron Job nhặt deadline xử lý trong chu kỳ 30p]
    DetectNew --> CronProcess
    
    CronProcess --> DiscordNotify[1. Bắn tin thông báo Embed vào đúng Channel môn học]
    CronProcess --> DiscordThread[2. Tạo Discord Thread: 💬 Thảo luận]
    CronProcess --> DiscordEvent[3. Tạo Discord Scheduled Event]
    CronProcess --> GCalSync[4. Đồng bộ sự kiện sang Google Calendar]
    CronProcess --> NotionSync[5. Tạo Todo Item trên Notion]
    
    DiscordNotify --> UserInteraction[Sinh viên nhận thông báo & tương tác]
    
    UserInteraction --> CompleteAction{Sinh viên hoàn thành bài?}
    CompleteAction -->|Thả reaction ✅ trên Discord| TrackReaction[Bot quét Discord Reactions]
    CompleteAction -->|Bấm checkbox trên Web Dashboard| WebToggle[Gọi API POST /api/deadlines/toggle]
    
    TrackReaction --> MarkDone[Cập nhật Supabase: completed=true, completed_by=user]
    WebToggle --> MarkDone
    
    MarkDone --> UpdateGCal[Đổi màu Google Calendar sang Xanh Lá]
    MarkDone --> UpdateNotion[Đánh dấu checkbox Notion hoàn thành]
    MarkDone --> UpdateDashboard[Web Dashboard & Báo cáo tiến độ 7h sáng tăng % hoàn thành]
    
    UpdateDashboard --> Finish([Hoàn tất quy trình])
```

---

## PHẦN 2: THIẾT KẾ KIẾN TRÚC HỆ THỐNG (SYSTEM ARCHITECTURE)

### 1. Sơ đồ Kiến trúc Tổng thể (Overall Architecture)

```mermaid
graph TD
    subgraph Clients ["Lớp Khách (Clients)"]
        Browser["🌐 Web Browser (Sinh viên / Admin)"]
        DiscordClient["💬 Discord Client (Mobile / Desktop)"]
        ThirdParty["🔗 External Apps (Zapier, Google Forms, Script)"]
    end

    subgraph CDN_Gateway ["Vercel Cloud Platform (API & Frontend Hosting)"]
        VercelEdge["Vercel Edge Network / Routing"]
        StaticFrontend["Frontend Static Assets (Vite + React SPA)"]
        ServerlessFunc["Serverless Python API (api/index.py)"]
    end

    subgraph Automation_Engine ["Background Automation Engine (GitHub Actions)"]
        CronSchedule["⏰ Scheduled Cron (Mỗi 30 phút & 07:00 AM)"]
        MainRunner["🐍 Python CLI Engine (main.py / src/app.py)"]
    end

    subgraph Data_Tier ["Data Tier (Supabase PostgreSQL Cloud)"]
        Pooler["Supabase Connection Pooler (PgBouncer - Port 5432)"]
        PG_DB[("PostgreSQL Database
        - courses
        - deadlines
        - announcements
        - course_modules
        - forum_discussions
        - notifications
        - error_logs")]
    end

    subgraph External_Services ["Dịch vụ Bên Thứ Ba (External Integrations)"]
        MoodleLMS["🎓 Moodle FIT HCMUS (Calendar .ics & REST API)"]
        DiscordAPI["🎮 Discord REST API (Channels, Events, Messages)"]
        GCalAPI["📅 Google Calendar API (Service Account)"]
        NotionAPI["📝 Notion API (Todo Database)"]
    end

    %% Client Routing
    Browser -->|HTTPS GET /| VercelEdge
    VercelEdge -->|Serve HTML/JS/CSS| StaticFrontend
    Browser -->|AJAX /api/*| VercelEdge
    ThirdParty -->|POST /api/add_deadline kèm X-API-Key| VercelEdge
    DiscordClient -->|Webhook Interactions / Slash Commands| VercelEdge
    VercelEdge -->|Proxy API Request| ServerlessFunc

    %% API to Database
    ServerlessFunc -->|Verify Ed25519 / API Key| ServerlessFunc
    ServerlessFunc -->|Direct SQL Query| Pooler

    %% Cron to External & Database
    CronSchedule -->|Trigger Trigger Workflow| MainRunner
    MainRunner -->|1. Pull Data| MoodleLMS
    MainRunner -->|2. Read/Write State| Pooler
    Pooler --> PG_DB
    MainRunner -->|3. Send Messages, Create Events & Threads| DiscordAPI
    MainRunner -->|4. Sync Events| GCalAPI
    MainRunner -->|5. Sync Tasks| NotionAPI
```

---

### 2. Quyết định Công nghệ (Tech Stack Rationale)

| Tầng (Layer) | Công nghệ lựa chọn | Lý do lựa chọn cốt lõi | Đánh đổi (Trade-offs) & Giải pháp khắc phục |
|---|---|---|---|
| **Frontend** | **React 18 + Vite + Tailwind CSS + Lucide Icons** | Khởi động tức thì (Vite HMR), xây dựng giao diện component hoá sạch sẽ, Tailwind giúp style nhanh chuẩn responsive, Lucide cung cấp icon hiện đại, bundle thành static file cực nhẹ để host free trên Vercel. | SPA cần cấu hình rewrite URL trên Vercel để tránh lỗi 404 khi F5. *Giải pháp:* Đã thêm rule rewrite trong `vercel.json`. |
| **API Gateway / Serverless** | **Python 3.12 (HTTP Serverless Functions trên Vercel)** | Tận dụng 100% logic mã nguồn Python đã viết ở backend (`src/`), không phải duy trì 2 ngôn ngữ khác nhau giữa backend và bot. Chi phí $0/tháng. | Serverless có cold start (khoảng 1-2s). *Giải pháp:* Mã nguồn tối ưu nhẹ, import lazy, không dùng framework cồng kềnh như Django. |
| **Worker / Background Job** | **GitHub Actions (Ubuntu Runner)** | Chạy ngầm định kỳ (Cron `*/30 * * * *` và `0 0 * * *`), hoàn toàn miễn phí cho kho lưu trữ cá nhân/private, không cần thuê máy chủ VPS treo 24/7. | Cron của GitHub Actions có thể trễ từ 1-5 phút trong giờ cao điểm của GitHub. *Giải pháp:* Chấp nhận được vì deadline trường học quét chu kỳ 30 phút là đủ an toàn. |
| **Database** | **PostgreSQL (Supabase Cloud)** | Hệ quản trị cơ sở dữ liệu quan hệ mạnh mẽ, hỗ trợ ACID, ràng buộc khóa ngoại (Foreign Keys) chống sai lệch dữ liệu, miễn phí và có giao diện web quản lý tiện lợi. | Giới hạn số lượng connection đồng thời ở gói Free. *Giải pháp:* Sử dụng connection pooler (Session/Transaction mode) của Supabase và đóng kết nối ngay sau khi query xong qua Context Manager. |
| **Discord Integration** | **Discord REST API Trực tiếp (Pure `requests`)** | Không dùng thư viện nặng như `discord.py` (vốn đòi hỏi WebSocket giữ kết nối liên tục 24/7), giúp hệ thống hoạt động hoàn hảo dưới mô hình Serverless và CLI Job. | Phải tự quản lý format payload JSON và handle rate limit (HTTP 429). *Giải pháp:* Tự viết wrapper chuẩn trong `src/discord_api.py`. |

---

### 3. Chiến lược Xác thực & Phân quyền (Auth & Security Strategy)

1. **Discord Webhook Verification (Ed25519 Signature):**
   - Mọi request từ Discord gửi vào `POST /api/interactions` bắt buộc phải chứa 2 headers: `X-Signature-Ed25519` và `X-Signature-Timestamp`.
   - Backend sử dụng thư viện mật mã `pynacl` cùng public key `DISCORD_PUBLIC_KEY` để giải mã chữ ký. Request giả mạo hoặc thiếu timestamp sẽ bị từ chối ngay lập tức bằng HTTP 401.
2. **External API Authentication (Constant-Time API Key):**
   - Các dịch vụ tích hợp bên thứ ba (Zapier, Google Form, Webhook ngoài) khi gọi `POST /api/add_deadline` phải truyền header `X-API-Key`.
   - Backend dùng `hmac.compare_digest` để so sánh mã key, ngăn chặn triệt để tấn công dò mã dạng Timing Attack.
3. **Web Dashboard Security:**
   - Phiên bản MVP: Web Dashboard công khai quyền xem (Read-only) cho mọi sinh viên trong nhóm có link. Quyền ghi (Thêm deadline, đánh dấu hoàn thành) được bảo vệ bằng cơ chế xác thực session hoặc kiểm tra Secret Passkey nội bộ được lưu trong LocalStorage.
4. **Database Security & Secrets Management:**
   - 100% thông tin nhạy cảm (`DATABASE_URL`, `DISCORD_BOT_TOKEN`, `MOODLE_TOKEN`, `GOOGLE_SERVICE_ACCOUNT_JSON`) được lưu trữ tại GitHub Actions Secrets và Vercel Environment Variables.
   - Kết nối cơ sở dữ liệu Supabase bắt buộc sử dụng SSL mode (`sslmode=require`).

---

## PHẦN 3: ĐẶC TẢ DỮ LIỆU & API (DATA & API SPECS)

### 1. Mô hình Dữ liệu (Database Schema)

#### 1.1. Sơ đồ Quan hệ Thực thể (ERD)

```mermaid
erDiagram
    COURSES ||--o{ DEADLINES : "has"
    COURSES ||--o{ ANNOUNCEMENTS : "contains"
    COURSES ||--o{ COURSE_MODULES : "owns"
    COURSES ||--o{ FORUM_DISCUSSIONS : "has"
    
    COURSES {
        serial courses_id PK
        varchar course_name UK "Mã môn học (VD: CSC10014)"
        varchar display_name "Tên tiếng Việt hiển thị"
        varchar lms_courses_id UK "ID khóa học trên Moodle"
        varchar chat_id UK "Discord Channel ID"
        timestamp last_crawled_time "Lần quét gần nhất"
        varchar discord_category_id "Category ID theo học kỳ"
    }

    DEADLINES {
        serial deadlines_id PK
        int courses_id FK
        varchar deadline_name "Tên bài tập/deadline"
        varchar lms_deadlines_id UK "Mã duy nhất (ICS UID / UUID)"
        timestamp due_time "Hạn nộp bài"
        timestamp created_time "Thời điểm tạo"
        varchar source_url "Link bài tập trên Moodle hoặc Web"
        varchar source "moodle | manual | external"
        varchar added_by "Người tạo (Discord Tag / Web User)"
        boolean notified_new "Đã gửi thông báo mới"
        boolean reminded_3d "Đã nhắc trước 3 ngày"
        boolean reminded_1d "Đã nhắc khẩn cấp trước 24h"
        boolean completed "Trạng thái hoàn thành"
        varchar completed_by "Người đánh dấu hoàn thành"
        varchar discord_message_id "ID tin nhắn trên Discord"
        varchar discord_channel_id "ID kênh Discord"
        varchar discord_event_id "ID sự kiện Discord"
    }

    ANNOUNCEMENTS {
        serial announcements_id PK
        int courses_id FK
        varchar announcements_name "Tiêu đề thông báo"
        varchar lms_announcements_id UK "Mã thông báo Moodle"
        timestamp created_time "Thời gian đăng"
        varchar source_url "Link thông báo"
    }

    COURSE_MODULES {
        serial module_id PK
        int courses_id FK
        varchar lms_module_id "ID module trên Moodle"
        varchar module_type "resource | assign | quiz | url"
        varchar module_name "Tên tài liệu / bài giảng"
        timestamp time_modified "Thời điểm cập nhật tài liệu"
    }

    FORUM_DISCUSSIONS {
        serial discussion_id PK
        int courses_id FK
        varchar lms_discussion_id UK "ID bài đăng diễn đàn"
        varchar forum_name "Tên diễn đàn"
        varchar subject "Chủ đề bài đăng"
        varchar author "Giảng viên / Người đăng"
        timestamp created_time "Thời gian đăng"
    }

    NOTIFICATIONS {
        serial notifications_id PK
        varchar type "deadline | announcement"
        timestamp sent_at "Thời điểm gửi"
        text message "Nội dung tin nhắn"
        timestamp created_at "Thời điểm ghi log"
        int reference_id "Trỏ đến deadline_id hoặc announcement_id"
    }

    ERROR_LOGS {
        serial error_logs_id PK
        varchar source "moodle_calendar | moodle_api | discord_api | system"
        varchar severity "warning | error | critical"
        varchar command "Lệnh đang thực thi"
        varchar reference_type "course | deadline | notification"
        int reference_id "ID đối tượng lỗi"
        text error_message "Nội dung thông báo lỗi"
        text stack_trace "Chi tiết stack trace"
        timestamp created_at "Thời điểm phát sinh lỗi"
    }
```

---

### 2. Bảng Đặc tả API RESTful

#### 2.1. Module: Khóa học (Courses)

##### `GET /api/courses`
- **Mục đích:** Lấy danh sách tất cả các môn học đang theo dõi cùng số lượng deadline đang chờ nộp.
- **Query Params:** Không có.
- **Response Success (200 OK):**
```json
{
  "ok": true,
  "data": [
    {
      "courses_id": 3,
      "course_name": "CSC10105",
      "display_name": "Nhập môn tư duy thuật toán",
      "chat_id": "1539917459509878784",
      "lms_courses_id": "4210",
      "discord_category_id": "1539917450000000000",
      "pending_deadlines_count": 2
    }
  ]
}
```
- **Error Codes:** `500 Internal Server Error` (Lỗi kết nối cơ sở dữ liệu).

---

#### 2.2. Module: Deadline & Nhiệm vụ (Deadlines)

##### `GET /api/deadlines`
- **Mục đích:** Truy vấn danh sách deadline với các bộ lọc phục vụ hiển thị trên Web Dashboard.
- **Query Params:**
  - `course` *(optional - string)*: Lọc theo mã môn (VD: `CSC10105`).
  - `status` *(optional - string)*: `all` | `pending` | `urgent` | `completed` | `overdue`. Mặc định: `all`.
- **Response Success (200 OK):**
```json
{
  "ok": true,
  "total": 1,
  "data": [
    {
      "deadlines_id": 15,
      "courses_id": 3,
      "course_name": "CSC10105",
      "course_display_name": "Nhập môn tư duy thuật toán",
      "deadline_name": "Nộp bài tập thực hành Tuần 3",
      "due_time": "2026-09-25T16:59:00Z",
      "due_time_vn": "23:59 25/09/2026",
      "source": "moodle",
      "source_url": "https://courses.fit.hcmus.edu.vn/mod/assign/view.php?id=12345",
      "added_by": null,
      "completed": false,
      "completed_by": null,
      "is_urgent": false,
      "is_overdue": false,
      "countdown_text": "Còn 5 ngày 7 giờ",
      "discord_channel_id": "1539917459509878784"
    }
  ]
}
```
- **Error Codes:** `400 Bad Request` (Tham số `status` không hợp lệ).

---

##### `POST /api/deadlines`
- **Mục đích:** Thêm mới deadline nội bộ thủ công từ Web Dashboard.
- **Request Headers:** `Content-Type: application/json`
- **Request Body (JSON):**
```json
{
  "mon": "CSC10105",
  "ten": "Họp chốt phân chia công việc đồ án",
  "han_chot": "28/09/2026 21:00",
  "nguoi_phu_trach": "Truong Bao Nguyen",
  "ghi_chu_url": "https://docs.google.com/document/d/xyz"
}
```
- **Response Success (201 Created):**
```json
{
  "ok": true,
  "deadlines_id": 28,
  "mon": "CSC10105",
  "ten": "Họp chốt phân chia công việc đồ án",
  "han_chot_utc": "2026-09-28T14:00:00Z",
  "message": "Thêm deadline nội bộ thành công!"
}
```
- **Error Codes:** 
  - `400 Bad Request` (Thiếu trường bắt buộc `mon`, `ten`, `han_chot` hoặc sai format ngày).
  - `409 Conflict` (Deadline trùng lặp).

---

##### `POST /api/deadlines/toggle`
- **Mục đích:** Chuyển đổi trạng thái hoàn thành (`completed: true/false`) của deadline.
- **Request Headers:** `Content-Type: application/json`
- **Request Body (JSON):**
```json
{
  "deadlines_id": 15,
  "completed": true,
  "completed_by": "Truong Bao Nguyen"
}
```
- **Response Success (200 OK):**
```json
{
  "ok": true,
  "deadlines_id": 15,
  "completed": true,
  "completed_by": "Truong Bao Nguyen",
  "updated_at": "2026-09-19T13:45:00Z"
}
```
- **Error Codes:** 
  - `400 Bad Request` (Thiếu `deadlines_id`).
  - `404 Not Found` (Không tìm thấy deadline tương ứng).

---

#### 2.3. Module: Thống kê & Tổng quan (Dashboard Stats)

##### `GET /api/stats`
- **Mục đích:** Cung cấp số liệu tổng hợp phục vụ thanh tiến độ và các thẻ chỉ số trên Web Dashboard.
- **Response Success (200 OK):**
```json
{
  "ok": true,
  "data": {
    "total_deadlines": 24,
    "completed_deadlines": 18,
    "pending_deadlines": 6,
    "completion_rate": 75.0,
    "urgent_24h": 1,
    "upcoming_3d": 2,
    "overdue": 0,
    "total_courses": 6
  }
}
```

---

#### 2.4. Module: Discord & External Webhook

##### `POST /api/interactions`
- **Mục đích:** Endpoint webhook nhận và xử lý Slash Commands từ Discord (Ping PONG, `/add_deadline`, `/deadline`).
- **Request Headers:** `X-Signature-Ed25519`, `X-Signature-Timestamp`
- **Response Success (200 OK):**
```json
{
  "type": 4,
  "data": {
    "content": "✅ Đã thêm deadline **[Nộp báo cáo tuần]** cho môn **CSC10105** (Hạn: 23:59 25/09/2026)."
  }
}
```
- **Error Codes:** `401 Unauthorized` (Chữ ký Ed25519 không khớp hoặc thiếu timestamp).

---

##### `POST /api/add_deadline`
- **Mục đích:** API cho bên thứ ba (Zapier, Google Forms, Scripts tự động).
- **Request Headers:** `X-API-Key: <SECRET_KEY>`, `Content-Type: application/json`
- **Request Body (JSON):**
```json
{
  "mon": "CSC10014",
  "ten": "Nộp bài tập lớn giai đoạn 1",
  "han_chot": "30/09/2026 23:59",
  "nguon": "Google Form",
  "id": "form-response-9921"
}
```
- **Response Success (201 Created):**
```json
{
  "ok": true,
  "deadlines_id": 31,
  "mon": "CSC10014",
  "han_chot_utc": "2026-09-30T16:59:00Z"
}
```
- **Error Codes:** `401 Unauthorized` (Sai hoặc thiếu API Key).

---

## PHẦN 4: HƯỚNG DẪN DỰ ÁN & VẬN HÀNH (DEV ENVIRONMENT & README)

### 1. Cấu trúc Thư mục Dự án Chuẩn hóa (Project Tree)

```text
Notification Project/
├── .github/
│   └── workflows/
│       └── notify.yml               # CI/CD Workflow: chạy cron định kỳ mỗi 30 phút và 7h sáng
├── api/                             # Serverless API Gateway chạy trên Vercel
│   ├── index.py                     # Entrypoint điều hướng toàn bộ REST API & Discord Interactions
│   ├── add_deadline.py              # Endpoint cho API bên thứ ba
│   └── interactions.py              # Endpoint chuyên biệt cho Discord
├── frontend/                        # Web Dashboard UI (Vite + React + Tailwind CSS)
│   ├── public/                      # Static assets, logo, favicon
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts            # REST API Client giao tiếp với /api/*
│   │   ├── components/
│   │   │   ├── Header.tsx           # Thanh điều hướng, trạng thái server, nút đổi theme
│   │   │   ├── StatsCards.tsx       # 4 thẻ thống kê tiến độ, đếm deadline khẩn cấp
│   │   │   ├── DeadlineList.tsx     # Danh sách deadline, countdown, bộ lọc & checkbox
│   │   │   ├── AddDeadlineModal.tsx # Form modal thêm deadline nội bộ
│   │   │   ├── CourseList.tsx       # Danh sách môn học & liên kết Discord
│   │   │   └── Announcements.tsx    # Feed thông báo & tài liệu mới từ Moodle
│   │   ├── App.tsx                  # Root Application Component & Tab Router
│   │   ├── main.tsx                 # React DOM mount point
│   │   └── index.css                # Tailwind directives & custom styling
│   ├── index.html                   # HTML template
│   ├── package.json                 # Node dependencies (React, Lucide, Tailwind)
│   ├── tsconfig.json                # TypeScript compiler configuration
│   └── vite.config.ts               # Vite build config & proxy /api khi dev
├── migrations/                      # Toàn bộ SQL Scripts di chuyển cơ sở dữ liệu
│   ├── 001_create_database.sql      # Khởi tạo schema gốc
│   ├── 002_add_display_name.sql     # Thêm display_name tiếng Việt
│   ├── 004_add_discord_category.sql # Cấu hình category ID học kỳ
│   └── 005_add_manual_deadline.sql  # Cột hỗ trợ deadline thủ công (source, added_by)
├── scripts/                         # CLI Utility Scripts phục vụ vận hành & bảo trì
│   ├── register_commands.py         # Đăng ký Slash Commands lên Discord Developer Portal
│   ├── set_category.py              # Gán category Discord cho môn học
│   ├── rename_all_channels.py       # Đồng bộ chuẩn hóa tên các kênh Discord
│   └── run_server.py                # Chạy local server tích hợp Web & API
├── src/                             # Core Python Business Logic Library
│   ├── __init__.py
│   ├── config.py                    # Đọc và validate biến môi trường, Timezone HCM
│   ├── database.py                  # Quản lý kết nối PostgreSQL & Context Manager
│   ├── db_queries.py                # Toàn bộ câu truy vấn SQL (Data Access Layer)
│   ├── discord_api.py               # Wrapper gọi Discord REST API (Kênh, Event, Tin nhắn)
│   ├── moodle_parser.py             # Bóc tách và parse file iCalendar (.ics)
│   ├── moodle_api.py                # Giao tiếp Moodle Web Services API
│   ├── announcement_tracker.py      # Bộ quét thông báo & tài liệu khóa học mới
│   ├── event_tracker.py             # Bộ quét deadline và tạo Scheduled Events
│   ├── google_calendar_sync.py      # Tích hợp đồng bộ Google Calendar
│   ├── notion_sync.py               # Tích hợp đồng bộ Notion Todo List
│   ├── interactions.py              # Logic giải mã chữ ký Ed25519 & dispatch lệnh Discord
│   ├── external_api.py              # Logic xác thực API Key & thêm deadline từ bên ngoài
│   └── utils.py                     # Hàm tiện ích (parse_due_time, format date, clean HTML)
├── .env.example                     # File mẫu biến môi trường
├── .gitignore                       # Danh sách loại trừ Git
├── .vercelignore                    # Danh sách file không đưa lên Vercel Serverless
├── main.py                          # Entrypoint cho GitHub Actions runner
├── pyproject.toml                   # Khai báo dependency cho Vercel Python Builder
├── requirements.txt                 # Khai báo thư viện Python (requests, psycopg2, pynacl)
├── vercel.json                      # Cấu hình routing và rewrite của Vercel
└── README.md                        # Tài liệu hướng dẫn sử dụng và cài đặt
```

---

### 2. File `.env.example` Hoàn chỉnh

```env
# ==============================================================================
# COURSE FIT HCMUS BOT & DASHBOARD - ENVIRONMENT CONFIGURATION
# ==============================================================================

# 1. MOODLE LMS CONFIGURATION
# Lấy từ Moodle -> Lịch (Calendar) -> Xuất lịch (Export Calendar) -> Sao chép URL .ics
MOODLE_CALENDAR_URL="https://courses.fit.hcmus.edu.vn/calendar/export_execute.php?userid=YOUR_USER_ID&authtoken=YOUR_AUTH_TOKEN&preset_what=all&preset_time=recentupcoming"

# Token Moodle Web Service (Lấy từ F12 -> Application -> Local Storage hoặc Mobile App Key)
# Dùng để quét tài liệu khóa học (slides, files) và thông báo diễn đàn mới
MOODLE_TOKEN="your_moodle_wstoken_here"


# 2. DISCORD APPLICATION & BOT CONFIGURATION
# Lấy từ Discord Developer Portal (https://discord.com/developers/applications)
DISCORD_BOT_TOKEN="your_discord_bot_token_here"
DISCORD_APPLICATION_ID="your_discord_application_id_here"

# Public Key (Ed25519) dùng để xác thực các request Webhook Slash Command từ Discord
DISCORD_PUBLIC_KEY="your_discord_application_public_key_hex_here"

# ID của Discord Server (Guild ID) cần bot quản lý (Bật Developer Mode -> Chuột phải tên Server -> Copy ID)
DISCORD_SERVER_ID="123456789012345678"


# 3. SUPABASE POSTGRESQL DATABASE
# Connection String lấy từ Supabase Dashboard -> Settings -> Database -> Connection string (URI)
# Khuyên dùng kết nối Transaction/Session Pooler (Port 5432 hoặc 6543)
DATABASE_URL="postgresql://postgres.yourprojectref:yourpassword@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres?sslmode=require"


# 4. EXTERNAL API AUTHENTICATION
# Khóa bí mật dùng để bảo vệ endpoint POST /api/add_deadline khi gọi từ Zapier/Google Form
EXTERNAL_API_KEY="generate_a_very_secure_random_token_here"


# 5. GOOGLE CALENDAR INTEGRATION (TUỲ CHỌN)
# Nội dung file JSON của Google Cloud Service Account (đã rút gọn thành 1 dòng hoặc đường dẫn)
GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", "project_id": "...", "private_key": "...", "client_email": "..."}'

# ID của Google Calendar cần đồng bộ (VD: your_group_calendar@group.calendar.google.com)
GOOGLE_CALENDAR_ID="your_google_calendar_id@group.calendar.google.com"


# 6. NOTION TODO LIST INTEGRATION (TUỲ CHỌN)
# Notion Internal Integration Secret Token (bắt đầu bằng ntn_...)
NOTION_API_TOKEN="ntn_your_notion_integration_token_here"

# ID của Database bảng Todo List trên Notion
NOTION_DATABASE_ID="your_notion_database_32_chars_id_here"


# 7. LOCAL SERVER SETTINGS
PORT=8000
NODE_ENV="development"
```

---

### 3. Khung Hướng dẫn Cài đặt & Vận hành (`README.md`)

```markdown
# Course FIT HCMUS - Deadline & Academic Activity Hub 🎓🤖

Hệ thống tự động hóa quản lý học tập thông minh: Đồng bộ bài tập, deadline, tài liệu và thông báo từ Moodle (courses.fit.hcmus.edu.vn) sang Discord Server, Google Calendar, Notion và Web Dashboard trực quan theo kiến trúc **100% Serverless**.

---

## 🚀 Yêu cầu Môi trường (Prerequisites)

- **Python:** Phiên bản `>= 3.10` (Khuyên dùng `3.12`).
- **Node.js:** Phiên bản `>= 18.0.0` và `npm >= 9.0.0` (cho Web Dashboard).
- **PostgreSQL Database:** Tài khoản miễn phí tại [Supabase](https://supabase.com).
- **Discord Developer Account:** Bot Application đã được cấu hình với các quyền: `Manage Channels`, `Create Events`, `Send Messages`, `Create Public Threads`, `Read Message History`.

---

## 🛠️ Cài đặt Cục bộ (Local Development Setup)

### Bước 1: Clone mã nguồn & Cài đặt thư viện Backend
```bash
git clone https://github.com/your-username/course_fit_bot.git
cd course_fit_bot

# Khởi tạo virtual environment Python
python -m venv venv
source venv/bin/activate  # Trên Windows: venv\Scripts\activate

# Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt
```

### Bước 2: Thiết lập Biến Môi Trường
```bash
cp .env.example .env
# Mở file .env và điền các thông số: DATABASE_URL, DISCORD_BOT_TOKEN, MOODLE_CALENDAR_URL...
```

### Bước 3: Khởi tạo Cơ sở Dữ liệu (Database Migration)
Mở giao diện **SQL Editor** trên Supabase Dashboard và thực thi tuần tự các file script trong thư mục `migrations/`:
1. `migrations/001_create_database.sql`
2. `migrations/002_add_display_name.sql`
3. `migrations/004_add_discord_category.sql`
4. `migrations/005_add_manual_deadline.sql`

### Bước 4: Cài đặt & Chạy Web Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
# Dashboard sẽ khởi chạy tại: http://localhost:5173 (tự động proxy API về http://localhost:8000)
```

### Bước 5: Chạy Backend Serverless API Cục bộ
Tại thư mục gốc dự án:
```bash
python scripts/run_server.py
# API server sẵn sàng tại: http://localhost:8000
```

### Bước 6: Chạy thử Bot thủ công (CLI Modes)
```bash
python main.py                  # Quét và cập nhật deadline Moodle mới nhất
python main.py --summary        # Gửi báo cáo tóm tắt deadline hằng ngày
python main.py --progress       # Gửi báo cáo tiến độ chi tiết (thanh progress bar)
python main.py --announcements  # Quét tài liệu bài giảng và thông báo diễn đàn
python main.py --sync-channels  # Tự động tạo và chuẩn hóa tên kênh Discord theo mã môn
python main.py --sync-gcal      # Đồng bộ toàn bộ deadline lên Google Calendar
python main.py --sync-notion    # Đồng bộ toàn bộ deadline lên Notion Todo List
```

---

## 🚢 Hướng dẫn Triển khai (Deployment)

### 1. Triển khai Web & API Gateway lên Vercel
1. Cài đặt Vercel CLI: `npm install -g vercel`
2. Đăng nhập và liên kết dự án:
   ```bash
   vercel
   ```
3. Truy cập **Project Settings -> Environment Variables** trên Vercel và thêm toàn bộ các biến trong `.env`.
4. Deploy bản chính thức:
   ```bash
   vercel --prod
   ```
5. Sao chép URL triển khai của Vercel (VD: `https://course-fit-bot.vercel.app/api/interactions`) và dán vào mục **Interactions Endpoint URL** trong Discord Developer Portal.

### 2. Triển khai Bộ quét Cron tự động (GitHub Actions)
1. Tạo một Private Repository trên GitHub và push toàn bộ mã nguồn lên.
2. Vào **Settings -> Secrets and variables -> Actions** trong Repository.
3. Bấm **New repository secret** và thêm các khóa bảo mật tương ứng (`DATABASE_URL`, `DISCORD_BOT_TOKEN`, `MOODLE_CALENDAR_URL`, `MOODLE_TOKEN`...).
4. File `.github/workflows/notify.yml` sẽ tự động kích hoạt tiến trình quét mỗi 30 phút mà không cần can thiệp thủ công.
```

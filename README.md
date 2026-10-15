# Course FIT HCMUS - Discord Notification Bot

Hệ thống tự động đồng bộ deadline, tài liệu môn học và thông báo từ Moodle (`courses.fit.hcmus.edu.vn`) sang Server Discord, kèm **Web Dashboard** quản lý deadline và **Slash Commands** trên Discord.

Bot gọi trực tiếp Discord REST API (không dùng `discord.py`), nên không cần server 24/7:
- **Tác vụ định kỳ** (quét Moodle, gửi thông báo, báo cáo) chạy bằng **GitHub Actions** hoặc **máy trạm Termux** trên điện thoại.
- **Slash Commands + Web Dashboard + REST API** chạy trên **Vercel Serverless**.
- **Trạng thái** (đã thông báo, đã nhắc, đã hoàn thành...) lưu trong **Supabase PostgreSQL** để chống gửi trùng.

## Kiến trúc tổng quan

```
                ┌──────────────────────────── Moodle ────────────────────────────┐
                │  iCalendar (.ics)          REST Web Services (MOODLE_TOKEN)    │
                └───────┬──────────────────────────────┬─────────────────────────┘
                        │                              │ assignments, quizzes, calendar,
                        ▼                              ▼ modules, forums, submission status
   GitHub Actions / Termux cron ──►  main.py  ──►  course_bot/jobs/
                                                   │   ├─ notify (ics_feed) / crawl_deadlines
                                                   │   ├─ announcements
                                                   │   └─ services/ (kênh môn, react ✅ → hoàn thành)
                                                   ▼
                                       Supabase PostgreSQL (migrations/)
                                         ▲            │
                                         │            ├──► Discord (kênh môn, @everyone, Scheduled Events)
                                         │            ├──► Notion Todo List   (tuỳ chọn)
                                         │            └──► Google Calendar    (tuỳ chọn)
                                         │
   Discord Slash Commands ─┐             │
   Web Dashboard (React) ──┼──► Vercel: api/index.py ──┘
   API bên thứ 3 (API key)─┘
```

## Tính năng

**Bot định kỳ (`main.py`)**
- **Deadline từ 2 nguồn:** file `.ics` của Moodle và Moodle REST API (`mod_assign`, `mod_quiz`, `core_calendar_get_action_events_by_timesort`).
- **Chuỗi nhắc nhở:** `DEADLINE MỚI` → `CÒN 3 NGÀY` → `CÒN 24 GIỜ`, mỗi mốc chỉ gửi một lần.
- **Tự động hoàn thành:** đánh dấu xong khi có người react `✅`, hoặc khi Moodle báo bài đã nộp (auto-complete qua `mod_assign_get_submission_status`).
- **Theo dõi nội dung khóa học:** phát hiện tài liệu, folder, URL, quiz mới và bài đăng diễn đàn của giảng viên.
- **Quản lý kênh & học kỳ:** tạo kênh theo format `#<viết-tắt-tên-môn>-<mã-môn>` (vd: `#nmttnt-csc10014`), xếp vào Category `kì N`.
- **Báo cáo:** tổng hợp deadline hằng ngày (≈ 6:55 sáng giờ VN) và báo cáo tiến độ kèm progress bar.
- **Đồng bộ ngoài:** Notion Todo List và Google Calendar (nhắc 24h, 3h, 30p trên điện thoại); đổi trạng thái `[XONG]` khi hoàn thành.
- **Dọn tin nhắn trùng:** `--dedup` quét và xoá tin nhắn bot gửi lặp.

**Slash Commands (Vercel)**
- `/add_deadline ten han_chot [mon]` — thêm deadline nội bộ (vd: mốc đồ án nhóm). Bỏ trống `mon` để tự nhận theo kênh đang chat. Deadline này đi chung luồng nhắc nhở với Moodle.
- `/deadline [mon] [so_luong]` — xem các deadline sắp tới (mặc định 5, tối đa 15).
- Input được làm sạch để chặn mention injection (`@everyone`, `@here`, role ping) và trùng lặp.

**Web Dashboard (`frontend/`)**
- React 18 + TypeScript + Vite + Tailwind, hỗ trợ dark mode và giao diện mobile (Sidebar trên desktop, BottomNav trên điện thoại).
- Các tab: Tổng quan (progress, thống kê), Deadline (dạng List / Kanban, lọc, tìm kiếm, thêm, đánh dấu xong), Môn học, Thông báo, Cài đặt.

## Cấu trúc thư mục

| Đường dẫn | Mục đích |
|---|---|
| `main.py` | CLI entry point cho các tác vụ định kỳ (chọn chế độ bằng tham số). |
| `course_bot/jobs/` | Mỗi chế độ CLI một file: `notify.py` (mặc định), `reports.py` (`--summary`, `--progress`), `announcements.py`, `sync_channels.py`, `sync_external.py` (`--sync-notion`, `--sync-gcal`), `crawl_deadlines.py`, `dedup.py`. |
| `course_bot/services/` | Use-case dùng chung cho nhiều entry point: `channel_resolver.py` (tìm/rename/tạo kênh môn), `manual_deadlines.py` (thêm deadline thủ công từ Web, Discord, API), `completion_tracker.py` (react `✅` → hoàn thành), `deadline_crawler.py` (Moodle API), `announcement_tracker.py` (nội dung Moodle mới). |
| `course_bot/core/` | `config.py` (đọc biến môi trường, hỗ trợ `.env`), `time_utils.py` (`LOCAL_TZ` = UTC+7, parse hạn chót), `logging_setup.py`. |
| `course_bot/db/` | `connection.py` (kết nối PostgreSQL) và `repositories/` (SQL theo từng bảng: `courses.py`, `deadlines.py`, `moodle_content.py`, `notifications.py`). |
| `course_bot/integrations/` | Client mỏng cho dịch vụ ngoài: `moodle/webservice.py` (Moodle Web Services), `discord/rest.py` (Discord REST: kênh, tin nhắn, reaction, Scheduled Events), `discord/signature.py` (xác thực Ed25519), `notion/client.py`, `google_calendar/client.py`. |
| `course_bot/domain/` | Logic thuần, không I/O: `course_naming.py` (tách mã/tên môn, tên kênh), `semester.py` (tính học kỳ). Việc tải và parse `.ics` nằm ở `integrations/moodle/ics_feed.py`. |
| `course_bot/web/` | Tầng HTTP cho Vercel: `router.py` (điều hướng `/api/*`), `http_utils.py` (JSON, CORS), `routes/dashboard.py` (API cho Web Dashboard), `routes/discord_interactions.py` (Slash Commands), `routes/external.py` (thêm deadline cho bên thứ 3, xác thực `X-API-Key`). Không import `jobs/`, Notion hay Google Calendar. |
| `api/index.py` | Entry point duy nhất của Vercel: chỉ re-export `handler` từ `course_bot/web/router.py`. |
| `frontend/` | Web Dashboard (Vite + React + TS + Tailwind). Trong `frontend/src/`: `app/` (`App.tsx`, `main.tsx`, `layout/` Header/Sidebar/BottomNav, hook `useDashboardData` và `useTheme`), `features/<tên>/` (giao diện + hook dữ liệu của từng tab, ví dụ `deadlines/useDeadlines.ts`), `shared/` (`ui/`, `api/client.ts`, `types/`, `utils/`, `hooks/`). Import khác thư mục dùng alias `@/` (khai báo ở cả `tsconfig.json` và `vite.config.ts`). |
| `migrations/` | SQL tạo và nâng cấp schema (chạy theo thứ tự số). |
| `scripts/` | Công cụ phụ: đăng ký slash command, chạy server local, setup Termux, đổi tên kênh, gán category, dọn tin nhắn... |
| `tests/` | Unit test (pytest) và các script debug thủ công. |
| `.github/workflows/` | `notify.yml` (mỗi 30 phút) và `daily_summary.yml` (báo cáo sáng). |
| `docs/` | Tài liệu kỹ thuật, lộ trình tính năng, đặc tả UI. |
| `docs/design/mobile-13t-pro/` | Bản thiết kế giao diện mobile (tối ưu cho Xiaomi 13T Pro). |
| `docs/guides/termux-workstation.md` | Hướng dẫn biến điện thoại Android thành máy trạm chạy bot. |

## Biến môi trường

| Biến | Bắt buộc | Dùng cho |
|---|---|---|
| `DISCORD_BOT_TOKEN` | ✅ | Gọi Discord API. |
| `DISCORD_SERVER_ID` | ✅ | ID Server Discord. |
| `MOODLE_CALENDAR_URL` | ✅ | URL xuất lịch `.ics` của Moodle. |
| `DATABASE_URL` | ✅ | Connection string Supabase PostgreSQL (cả bot lẫn Vercel). |
| `MOODLE_TOKEN` | Khuyên dùng | Moodle REST API: crawler deadline, auto-complete, tài liệu, diễn đàn. |
| `DISCORD_PUBLIC_KEY` | Slash Commands | Xác thực request Discord gửi tới Vercel. |
| `DISCORD_APPLICATION_ID` | Slash Commands | Dùng bởi `scripts/ops/register_commands.py`. |
| `EXTERNAL_API_KEY` | Tuỳ chọn | Bảo vệ endpoint `POST /api/add_deadline`. |
| `NOTION_API_TOKEN`, `NOTION_DATABASE_ID` | Tuỳ chọn | Đồng bộ Notion ([hướng dẫn](docs/guides/notion-todo-list-integration.md)). |
| `GOOGLE_SERVICE_ACCOUNT_JSON` hoặc `GOOGLE_SERVICE_ACCOUNT_FILE`, `GOOGLE_CALENDAR_ID` | Tuỳ chọn | Đồng bộ Google Calendar ([hướng dẫn](docs/guides/google-calendar-integration.md)). |

> ⚠️ Không commit `.env` hay `service_account*.json` (đã có trong `.gitignore`). Repo GitHub nên để **Private**.

## Cài đặt

### 1. Database (Supabase)
1. Tạo project tại [Supabase](https://supabase.com), lấy **Connection string (URI)** trong **Settings → Database**.
2. Mở **SQL Editor** và chạy lần lượt các file trong `migrations/` theo thứ tự số (`001` → `002` → `004` → `005`).

### 2. Discord Bot
1. Tạo ứng dụng trên [Discord Developer Portal](https://discord.com/developers/applications), lấy **Bot Token**, **Application ID** và **Public Key**.
2. Mời bot vào Server với quyền: Quản lý kênh, Quản lý sự kiện, Gửi tin nhắn, Thêm reaction, Đọc lịch sử tin nhắn.

### 3. Chạy định kỳ bằng GitHub Actions
1. Đẩy mã nguồn lên repo **Private** (gồm cả `.github/workflows`).
2. Vào **Settings → Secrets and variables → Actions**, thêm các secret ở bảng trên (các biến dùng cho bot: Discord, Moodle, Database, Notion, Google).
3. Vào tab **Actions → Notification Bot → Run workflow** để chạy thử. Có thể chọn chế độ: `notify`, `summary`, `progress`, `announcements`, `sync-channels`, `sync-notion`, `sync-gcal`, `crawl-deadlines`.

| Workflow | Lịch (UTC) | Giờ Việt Nam | Lệnh |
|---|---|---|---|
| `Notification Bot` (`notify.yml`) | `*/30 * * * *` | Mỗi 30 phút | `python main.py` |
| `Daily Summary` (`daily_summary.yml`) | `55 23 * * *` | 06:55 sáng | `python main.py --summary` |

> GitHub Actions cron có thể trễ vài phút đến vài chục phút khi hàng đợi đông. Nếu cần đúng giờ hơn, dùng máy trạm Termux (xem bên dưới).

### 4. Deploy Slash Commands + Web Dashboard lên Vercel
1. Import repo vào Vercel. `vercel.json` đã cấu hình build `frontend/` và chuyển `/api/*` về `api/index.py`.
2. Thêm biến môi trường trên Vercel: `DATABASE_URL`, `DISCORD_PUBLIC_KEY`, và `EXTERNAL_API_KEY` (nếu dùng).
3. Trong Discord Developer Portal, đặt **Interactions Endpoint URL** = `https://<domain>.vercel.app/api/interactions`.
4. Đăng ký lệnh (chạy một lần, hoặc mỗi khi sửa danh sách lệnh):
   ```bash
   python scripts/ops/register_commands.py
   ```

### 5. (Tuỳ chọn) Máy trạm Termux
Chạy bot bằng cron trên điện thoại Android, kèm 10 phím Widget 1 chạm. Xem chi tiết tại [docs/guides/termux-workstation.md](docs/guides/termux-workstation.md) và script `scripts/termux/setup_termux.sh`.

## Phát triển cục bộ

```bash
pip install -r requirements.txt
# Tạo file .env chứa các biến môi trường ở bảng trên
```

**Chạy các tác vụ bot:**
```bash
python main.py                    # Quét deadline (ICS + Moodle API), gửi thông báo/nhắc nhở, kiểm tra tài liệu & diễn đàn
python main.py --summary          # Báo cáo tổng hợp deadline hằng ngày
python main.py --progress         # Báo cáo tiến độ chi tiết (#tien-do-deadline)
python main.py --announcements    # Chỉ kiểm tra tài liệu và diễn đàn Moodle
python main.py --crawl-deadlines  # Chỉ thu thập deadline từ Moodle API
python main.py --sync-channels    # Tạo/chuẩn hoá tên kênh Discord theo Moodle
python main.py --sync-notion      # Đồng bộ toàn bộ deadline lên Notion
python main.py --sync-gcal        # Đồng bộ toàn bộ deadline lên Google Calendar
python main.py --dedup [--channel <tên>] [--limit <N>] [--dry-run]   # Dọn tin nhắn trùng
```

**Chạy API + Web Dashboard (Windows PowerShell, từ thư mục gốc repo):**

Cần Python ≥ 3.10 và Node.js ≥ 18. Backend Python không cần build; frontend React được build thành `frontend/dist`.

```powershell
.\scripts\dev\start.ps1 -Install   # lần đầu: cài thư viện Python + npm, build frontend, chạy http://localhost:8000
.\scripts\dev\start.ps1            # những lần sau: build frontend + chạy API tại http://localhost:8000
.\scripts\dev\start.ps1 -Dev       # chế độ dev: backend ở cửa sổ mới + Vite tại http://localhost:5173 (sửa code thấy ngay)
```

Làm tay từng bước:
```powershell
# Windows PowerShell 5.1 (mặc định trên Windows) — không hỗ trợ `&&`
pip install -r requirements.txt pytest
npm --prefix frontend install
npm --prefix frontend run build; if ($?) { python scripts/dev/run_server.py }   # http://localhost:8000
```
```bash
# Git Bash, macOS, Linux hoặc PowerShell 7+
pip install -r requirements.txt pytest
npm --prefix frontend install
npm --prefix frontend run build && python scripts/dev/run_server.py   # http://localhost:8000
```
Chế độ dev làm tay: chạy `python scripts/dev/run_server.py` ở một terminal và `npm --prefix frontend run dev` ở terminal khác, rồi mở http://localhost:5173.

> ⚠️ `run_server.py` dùng `DATABASE_URL` trong `.env`. Xem dashboard thì an toàn, nhưng tick hoàn thành / thêm deadline sẽ **ghi thật** vào DB đó (và deadline mới sẽ được bot thông báo `@everyone` ở lần cron kế tiếp). Muốn thử an toàn, đặt `DATABASE_URL` của staging trước khi chạy: `$env:DATABASE_URL = "<url staging>"`.
>
> Thấy lỗi `http proxy error ... ECONNREFUSED` trong cửa sổ Vite nghĩa là backend (cổng 8000) chưa chạy.

**Kiểm tra trước khi commit:**
```bash
python -m pytest -m "not integration"   # test backend, không cần mạng / DB
npm --prefix frontend run build         # kiểm tra TypeScript + build frontend
python main.py --bogus                  # chỉ in usage, an toàn
```
> ⛔ Không chạy `python main.py` (không tham số) hay `--summary`, `--progress`, ... để "thử": các lệnh này gửi thông báo thật lên Discord.

Deploy không cần build tay: Vercel tự chạy `npm install && npm run build` trong `frontend/` mỗi lần push, GitHub Actions tự chạy `python main.py` theo lịch.
> Các script debug cần token thật (gọi Discord/Moodle thật) nằm ở `scripts/debug/`, chạy trực tiếp bằng `python scripts/debug/<file>.py`. Pytest không thu thập chúng.

## REST API (Vercel)

| Method | Route | Mô tả |
|---|---|---|
| `GET` | `/api/health` | Health check. |
| `GET` | `/api/courses` | Danh sách môn kèm số deadline. |
| `GET` | `/api/deadlines?course=<mã>` | Danh sách deadline (lọc theo môn). |
| `POST` | `/api/deadlines` | Thêm deadline thủ công từ Web (`mon`, `ten`, `han_chot`, `nguoi_phu_trach`, `ghi_chu_url`). |
| `POST` | `/api/deadlines/toggle` | Đánh dấu / bỏ đánh dấu hoàn thành (`deadlines_id`, `completed`). |
| `GET` | `/api/stats` | Thống kê cho Dashboard. |
| `GET` | `/api/announcements` | Thông báo môn học gần đây. |
| `POST` | `/api/interactions` | Webhook Slash Commands của Discord. |
| `POST` | `/api/add_deadline` | Thêm deadline từ bên thứ 3 (header `X-API-Key`). |

## Cơ sở dữ liệu

| Bảng | Nội dung chính |
|---|---|
| `courses` | Mã môn, tên hiển thị, ID khóa học Moodle, kênh Discord (`chat_id`), category học kỳ. |
| `deadlines` | Tên, hạn chót, nguồn (`moodle` / `manual`), cờ `notified_new` / `reminded_3d` / `reminded_1d` / `completed`, ID tin nhắn & sự kiện Discord. |
| `announcements` | Thông báo môn học. |
| `course_modules` | Tài liệu/bài tập/quiz đã biết trên Moodle (phát hiện nội dung mới). |
| `forum_discussions` | Bài đăng diễn đàn đã biết. |
| `notifications` | Nhật ký tin nhắn đã gửi. |
| `error_logs` | Nhật ký lỗi theo nguồn và mức độ. |

## Tài liệu thêm
- [docs/architecture/cau-truc-du-an.md](docs/architecture/cau-truc-du-an.md): cấu trúc dự án chi tiết.
- [docs/planning/roadmap.md](docs/planning/roadmap.md): hướng phát triển.
- [docs/architecture/technical-specification.md](docs/architecture/technical-specification.md): đặc tả kỹ thuật.
- [docs/architecture/frontend-architecture-and-workflow.md](docs/architecture/frontend-architecture-and-workflow.md): kiến trúc Web Dashboard.
- [docs/architecture/refactoring-blueprint.md](docs/architecture/refactoring-blueprint.md): kế hoạch tái cấu trúc thư mục.
- [docs/context-pack/](docs/context-pack/): bộ tài liệu tổng quan cho AI/người mới.

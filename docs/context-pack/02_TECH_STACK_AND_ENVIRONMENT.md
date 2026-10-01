# PHẦN 2: TECH STACK & MÔI TRƯỜNG RUNTIME

> **File:** `02_TECH_STACK_AND_ENVIRONMENT.md`  
> **Ngữ cảnh sử dụng:** Cung cấp chi tiết các công nghệ, thư viện, phiên bản và các biến môi trường cấu hình.

---

## 1. Tổng quan Tech Stack

Hệ thống sử dụng kiến trúc Polyglot hiện đại, phân tách rõ ràng giữa Web UI SPA và Backend Automation/Serverless:

```text
Frontend (SPA)              Backend (Python Core & Serverless)     Database & Cloud
├── React 18.3.1            ├── Python >= 3.10                     ├── PostgreSQL (Supabase)
├── TypeScript 5.7.3        ├── psycopg2-binary                    ├── Vercel (Edge CDN + Functions)
├── Vite 6.1.0              ├── requests                           └── GitHub Actions (Cron Runner)
└── Tailwind CSS 3.4.17     ├── pynacl
                            ├── google-api-python-client
                            └── python-dotenv
```

---

## 2. Chi tiết các thành phần & Phiên bản

### 2.1 Backend Core (Python)
Khai báo từ [`requirements.txt`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/requirements.txt) và [`pyproject.toml`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/pyproject.toml):

| Tên thư viện / Công cụ | Phiên bản khai báo | Vai trò kỹ thuật & Mục đích |
| :--- | :--- | :--- |
| **Python Runtime** | `>= 3.10` | Chạy trên runner `ubuntu-latest` (GitHub Actions: Python 3.10) và Vercel Python Serverless Runtime. |
| `psycopg2-binary` | Mới nhất / binary | Driver kết nối PostgreSQL, hỗ trợ `RealDictCursor` để trả kết quả truy vấn dạng dict. |
| `requests` | Mới nhất | Client HTTP đồng bộ cho toàn bộ kết nối ngoại vi (Discord API, Moodle API, Notion API). |
| `pynacl` | Mới nhất | Binding của libsodium, dùng để giải mã và xác thực chữ ký số **Ed25519** trong Discord Webhook. |
| `python-dotenv` | Mới nhất | Tự động đọc biến cấu hình từ `.env` trong môi trường phát triển nội bộ. |
| `google-auth` | `>= 2.0.0` | Thư viện xác thực tài khoản dịch vụ (Google Service Account credentials) cho Google Cloud. |
| `google-api-python-client` | `>= 2.0.0` | SDK tương tác với Google Calendar API v3 (`build('calendar', 'v3', ...)`). |

### 2.2 Frontend Web Dashboard (React + TypeScript)
Khai báo từ [`frontend/package.json`](file:///e:/coder/OnlyC%28ode%29/Notification%20Project/frontend/package.json):

| Package | Phiên bản | Vai trò kỹ thuật |
| :--- | :--- | :--- |
| `react` & `react-dom` | `^18.3.1` | Core UI Library xây dựng Single Page Application Dashboard. |
| `typescript` | `^5.7.3` | Type-safety toàn diện cho data contracts, state và API responses. |
| `vite` | `^6.1.0` | Build tool và dev server thế hệ mới với Hot Module Replacement cực nhanh. |
| `@vitejs/plugin-react` | `^4.3.4` | Plugin chính thức hỗ trợ JSX/TSX Fast Refresh. |
| `tailwindcss` | `^3.4.17` | Utility-first CSS framework thiết kế giao diện hiện đại, responsive. |
| `postcss` & `autoprefixer` | `^8.5.1` & `^10.4.20` | CSS pre-processing pipeline. |
| `clsx` & `tailwind-merge` | `^2.1.1` & `^2.6.0` | Ghép class và override class Tailwind động mà không xung đột. |
| `lucide-react` | `^0.475.0` | Bộ icon SVG hiện đại, tối ưu tree-shaking cho Dashboard. |

### 2.3 Cơ sở dữ liệu & Hạ tầng Đám mây
* **Database Engine:** PostgreSQL (phiên bản 15+ do **Supabase** quản lý).
* **Vercel Serverless Platform:**
  * Build command: `cd frontend && npm install && npm run build`
  * Output directory: `frontend/dist`
  * Rewrite rule: `/api/(.*) -> /api/index.py` (điều hướng toàn bộ API về gateway serverless).
* **GitHub Actions Runner:**
  * `cron: '*/30 * * * *'`: Quét deadline và thông báo Moodle mỗi 30 phút.
  * `cron: '25 23 * * *'`: Gửi báo cáo tổng hợp lúc 23:25 UTC (~06:45 - 07:00 AM giờ Việt Nam sau độ trễ hàng đợi).

---

## 3. Bảng biến môi trường (Environment Variables)

Hệ thống cấu hình qua biến môi trường (Secrets trên GitHub Actions và Vercel Environment Variables):

| Tên biến | Bắt buộc? | Mô tả & Mục đích |
| :--- | :---: | :--- |
| `MOODLE_CALENDAR_URL` | **Có** | Link iCalendar (ICS) xuất từ trang cá nhân Moodle FIT HCMUS. |
| `DISCORD_BOT_TOKEN` | **Có** | Token của Discord Bot để xác thực API calls. |
| `DISCORD_SERVER_ID` | **Có** | Guild ID của máy chủ Discord đích nơi bot gửi thông báo. |
| `DATABASE_URL` | **Có** | Chuỗi kết nối PostgreSQL (URI) của Supabase. |
| `DISCORD_PUBLIC_KEY` | Tùy chọn* | Public Key dùng xác thực Ed25519 cho Slash Commands (*bắt buộc trên Vercel). |
| `DISCORD_APPLICATION_ID` | Tùy chọn | App ID dùng khi chạy script đăng ký Slash Commands (`register_commands.py`). |
| `EXTERNAL_API_KEY` | Tùy chọn | API Key tĩnh dùng để bảo vệ endpoint `POST /api/add_deadline` từ Zapier/Google Form. |
| `MOODLE_TOKEN` | Tùy chọn | Web Service Token từ Moodle để crawl tài liệu và diễn đàn môn học. |
| `NOTION_API_TOKEN` | Tùy chọn | Integration Token để kết nối Notion API. |
| `NOTION_DATABASE_ID` | Tùy chọn | ID của bảng Notion Database dùng lưu trữ Todo List. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Tùy chọn | Nội dung JSON (hoặc Base64) của Service Account Key Google Cloud. |
| `GOOGLE_CALENDAR_ID` | Tùy chọn | ID lịch Google nhận đồng bộ deadline (thường là email lịch chia sẻ). |

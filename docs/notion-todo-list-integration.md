# 📋 Tích hợp Notion Todo List — Kế hoạch & Tiến độ

> **Ngày bắt đầu:** 16/09/2026
> **Trạng thái:** 🟢 Bước 2-5 đã hoàn thành — Chờ Nguyên test local (Bước 6)

---

## Tổng quan

Thêm tính năng đồng bộ deadline từ Moodle lên Notion dưới dạng **Todo List Database**, cho phép xem và quản lý lịch deadline trực tiếp trên app Notion (điện thoại/máy tính). Bot sẽ tự động tạo, cập nhật và đánh dấu hoàn thành các task trên Notion đồng bộ với Discord.

**Luồng hoạt động:**
```
Moodle (ICS) ──► Bot (GitHub Actions) ──┬──► Discord (thông báo)
                                        └──► Notion (Todo List) ──► Xem trên điện thoại
```

---

## Theo dõi tiến độ

### Bước 1 — Nguyên chuẩn bị trên Notion 🧑 ✅
- [x] Tạo Notion Integration tại [notion.so/my-integrations](https://www.notion.so/my-integrations)
  - Name: `Course FIT Bot`
  - Capabilities: ✅ Read, ✅ Update, ✅ Insert
- [x] Copy **Internal Integration Secret** (`NOTION_TOKEN`)
- [x] Tạo trang mới trên Notion → Tạo Database (Table view)
- [x] Thiết lập 6 cột trong Database:
  - [x] `Tên deadline` — Title
  - [x] `Trạng thái` — Status (To-do / In Progress / Done)
  - [x] `Môn học` — Select
  - [x] `Hạn chót` — Date (bật Include time)
  - [x] `Link Moodle` — URL
  - [x] `Nguồn` — Select (Moodle, Discord)
- [x] Thêm View **Calendar** (Show calendar by → Hạn chót)
- [x] Kết nối Integration vào Database (dấu `···` → Add connections)
- [x] Lấy **Database ID** từ URL trang Notion
- [x] **Gửi cho mình: `NOTION_TOKEN` + `NOTION_DATABASE_ID`**

---

### Bước 2 — Cấu hình biến môi trường 🤖 ✅
- [x] Thêm `NOTION_TOKEN` và `NOTION_DATABASE_ID` vào `.env`
- [x] Cập nhật `src/config.py` — đọc 2 biến mới (optional)

---

### Bước 3 — Code module Notion 🤖 ✅
- [x] Tạo file mới `src/notion_sync.py`
  - [x] `__init__(token, database_id)` — Khởi tạo kết nối
  - [x] `find_page_by_lms_id(lms_id)` — Tìm task tránh trùng lặp
  - [x] `add_deadline(name, course, deadline, url, source)` — Thêm deadline mới
  - [x] `mark_completed(lms_id, completed_by)` — Đánh dấu Done
  - [x] `sync_all_deadlines(deadlines)` — Đồng bộ hàng loạt (lần đầu)
  - [x] Xử lý lỗi: retry, logging, không crash nếu Notion API lỗi

---

### Bước 4 — Tích hợp vào luồng chính 🤖 ✅
- [x] Sửa `src/app.py`
  - [x] Import `NotionSync`
  - [x] Khởi tạo `NotionSync` trong `run_main_bot()` (nếu có token)
  - [x] Gọi `notion.add_deadline()` sau khi gửi Discord thành công
- [x] Sửa `src/event_tracker.py`
  - [x] Gọi `notion.mark_completed()` khi phát hiện user react ✅

---

### Bước 5 — Cập nhật dependencies & GitHub Actions 🤖 ✅
- [x] Cập nhật `requirements.txt` (thêm `python-dotenv`)
- [x] Cập nhật `.github/workflows/notify.yml`
  - [x] Thêm `NOTION_API_TOKEN` vào env secrets
  - [x] Thêm `NOTION_DATABASE_ID` vào env secrets

---

### Bước 6 — Test local 🧑
- [ ] Chạy `pip install -r requirements.txt`
- [ ] Chạy `python main.py` → kiểm tra log
- [ ] Mở Notion → xác nhận deadline xuất hiện trên bảng
- [ ] Kiểm tra Calendar View hiển thị đúng ngày
- [ ] React ✅ trên Discord → kiểm tra Notion chuyển sang Done

---

### Bước 7 — Deploy lên GitHub Actions 🧑
- [ ] Thêm secret `NOTION_TOKEN` trên GitHub (Settings → Secrets → Actions)
- [ ] Thêm secret `NOTION_DATABASE_ID` trên GitHub
- [ ] Push code lên GitHub
- [ ] Chạy thử workflow (Actions → Run workflow → mode: notify)
- [ ] Kiểm tra Notion có cập nhật sau khi workflow chạy xong

---

### Bước 8 — Setup điện thoại 🧑
- [ ] Cài app Notion trên điện thoại
- [ ] Đăng nhập cùng tài khoản
- [ ] Mở trang Deadline Tracker → chuyển sang Calendar View
- [ ] Thêm Widget Notion ra màn hình chính (tùy chọn)

---

## Thiết kế Database Notion

| # | Tên cột | Kiểu | Ghi chú |
|---|---------|------|---------|
| 1 | `Tên deadline` | Title | Cột mặc định |
| 2 | `Trạng thái` | Status | To-do / In Progress / Done |
| 3 | `Môn học` | Select | Bot tự tạo options |
| 4 | `Hạn chót` | Date | Bật Include time |
| 5 | `Link Moodle` | URL | |
| 6 | `Nguồn` | Select | Moodle hoặc Discord |

## Các file thay đổi

| File | Hành động | Mô tả |
|------|-----------|-------|
| `src/notion_sync.py` | **TẠO MỚI** | Module giao tiếp Notion API |
| `src/config.py` | Sửa | Thêm đọc biến `NOTION_TOKEN`, `NOTION_DATABASE_ID` |
| `src/app.py` | Sửa | Gọi `notion.add_deadline()` khi có deadline mới |
| `src/event_tracker.py` | Sửa | Gọi `notion.mark_completed()` khi react ✅ |
| `.env` | Sửa | Thêm 2 biến môi trường |
| `requirements.txt` | Sửa | Thêm `python-dotenv` |
| `.github/workflows/notify.yml` | Sửa | Thêm 2 secrets |

---

## Ký hiệu

| Ký hiệu | Ý nghĩa |
|----------|---------|
| 🧑 | Nguyên thực hiện |
| 🤖 | Bot code |
| `[ ]` | Chưa làm |
| `[/]` | Đang làm |
| `[x]` | Hoàn thành |

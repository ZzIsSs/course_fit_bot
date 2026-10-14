# 📱 Kế Hoạch & Sổ Tay Vận Hành Máy Trạm Bot Trên Điện Thoại (Xiaomi 13T Pro — Dành Riêng Cho Nguyên)

> **Dự án:** HCMUS Course FIT Notification Bot  
> **Repository:** `https://github.com/ZzIsSs/course_fit_bot.git`  
> **Thiết bị vận hành:** Xiaomi 13T Pro (Dimensity 9200+, UFS 4.0, 12GB RAM, Android 14 / HyperOS)  
> **Cập nhật mới nhất:** Tháng 10/2026 — Bổ sung module **Moodle REST API Crawler**, cơ chế **Auto-complete nộp bài**, trọn bộ **10 phím bấm Widget 1 chạm**, kịch bản cài đặt tự động `setup_termux.sh` và quy trình **Đồng bộ Git 1 chạm**.

---

## 🧭 1. KIẾN TRÚC MÁY TRẠM TRONG HỆ SINH THÁI DỰ ÁN

Hệ thống của Nguyên hiện tại vận hành theo mô hình kết hợp cực kỳ tối ưu:

```text
       ┌────────────────────────────────────────────────────────┐
       │                KHO DỮ LIỆU TRUNG TÂM                   │
       │           SUPABASE POSTGRESQL (CLOUD DB)               │
       └──────────────┬──────────────────────────┬──────────────┘
                      │ (Đọc / Ghi State)        │ (Đọc / Ghi State)
                      ▼                          ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│     ĐIỆN THOẠI XIAOMI 13T PRO   │   │       VERCEL SERVERLESS         │
│          (MÁY TRẠM TERMUX)      │   │       (WEB & WEBHOOKS)          │
├─────────────────────────────────┤   ├─────────────────────────────────┤
│ • Thay thế Cron GitHub Actions  │   │ • Web Dashboard React + Vite    │
│ • Quét iCalendar (.ics) định kỳ │   │ • Nhận Slash Commands Discord   │
│ • [MỚI] Moodle API Crawler      │   │   (/add_deadline, /deadline)    │
│ • [MỚI] Auto-complete nộp bài   │   │ • Nhận Webhook Google Forms     │
│ • Bắn tin Discord / Notion/GCal │   │ • Hoạt động 24/7 không cần mở   │
│ • 10 Widget điều khiển 1 chạm   │   │   port máy trạm ra ngoài        │
└─────────────────────────────────┘   └─────────────────────────────────┘
```

* **Điện thoại (Xiaomi 13T Pro):** Đóng vai trò là **Động cơ thực thi ngầm (Worker & Scheduler)**. Điện thoại chủ động kéo dữ liệu từ Moodle, kiểm tra hạn chót, đồng bộ Notion, Google Calendar và gửi thông báo Discord. Bạn có toàn quyền điều khiển bằng các nút bấm Widget ngoài màn hình chính.
* **Vercel:** Giữ cổng đón nhận lệnh người dùng 24/7 từ Discord và cung cấp Web Dashboard. Điện thoại không cần mở port (không cần port-forwarding hay DDNS), đảm bảo an toàn tuyệt đối.
* **Supabase:** Là nơi đồng bộ dữ liệu giữa Web Dashboard và Máy trạm điện thoại.

---

## 📑 MỤC LỤC TOÀN TẬP

1. [Bảng theo dõi tiến độ thực tế](#1-bảng-theo-dõi-tiến-độ-thực-tế)
2. [Chặng 1: Cài đặt môi trường từ A - Z & Sửa triệt để lỗi build](#2-chặng-1-cài-đặt-môi-trường-từ-a---z--sửa-triệt-để-lỗi-build)
3. [Chặng 2: Nạp cấu hình (.env) đầy đủ & Kích hoạt Moodle Token](#3-chặng-2-nạp-cấu-hình-env-đầy-đủ--kích-hoạt-moodle-token)
4. [Chặng 3: Giữ sống thiết bị trên HyperOS (Chống tắt ngầm)](#4-chặng-3-giữ-sống-thiết-bị-trên-hyperos-chống-tắt-ngầm)
5. [Chặng 4: Lịch chạy tự động thông minh (Tiết kiệm pin tối đa)](#5-chặng-4-lịch-chạy-tự-động-thông-minh-tiết-kiệm-pin-tối-đa)
6. [Chặng 5: Trọn bộ 10 nút bấm Widget 1 chạm & Script cài đặt 1 lệnh](#6-chặng-5-trọn-bộ-10-nút-bấm-widget-1-chạm--script-cài-đặt-1-lệnh)
7. [Chặng 6: Quy trình nâng cấp & Đồng bộ mã nguồn (Git Pull 1 chạm)](#7-chặng-6-quy-trình-nâng-cấp--đồng-bộ-mã-nguồn-git-pull-1-chạm)
8. [Chặng 7: Cơ chế khởi động lại máy & Quản lý Bật/Tắt linh hoạt](#8-chặng-7-cơ-chế-khởi-động-lại-máy--quản-lý-bậttắt-linh-hoạt)
9. [Chặng 8: Khối lệnh tự chẩn đoán lỗi hệ thống (Diagnostic Test 2.0)](#9-chặng-8-khối-lệnh-tự-chẩn-đoán-lỗi-hệ-thống-diagnostic-test-20)
10. [Bảng tra cứu lệnh nhanh toàn tập](#10-bảng-tra-cứu-lệnh-nhanh-toàn-tập)

---

## 1. BẢNG THEO DÕI TIẾN ĐỘ THỰC TẾ

* [x] **Chặng 1:** Cài đặt Termux, Python 3, PostgreSQL và build thành công `psycopg2`, `pynacl` trên kiến trúc ARM64 ➔ **HOÀN THÀNH 100%**.
* [x] **Chặng 2:** Nạp file cấu hình `.env`, kết nối Supabase, Discord Gateway ➔ **HOÀN THÀNH 100%**.
* [x] **Chặng nâng cấp mới:** Bổ sung `MOODLE_TOKEN` để mở khóa **Moodle REST API Crawler** và **Auto-complete nộp bài** ➔ **SẴN SÀNG**.
* [x] **Chặng 5 nâng cấp:** Nâng cấp từ 8 lên **10 nút bấm Widget 1 chạm** + Nút **Cập nhật Code Git** ➔ **SẴN SÀNG**.
* [ ] **Chặng 3 & 4:** Treo máy tự động 24/7 theo lịch Crontab (khi Nguyên muốn bot tự chạy thay GitHub Actions) ➔ *Tùy chọn: Bật khi cắm sạc qua đêm*.

---

## 2. CHẶNG 1: CÀI ĐẶT MÔI TRƯỜNG TỪ A - Z & SỬA TRIỆT ĐỂ LỖI BUILD

### 2.1. Nguồn cài đặt ứng dụng chuẩn (F-Droid)
* **Termux:** [https://f-droid.org/packages/com.termux/](https://f-droid.org/packages/com.termux/) *(Tuyệt đối không dùng bản Google Play Store)*.
* Cài thêm các tiện ích từ **cùng nguồn F-Droid** (đảm bảo trùng chữ ký bảo mật):
  - **Termux:Widget:** [https://f-droid.org/packages/com.termux.widget/](https://f-droid.org/packages/com.termux.widget/) *(Tạo nút bấm ra màn hình chính)*.
  - **Termux:API:** [https://f-droid.org/packages/com.termux.api/](https://f-droid.org/packages/com.termux.api/) *(Hiện thông báo Toast & Notification trên Android)*.
  - **Termux:Boot:** [https://f-droid.org/packages/com.termux.boot/](https://f-droid.org/packages/com.termux.boot/) *(Tự kích hoạt sau khi khởi động lại máy)*.

### 2.2. Cài gói hệ thống bắt buộc
Mở Termux và chạy dòng lệnh sau:
```bash
pkg update -y && pkg upgrade -y
pkg install -y git python clang make pkg-config libffi openssl libsodium libpq postgresql python-cryptography cronie termux-api util-linux nano
```
*(Gói `postgresql` cung cấp `pg_config` bắt buộc để `psycopg2` biên dịch chuẩn xác trên chip MediaTek Dimensity 9200+).*

### 2.3. Tải mã nguồn Bot về máy trạm
```bash
cd ~
git clone https://github.com/ZzIsSs/course_fit_bot.git
cd course_fit_bot
```

### 2.4. Khởi tạo môi trường ảo Python & Cài đặt thư viện
```bash
python -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade pip
pip install psycopg2
SODIUM_INSTALL=system pip install -r requirements.txt
```

---

## 3. CHẶNG 2: NẠP CẤU HÌNH (.ENV) ĐẦY ĐỦ & KÍCH HOẠT MOODLE TOKEN

### 3.1. Điểm mới quan trọng: Biến `MOODLE_TOKEN`
Trước đây, bot chỉ đọc file `.ics` qua `MOODLE_CALENDAR_URL`. Nhược điểm lớn là:
1. Nhiều bài tập / Quiz giảng viên tạo ra nhưng **không add vào Calendar** $\rightarrow$ bot bị sót.
2. Giảng viên đổi hạn chót bài tập $\rightarrow$ Calendar không cập nhật kịp.
3. Sinh viên đã nộp bài rồi nhưng bot vẫn gửi thông báo nhắc nhở làm phiền.

> 🌟 **Khi có `MOODLE_TOKEN`:**  
> Bot gọi trực tiếp Moodle REST API: quét sạch toàn bộ Assignment (`mod_assign`) và Quiz (`mod_quiz`), tự động cập nhật hạn chót nếu giảng viên dời ngày, và đặc biệt là **tự động đánh dấu hoàn thành (Auto-complete)** ngay khi phát hiện bạn đã nộp bài!

### 3.2. Cấu hình file `.env` trên máy trạm
Tại thư mục `~/course_fit_bot`, gõ lệnh:
```bash
nano .env
```
Dán đầy đủ cấu hình theo mẫu dưới đây:
```ini
# --- BẮT BUỘC CHO BOT HOẠT ĐỘNG ---
DISCORD_BOT_TOKEN=MTA...
DISCORD_SERVER_ID=123456789...
MOODLE_CALENDAR_URL=https://courses.fit.hcmus.edu.vn/calendar/export_execute.php?...
DATABASE_URL=postgresql://postgres.xxx:yyy@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres

# --- [MỚI & KHUYÊN DÙNG] MỞ KHÓA TOÀN BỘ SỨC MẠNH CÀO MOODLE & AUTO-COMPLETE ---
MOODLE_TOKEN=abc123xyz...

# --- TÙY CHỌN: ĐỒNG BỘ TIỆN ÍCH NGOẠI VI ---
NOTION_API_TOKEN=secret_...
NOTION_DATABASE_ID=...
GOOGLE_CALENDAR_ID=...@group.calendar.google.com
GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}
```
* Bấm **`CTRL` + `O`** rồi nhấn **`Enter`** để Lưu.
* Bấm **`CTRL` + `X`** để Thoát.
* Phân quyền an toàn: `chmod 600 .env`

### 3.3. Chạy thử nghiệm các tính năng mới
```bash
# 1. Chạy thử bộ cào Moodle REST API & kiểm tra auto-complete nộp bài
python main.py --crawl-deadlines

# 2. Chạy thử báo cáo tiến độ
python main.py --progress
```

---

## 4. CHẶNG 3: GIỮ SỐNG THIẾT BỊ TRÊN HYPEROS (CHỐNG TẮT NGẦM)

Xiaomi HyperOS có trình quản lý pin nghiêm ngặt. Để máy trạm chạy bền bỉ 24/7, Nguyên cần làm các bước sau một lần duy nhất:

### 4.1. Cấu hình quyền ứng dụng Termux & Termux:Widget
Vào **Cài đặt (Settings)** ➔ **Ứng dụng (Apps)** ➔ **Quản lý ứng dụng (Manage apps)** ➔ Tìm **Termux** (và làm tương tự cho **Termux:Widget**):
* **Tự khởi chạy (Autostart):** Bật **XANH**.
* **Quyền khác (Other permissions):**
  - ✅ Bật xanh: **Hiển thị cửa sổ pop-up khi chạy dưới nền** *(Bắt buộc)*.
  - ✅ Bật xanh: **Hiển thị trên màn hình khóa**.
* **Tiết kiệm pin (Battery saver):** Chọn **Không hạn chế (No restrictions)**.

### 4.2. Khóa ứng dụng trong màn hình Đa nhiệm (Recent Apps)
* Vuốt mở màn hình các ứng dụng gần đây ➔ Nhấn giữ cửa sổ Termux ➔ Bấm vào **biểu tượng ổ khóa** để hệ thống không giải phóng RAM của Termux.

### 4.3. Bật chế độ chống ngủ sâu CPU (Wake-lock)
Trong Termux, chạy lệnh:
```bash
termux-wake-lock
```
*(Trên thanh thông báo sẽ xuất hiện dòng thông báo giữ wake-lock của Termux).*

### 4.4. Tắt Phantom Process Killer (Android 14 / HyperOS)
Vào **Cài đặt** ➔ **Cài đặt bổ sung** ➔ **Tùy chọn nhà phát triển (Developer options)** ➔ Cuộn xuống tìm mục:
👉 **Disable child process restrictions** (hoặc *Vô hiệu hóa giới hạn tiến trình con*) ➔ Bật **BẬT**.

---

## 5. CHẶNG 4: LỊCH CHẠY TỰ ĐỘNG THÔNG MINH (TIẾT KIỆM PIN TỐI ĐA)

Lịch chạy được thiết kế riêng theo thói quen học tập sinh viên:
* **Ban ngày (07h00 - 22h00):** Tự động quét **1 tiếng/lần** (đủ nhanh để bắt bài tập mới, quiz mở và tự đổi trạng thái khi vừa nộp bài).
* **Đúng 06:55 sáng:** Tự động gửi tin nhắn tổng kết ngày mới (`--summary`).
* **Ban đêm (23h00 - 06h00):** Tạm dừng quét hoàn toàn để máy nghỉ, CPU ngủ sâu, tiêu thụ 0% pin.

### Cài đặt Crontab
Mở Termux và dán lệnh sau:
```bash
crontab - <<'EOF'
SHELL=/data/data/com.termux/files/usr/bin/bash
PATH=/data/data/com.termux/files/usr/bin
CRON_TZ=Asia/Ho_Chi_Minh
TZ=Asia/Ho_Chi_Minh

# Ban ngày từ 7h đến 22h: Quét tự động mỗi 1 tiếng vào phút thứ 00
0 7-22 * * * /data/data/com.termux/files/home/bot-bin/run.sh >/dev/null 2>&1

# 06:55 sáng hàng ngày: Gửi báo cáo tổng kết deadline hôm nay
55 6 * * * /data/data/com.termux/files/home/bot-bin/run.sh --summary >/dev/null 2>&1
EOF
crond
```

---

## 6. CHẶNG 5: TRỌN BỘ 10 NÚT BẤM WIDGET 1 CHẠM & SCRIPT CÀI ĐẶT 1 LỆNH

Nhằm giúp Nguyên không phải tự tay copy tạo từng file script phức tạp, dự án đã tích hợp sẵn script **`scripts/termux/setup_termux.sh`**.

### 6.1. Thiết lập tự động chỉ với 1 dòng lệnh duy nhất!
Tại Termux, Nguyên chỉ cần chạy:
```bash
cd ~/course_fit_bot
bash scripts/termux/setup_termux.sh
```
*Script sẽ tự động tạo thư mục, cấu hình quyền, sinh ra kịch bản `~/bot-bin/run.sh` tối ưu và cài đặt trọn bộ 10 phím bấm Widget!*

---

### 6.2. Danh mục 10 phím bấm Widget 1 chạm trên màn hình chính

| Thứ tự | Tên File Shortcut | Ý nghĩa hành động khi bấm | Lệnh chạy ngầm |
| :---: | :--- | :--- | :--- |
| **1** | `1_Quet_Toan_Dien.sh` | **Quét toàn diện:** Quét ICS + Moodle API, gửi thông báo Discord, tạo Scheduled Event, đồng bộ Notion & Google Calendar. | `run.sh` |
| **2** | `2_Cao_Moodle_API.sh` | **[MỚI] Cào Moodle API & Auto-complete:** Cào nhanh Assignment, Quiz và tự động tick hoàn thành bài tập vừa nộp. | `run.sh --crawl-deadlines` |
| **3** | `3_Bao_Cao_Tien_Do.sh` | **Báo cáo tiến độ:** Gửi biểu đồ phần trăm hoàn thành các môn học vào kênh Discord. | `run.sh --progress` |
| **4** | `4_Tong_Ket_Ngay.sh` | **Tổng kết ngày:** Gửi danh sách các bài tập còn hạn hoặc cần làm trong ngày. | `run.sh --summary` |
| **5** | `5_Quet_Thong_Bao_Moodle.sh` | **Quét thông báo môn học:** Quét slide bài giảng, file PDF mới upload và bài viết trên Diễn đàn môn học. | `run.sh --announcements` |
| **6** | `6_Dong_Bo_Mon_Kenh.sh` | **Đồng bộ môn & kênh:** Tạo tự động và chuẩn hóa tên kênh Discord theo mã môn học (vd: `#nmttnt-csc10014`). | `run.sh --sync-channels` |
| **7** | `7_Dong_Bo_Notion.sh` | **Đồng bộ Notion:** Đẩy toàn bộ deadline đang mở sang Database Notion Todo List. | `run.sh --sync-notion` |
| **8** | `8_Dong_Bo_Google_Cal.sh` | **Đồng bộ Google Calendar:** Đẩy sự kiện kèm 3 mốc chuông báo (24h, 3h, 30p) sang Google Calendar. | `run.sh --sync-gcal` |
| **9** | `9_Don_Dep_Tin_Nhan.sh` | **Dọn dẹp Discord:** Quét và xoá các tin nhắn thông báo trùng lặp hoặc tin rác của Bot. | `run.sh --dedup` |
| **10** | `10_Cap_Nhat_Code.sh` | **[MỚI] Đồng bộ Code từ GitHub:** Kéo mã nguồn mới nhất về máy trạm và tự nạp lại script. | `git pull origin main` |
| 📋 | `Xem_Log.sh` | **Xem Log trực tiếp:** Mở cửa sổ đọc 40 dòng log gần nhất để kiểm tra trạng thái chạy. | `tail -n 40 ~/logs/bot.log` |

---

### 6.3. Cách đưa các nút bấm ra màn hình chính trên Xiaomi HyperOS
1. Tại màn hình chính điện thoại, **nhấn giữ vào khoảng trống** ➔ Chọn **Tiện ích (Widgets)**.
2. Cuộn xuống dưới cùng của danh sách tiện ích Xiaomi ➔ Chọn **`Tiện ích ứng dụng`** (hoặc *Android Widgets*).
3. Tìm đến mục **`Termux:Widget`**:
   - Chọn **`Termux Shortcut`** và kéo ra màn hình chính ➔ Chọn nút tương ứng bạn muốn (ví dụ: `1_Quet_Toan_Dien`, `2_Cao_Moodle_API`, `10_Cap_Nhat_Code`...).
   - Hoặc kéo widget **`Termux:Widget (Thư mục)`** để gom toàn bộ 10 nút vào một ô duy nhất cực kỳ gọn gàng!

---

## 7. CHẶNG 6: QUY TRÌNH NÂNG CẤP & ĐỒNG BỘ MÃ NGUỒN (GIT PULL 1 CHẠM)

Khi Nguyên code tính năng mới hoặc chỉnh sửa mã nguồn trên máy tính (Laptop/PC) và push lên GitHub:

### 👉 Cách cập nhật lên máy trạm điện thoại:
* **Cách 1 (Nhanh nhất — 1 Chạm):** Bấm trực tiếp vào nút Widget **`10_Cap_Nhat_Code`** ngoài màn hình chính. Máy sẽ hiện thông báo Toast:
  - ⏳ *Đang cập nhật code từ GitHub...*
  - ✅ *Đã cập nhật code mới nhất thành công!*
* **Cách 2 (Bằng dòng lệnh Termux):**
  ```bash
  cd ~/course_fit_bot
  git pull origin main
  bash scripts/termux/setup_termux.sh
  ```

> 🔒 **Lưu ý an toàn:**  
> Lệnh `git pull` hoàn toàn **KHÔNG LÀM MẤT** file `.env`, file log hay môi trường ảo `venv` của bạn vì các file này đã được liệt kê trong `.gitignore`.

---

## 8. CHẶNG 7: CƠ CHẾ KHỞI ĐỘNG LẠI MÁY & QUẢN LÝ BẬT/TẮT LINH HOẠT

### 8.1. Khi điện thoại khởi động lại (Reboot)
1. Do cơ chế mã hóa bộ nhớ dựa trên tệp (File-Based Encryption - FBE) của Android, sau khi máy khởi động lại, Nguyên chỉ cần **Mở khóa màn hình lần đầu tiên bằng mã PIN/Vân tay**.
2. Sau khi đã mở khóa: Nguyên có thể **bấm thẳng vào các nút Widget ngoài màn hình** để chạy bot ngay lập tức mà **KHÔNG CẦN mở app Termux lên**!

### 8.2. Cách BẬT / TẮT máy trạm linh hoạt

* **🟢 Khi ở nhà (Bật chế độ máy trạm tự động):**
  Cắm sạc điện thoại, mở Termux gõ:
  ```bash
  termux-wake-lock
  crond
  ```
  *(Bot sẽ tự động thức dậy chạy định kỳ theo lịch Crontab).*

* **🔴 Khi mang máy ra ngoài / Đi học (Tắt máy trạm để tiết kiệm 100% pin):**
  Mở Termux gõ:
  ```bash
  pkill crond
  termux-wake-unlock
  ```
  *(Hoặc vuốt thanh thông báo xuống ➔ bấm nút **`Exit`** ở thông báo Termux).*

### 8.3. Xử lý xung đột với GitHub Actions
* Khi máy trạm trên điện thoại đã hoạt động ổn định và bạn muốn điện thoại gánh tải hoàn toàn:
  - Vào repository GitHub ➔ Mở file `.github/workflows/notify.yml` ➔ Comment hoặc xóa khối `schedule:` đi, chỉ giữ lại `workflow_dispatch:`.
  - Việc này giúp tiết kiệm 100% hạn mức 2,000 phút/tháng của GitHub Actions và tránh gửi thông báo trùng lặp.
* Khi bạn đi xa hoặc không muốn treo máy trạm: Bật lại `schedule:` trong GitHub Actions để mây gánh thay.

---

## 9. CHẶNG 8: KHỐI LỆNH TỰ CHẨN ĐOÁN LỖI HỆ THỐNG (DIAGNOSTIC TEST 2.0)

Bất cứ lúc nào nghi ngờ máy trạm chạy không đúng hoặc gặp sự cố, Nguyên chỉ cần mở Termux dán nguyên khối lệnh kiểm tra tự động dưới đây:

```bash
echo "=========================================================="
echo "🔍 BỘ CHẨN ĐOÁN TOÀN DIỆN MÁY TRẠM TERMUX (XIAOMI 13T PRO)"
echo "=========================================================="

# 1. Kiểm tra mã nguồn và .env
[ -d "$HOME/course_fit_bot" ] && echo "✅ 1. Thư mục mã nguồn: ĐÃ CÓ" || echo "❌ 1. Mã nguồn: CHƯA CÓ"
[ -f "$HOME/course_fit_bot/.env" ] && echo "✅ 2. File cấu hình .env: ĐÃ TỒN TẠI" || echo "❌ 2. File .env: THIẾU"

# 2. Kiểm tra MOODLE_TOKEN
if grep -q "MOODLE_TOKEN" "$HOME/course_fit_bot/.env" 2>/dev/null; then
    echo "✅ 3. Token Moodle REST API: ĐÃ CẤU HÌNH (Sẵn sàng cào & Auto-complete)"
else
    echo "⚠️ 3. Token Moodle: CHƯA CÓ TRONG .ENV (Chỉ quét được lịch .ics cơ bản)"
fi

# 3. Kiểm tra môi trường venv & run.sh
[ -f "$HOME/course_fit_bot/venv/bin/activate" ] && echo "✅ 4. Môi trường Python venv: SẴN SÀNG" || echo "❌ 4. venv: CHƯA CÓ"
[ -x "$HOME/bot-bin/run.sh" ] && echo "✅ 5. Kịch bản run.sh: SẴN SÀNG" || echo "❌ 5. run.sh: THIẾU HOẶC CHƯA CẤP QUYỀN"

# 4. Kiểm tra số lượng Widget
WIDGET_COUNT=$(ls -1 $HOME/.shortcuts/tasks/*.sh 2>/dev/null | wc -l)
echo "✅ 6. Số nút Widget khả dụng: $WIDGET_COUNT / 10 nút"

# 5. Kiểm tra tiến trình cron ngầm
if pgrep crond >/dev/null; then
    echo "✅ 7. Daemon Crontab: ĐANG CHẠY NGẦM (PID: $(pgrep crond))"
else
    echo "ℹ️ 7. Daemon Crontab: ĐANG TẮT (Chế độ chạy thủ công qua Widget)"
fi

# 6. Kiểm tra kết nối Internet
if curl -fsS -m 5 -o /dev/null https://discord.com/api/v10/gateway; then
    echo "✅ 8. Kết nối Discord Gateway: THÔNG SUỐT"
else
    echo "❌ 8. Kết nối mạng: KHÔNG THỂ KẾT NỐI DISCORD"
fi

echo "=========================================================="
echo "🎯 KẾT THÚC CHẨN ĐOÁN. NẾU TẤT CẢ XANH, HỆ THỐNG HOÀN HẢO!"
echo "=========================================================="
```

---

## 10. BẢNG TRA CỨU LỆNH NHANH TOÀN TẬP

| Thao tác muốn thực hiện | Lệnh trong Termux |
| :--- | :--- |
| **Vào thư mục bot** | `cd ~/course_fit_bot` |
| **Kích hoạt môi trường ảo** | `source venv/bin/activate` |
| **Cài đặt / Tái tạo toàn bộ Widget tự động** | `bash scripts/termux/setup_termux.sh` |
| **Cập nhật code từ GitHub** | `git pull origin main` |
| **Chạy cào Moodle REST API & Auto-complete** | `python main.py --crawl-deadlines` |
| **Quét toàn diện & gửi thông báo** | `~/bot-bin/run.sh` |
| **Gửi báo cáo tiến độ** | `~/bot-bin/run.sh --progress` |
| **Gửi tổng kết deadline ngày** | `~/bot-bin/run.sh --summary` |
| **Quét slide / tài liệu / diễn đàn Moodle** | `~/bot-bin/run.sh --announcements` |
| **Đồng bộ môn học & tạo kênh Discord** | `~/bot-bin/run.sh --sync-channels` |
| **Đồng bộ Notion Todo List** | `~/bot-bin/run.sh --sync-notion` |
| **Đồng bộ Google Calendar** | `~/bot-bin/run.sh --sync-gcal` |
| **Dọn dẹp tin nhắn trùng lặp** | `~/bot-bin/run.sh --dedup` |
| **Xem 40 dòng log gần nhất** | `tail -n 40 ~/logs/bot.log` |
| **Theo dõi log trực tiếp theo thời gian thực** | `tail -f ~/logs/bot.log` |
| **Bật chạy ngầm tự động** | `termux-wake-lock && crond` |
| **Tắt chạy ngầm hoàn toàn** | `pkill crond && termux-wake-unlock` |
| **Chạy chẩn đoán hệ thống tự động** | Dán khối lệnh ở **Mục 9** vào Termux |

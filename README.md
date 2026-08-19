# Course FIT HCMUS - Discord Notification Bot

Dự án này là một Bot Discord tự động đồng bộ các sự kiện, deadline bài tập và thông báo từ hệ thống Moodle (courses.fit.hcmus.edu.vn) sang Server Discord của bạn.

## Tính năng nổi bật
- **Đồng bộ Lịch & Deadline:** Tự động lấy các sự kiện, bài tập sắp tới từ file iCalendar (.ics) của Moodle.
- **Tạo Sự kiện (Scheduled Events):** Bot giao tiếp trực tiếp với API Discord để tự động tạo các Sự Kiện trên Server. Sinh viên có thể bấm "Tham gia" để nhận nhắc nhở.
- **Đồng bộ Thông báo môn học:** Gọi Moodle API để lấy các thông báo mới nhất từ diễn đàn môn học của giảng viên (yêu cầu thiết lập `MOODLE_TOKEN`).
- **Báo cáo Tóm tắt (Summary & Progress):** Cung cấp các lệnh báo cáo tổng hợp tiến độ và các deadline trong ngày/tuần để tránh trôi tin nhắn.
- **Lưu trữ trạng thái bằng PostgreSQL:** Sử dụng Supabase PostgreSQL làm cơ sở dữ liệu để lưu trạng thái thông báo, theo dõi deadline và ghi log lỗi. Có sẵn cơ chế chống spam và chống gửi thông báo lặp lại.
- **Tối ưu hóa Serverless:** Thiết kế gọn nhẹ (không phụ thuộc vào các thư viện bot nặng nề) để chạy tự động 24/7 miễn phí trên GitHub Actions.

## Hướng dẫn cài đặt và chạy tự động (GitHub Actions)

### Bước 1: Chuẩn bị Database (Supabase)
1. Đăng ký tài khoản miễn phí tại [Supabase](https://supabase.com).
2. Tạo một Project mới. Sau khi tạo xong, vào **Settings** → **Database** → sao chép **Connection string (URI)**.
3. Mở **SQL Editor** trên Supabase, dán nội dung file `migrations/001_create_database.sql` vào và bấm **Run** để tạo các bảng.

### Bước 2: Chuẩn bị thông tin (Tokens & IDs)
1. **`DISCORD_BOT_TOKEN`**: Tạo một ứng dụng Bot trên [Discord Developer Portal](https://discord.com/developers/applications), lấy Token. Đảm bảo bot đã được mời vào Server Discord với đủ quyền (Tạo Channel, Quản lý Event, Gửi tin nhắn).
2. **`DISCORD_SERVER_ID`**: ID của Server Discord (bật Developer Mode, chuột phải vào tên Server → Copy Server ID).
3. **`MOODLE_CALENDAR_URL`**: Đăng nhập Moodle → Lịch (Calendar) → Xuất lịch (Export Calendar) → Sao chép URL lịch (.ics).
4. **`MOODLE_TOKEN`** *(Tuỳ chọn)*: Token Moodle để đọc thông báo diễn đàn môn học.
5. **`DATABASE_URL`**: Connection string từ Supabase ở Bước 1.

### Bước 3: Tạo Repository trên GitHub
1. Tạo Repository mới trên GitHub. **Phải đặt chế độ Private** để bảo mật.
2. Tải toàn bộ mã nguồn lên Repository. Đảm bảo thư mục ẩn `.github/workflows` đã được đưa lên đầy đủ.

### Bước 4: Cấu hình GitHub Secrets
1. Trong Repository, vào tab **Settings** → **Secrets and variables** → **Actions**.
2. Bấm **New repository secret** và lần lượt thêm các biến:
   - `DISCORD_BOT_TOKEN`
   - `DISCORD_SERVER_ID`
   - `MOODLE_CALENDAR_URL`
   - `DATABASE_URL`
   - `MOODLE_TOKEN` *(nếu có)*

### Bước 5: Chạy thử (Manual Test)
1. Chuyển sang tab **Actions** trên giao diện Repo GitHub.
2. Bấm vào tên workflow **Notification Bot** ở menu bên trái.
3. Bấm nút **Run workflow** để chạy thử lần đầu.
4. Kiểm tra bên Server Discord xem Bot đã tạo Event hoặc gửi thông báo chưa. Từ nay, Bot sẽ tự động chạy ngầm mỗi 30 phút.

---

## Dành cho lập trình viên (Local Development)

1. Cài đặt Python và các thư viện:
   ```bash
   pip install -r requirements.txt
   ```
2. Thiết lập các Biến Môi Trường cục bộ (tương tự Bước 2 + `DATABASE_URL`).
3. Chạy migration SQL trên database:
   ```bash
   psql $DATABASE_URL -f migrations/001_create_database.sql
   ```
4. Chạy script:
   ```bash
   python main.py                  # Cập nhật deadline + thông báo mới
   python main.py --summary        # Gửi báo cáo tóm tắt
   python main.py --progress       # Gửi báo cáo tiến độ
   python main.py --announcements  # Kiểm tra thông báo Moodle
   ```

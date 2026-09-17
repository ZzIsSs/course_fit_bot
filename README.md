# Course FIT HCMUS - Discord Notification Bot

Dự án này là một Bot Discord tự động đồng bộ các sự kiện, deadline bài tập, tài liệu môn học và thông báo từ hệ thống Moodle (courses.fit.hcmus.edu.vn) sang Server Discord của bạn. 

Điểm đặc biệt của bot là kiến trúc **100% Serverless**, sử dụng trực tiếp Discord REST API thay vì các thư viện nặng (như `discord.py`), giúp bot có thể chạy ngầm hoàn toàn miễn phí qua GitHub Actions mà không cần thuê server 24/7.

## Tính năng nổi bật
- **Quản lý Kênh & Học kỳ tự động:** Tự động lấy danh sách môn học từ Moodle, bóc tách tên tiếng Việt và mã môn để tạo các kênh Discord theo format chuẩn (vd: `#nmttnt-csc10014`). Tự động tính toán để phân loại môn học vào đúng Category của từng Học kỳ.
- **Theo dõi toàn diện Moodle:** Không chỉ lấy thông báo diễn đàn, bot quét toàn bộ khóa học để phát hiện ngay lập tức khi giảng viên upload tài liệu (PDF, Slide), Folder, URL, hoặc bài Quiz mới.
- **Tương tác "Hoàn thành" qua Emoji:** Sinh viên chỉ cần thả cảm xúc (react) dấu `✅` vào tin nhắn nhắc deadline. Bot sẽ tự động ghi nhận deadline đã hoàn thành và điểm danh người thực hiện trên bảng báo cáo tiến độ.
- **Đồng bộ Lịch & Deadline:** Tự động lấy các sự kiện, bài tập sắp tới từ file iCalendar (.ics) của Moodle. Có chuỗi nhắc nhở thông minh: Mới tạo, Nhắc nhở (Còn 3 ngày), và Khẩn cấp (<24 giờ).
- **Tạo Sự kiện (Scheduled Events):** Giao tiếp trực tiếp với Discord API để tự động tạo Scheduled Events.
- **Báo cáo Tiến độ (Summary & Progress):** Tự động gửi báo cáo tổng hợp tiến độ (kèm thanh Progress Bar) và các deadline vào 7:00 sáng mỗi ngày.
- **Hỗ trợ Deadline thủ công (Backend):** Backend đã tích hợp sẵn cơ chế gộp các deadline nội bộ tự tạo vào chung luồng xử lý và nhắc nhở với Moodle.
- **Đồng bộ Google Calendar & Notion:** Tự động đồng bộ các deadline lên Google Calendar (kèm chuông thông báo 24h, 3h, 30p trên điện thoại) và Notion Todo List. Tự động chuyển màu xanh lá và đánh dấu `[XONG]` khi react `✅`.
- **Cơ chế lưu trạng thái chống Spam:** Sử dụng Supabase PostgreSQL làm cơ sở dữ liệu để lưu thời gian update (`timemodified`), tracking thông báo và chặn tuyệt đối việc gửi tin lặp lại.

## Hướng dẫn cài đặt và chạy tự động (GitHub Actions)

### Bước 1: Chuẩn bị Database (Supabase)
1. Đăng ký tài khoản miễn phí tại [Supabase](https://supabase.com).
2. Tạo một Project mới. Sau khi tạo xong, vào **Settings** → **Database** → sao chép **Connection string (URI)**.
3. Mở **SQL Editor** trên Supabase, dán nội dung file `migrations/001_create_database.sql` vào và bấm **Run** để tạo các bảng.

### Bước 2: Chuẩn bị thông tin (Tokens & IDs)
1. **`DISCORD_BOT_TOKEN`**: Tạo một ứng dụng Bot trên [Discord Developer Portal](https://discord.com/developers/applications), lấy Token. Đảm bảo bot đã được mời vào Server Discord với đủ quyền (Tạo Channel, Quản lý Event, Gửi tin nhắn).
2. **`DISCORD_SERVER_ID`**: ID của Server Discord (bật Developer Mode, chuột phải vào tên Server → Copy Server ID).
3. **`MOODLE_CALENDAR_URL`**: Đăng nhập Moodle → Lịch (Calendar) → Xuất lịch (Export Calendar) → Sao chép URL lịch (.ics).
4. **`MOODLE_TOKEN`** *(Tuỳ chọn nhưng khuyên dùng)*: Token Moodle để quét tài liệu khóa học và thông báo diễn đàn.
5. **`DATABASE_URL`**: Connection string từ Supabase ở Bước 1.
6. **Google Calendar** *(Tuỳ chọn - xem hướng dẫn chi tiết tại [docs/google-calendar-integration.md](docs/google-calendar-integration.md))*:
   - `GOOGLE_SERVICE_ACCOUNT_JSON`: Chuỗi JSON của Service Account Key.
   - `GOOGLE_CALENDAR_ID`: ID của lịch Google cần đồng bộ.

### Bước 3: Tạo Repository trên GitHub
1. Tạo Repository mới trên GitHub. **Phải đặt chế độ Private** để bảo mật các URL và Token.
2. Tải toàn bộ mã nguồn lên Repository. Đảm bảo thư mục ẩn `.github/workflows` đã được đưa lên đầy đủ.

### Bước 4: Cấu hình GitHub Secrets
1. Trong Repository, vào tab **Settings** → **Secrets and variables** → **Actions**.
2. Bấm **New repository secret** và lần lượt thêm các biến:
   - `DISCORD_BOT_TOKEN`
   - `DISCORD_SERVER_ID`
   - `MOODLE_CALENDAR_URL`
   - `DATABASE_URL`
   - `MOODLE_TOKEN` *(nếu có)*
   - `GOOGLE_SERVICE_ACCOUNT_JSON` *(nếu dùng Google Calendar)*
   - `GOOGLE_CALENDAR_ID` *(nếu dùng Google Calendar)*

### Bước 5: Chạy thử (Manual Test)
1. Chuyển sang tab **Actions** trên giao diện Repo GitHub.
2. Bấm vào tên workflow **Notification Bot** ở menu bên trái.
3. Bấm nút **Run workflow** để chạy thử lần đầu (có thể chọn các chế độ chạy như `--sync-channels` để tạo kênh Discord tự động, hoặc `--sync-gcal` để đồng bộ lịch Google).
4. Kiểm tra bên Server Discord và Google Calendar xem Bot đã tạo Event, tạo kênh hoặc gửi thông báo chưa. Từ nay, Bot sẽ tự động chạy ngầm mỗi 30 phút.

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
4. Chạy script thủ công:
   ```bash
   python main.py                  # Cập nhật deadline + thông báo Moodle mới
   python main.py --summary        # Gửi báo cáo tóm tắt deadline hằng ngày
   python main.py --progress       # Gửi báo cáo tiến độ chi tiết
   python main.py --announcements  # Chỉ kiểm tra tài liệu và diễn đàn Moodle
   python main.py --sync-channels  # Tự động tạo và làm chuẩn tên kênh Discord từ Moodle
   python main.py --sync-notion    # Đồng bộ toàn bộ deadline lên Notion Todo List
   python main.py --sync-gcal      # Đồng bộ toàn bộ deadline lên Google Calendar
   ```


# Prompt: Xây dựng công cụ thông báo deadline course.fit qua Telegram

Copy toàn bộ nội dung bên dưới và đưa cho AI coding agent (Antigravity, Claude Code, v.v.) để bắt đầu xây dựng.

---

## Prompt

Tôi cần xây dựng một công cụ tự động theo dõi trang web **course.fit** (trang thông tin khóa học của khoa tôi) và gửi thông báo qua **Telegram** khi có thông tin mới, vì hệ thống thông báo mặc định của Moodle bị lỗi.

### Yêu cầu chức năng
1. Viết một **script Python** thực hiện:
   - Đăng nhập vào course.fit bằng tài khoản sinh viên (username/password lấy từ biến môi trường / GitHub Secrets, không hardcode).
   - Truy cập và lấy dữ liệu từ các trang chứa: deadline bài tập, thông báo tài liệu mới, comment của giảng viên.
   - Lưu trạng thái đã xử lý (ví dụ danh sách ID/hash của các mục đã thông báo) vào một file JSON trong repo, để lần chạy sau so sánh và chỉ báo phần **mới**.
   - Nếu phát hiện mục mới → gửi tin nhắn qua Telegram Bot API tới một `chat_id` cụ thể.
2. Thiết lập **GitHub Actions workflow**:
   - Chạy script theo lịch (cron), ví dụ mỗi 30–60 phút.
   - Đọc secrets: `COURSE_FIT_USERNAME`, `COURSE_FIT_PASSWORD`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
   - Sau khi script chạy xong, **commit lại file trạng thái JSON** vào repo (để giữ lịch sử giữa các lần chạy) nếu có thay đổi.
3. Xử lý lỗi:
   - Nếu đăng nhập thất bại hoặc trang web đổi cấu trúc (không tìm thấy phần tử mong đợi) → gửi luôn 1 tin nhắn Telegram cảnh báo lỗi, để tôi biết cần kiểm tra lại thay vì im lặng không thông báo gì.
   - Thêm log rõ ràng (in ra console) để dễ debug qua GitHub Actions logs.

### Thông tin kỹ thuật cần tôi cung cấp thêm (hỏi tôi nếu chưa có)
- URL trang đăng nhập course.fit và URL trang deadline/thông báo/comment.
- Cấu trúc HTML của các trang đó (tôi sẽ cung cấp hoặc bạn có thể tự kiểm tra nếu truy cập được).
- Bot Telegram: tôi sẽ tạo qua @BotFather và cung cấp bot token.
- Chat ID Telegram của tôi (hướng dẫn tôi cách lấy nếu tôi chưa biết).

### Kết quả mong muốn
- Một repo GitHub hoàn chỉnh gồm: script Python, file requirements, workflow GitHub Actions (`.github/workflows/...yml`), và file README hướng dẫn cách thiết lập secrets + chạy thử.
- Không cần giao diện web, chỉ cần chạy nền và gửi thông báo qua Telegram.

---

## Ghi chú khi dùng prompt này
- Nếu agent hỏi thêm chi tiết về cấu trúc trang course.fit, hãy cung cấp URL hoặc chụp màn hình/HTML mẫu.
- Giữ bí mật bot token và mật khẩu — không dán trực tiếp vào code, luôn dùng biến môi trường / GitHub Secrets.

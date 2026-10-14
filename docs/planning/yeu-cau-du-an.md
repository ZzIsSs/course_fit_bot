# Yêu cầu dự án: Công cụ thông báo deadline course.fit

## 1. Bối cảnh / Vấn đề
- Nguyên hay bị **miss thông tin** từ trang **course.fit** của khoa (deadline, thông báo tài liệu, comment của thầy cô).
- Hệ thống thông báo của **Moodle bị lỗi**, không đáng tin cậy.
- Nguyên muốn có **1 công cụ riêng** để theo dõi trang course.fit và **thông báo kịp thời** khi có thông tin mới.

## 2. Yêu cầu chức năng
- Theo dõi (crawl/scrape) trang course.fit để phát hiện:
  - Deadline mới
  - Thông báo tài liệu mới
  - Comment mới của thầy/cô
- **So sánh với lần kiểm tra trước đó** để chỉ báo những gì **mới** (tránh spam lại thông tin cũ).
- Gửi thông báo ngay khi phát hiện thay đổi.

## 3. Kênh nhận thông báo
- **Telegram bot** — nhận trực tiếp trên điện thoại như push notification.
- Cần tạo bot qua **@BotFather** trên Telegram (`/newbot`) để lấy **bot token**.
- Cần lấy **chat_id** của Nguyên để bot biết gửi tin cho ai.

## 4. Đăng nhập / Xác thực
- Trang course.fit **cần đăng nhập** bằng tài khoản sinh viên mới xem được deadline/thông báo.
- Thông tin đăng nhập (username/password) sẽ được lưu dưới dạng **secret mã hoá** trên nền tảng chạy tự động (không public, không hiện ra ngoài).

## 5. Nơi chạy công cụ
- Chạy **tự động trên cloud miễn phí**, không cần bật máy tính cá nhân.
- Đề xuất: **GitHub Actions** (free tier) — chạy script theo lịch (ví dụ mỗi 30–60 phút).

## 6. Kiến trúc dự kiến
1. **Script Python**:
   - Đăng nhập vào course.fit bằng tài khoản sinh viên.
   - Lấy danh sách deadline / thông báo / comment mới nhất.
   - So sánh với trạng thái đã lưu từ lần chạy trước (file trạng thái/JSON, hoặc lưu trong repo).
   - Nếu có gì mới → gửi tin nhắn qua Telegram bot.
2. **GitHub Actions**:
   - Chạy script theo lịch (cron) định kỳ.
   - Lưu secrets: tài khoản course.fit, Telegram bot token, chat_id.

## 7. Thông tin còn thiếu / cần bổ sung
- [ ] URL cụ thể của trang course.fit (trang login + trang xem deadline/thông báo).
- [ ] Cấu trúc trang (form đăng nhập, HTML chứa deadline) — cần xem để viết logic scraping chính xác.
- [ ] Bot token Telegram (tạo qua @BotFather).
- [ ] Chat ID Telegram của Nguyên.

## 8. Công cụ hỗ trợ được nhắc đến
- Nguyên có thể dùng **Google Antigravity 2.0** (IDE agent-first, hỗ trợ cả model Claude) để tự code/test script trên máy trước khi deploy lên GitHub Actions.
- Hoặc có thể nhờ Claude viết trực tiếp script trong chat.

# 🚀 Gợi ý Hướng Phát Triển (Roadmap) cho Course FIT HCMUS Bot

Dưới đây là một số ý tưởng và hướng phát triển để nâng cấp bot trở nên mạnh mẽ, tiện dụng và hỗ trợ học tập nhóm hiệu quả hơn:

## 1. Nâng cấp trải nghiệm tương tác trực tiếp (Slash Commands)
Hiện tại bot đang hoạt động theo cơ chế một chiều (chạy ngầm định kỳ và gửi thông báo). Có thể nâng cấp thành bot tương tác 2 chiều:
- **Tích hợp Slash Commands (`/`)**: Cho phép người dùng gọi bot bất cứ lúc nào.
  - `/deadline`: Liệt kê ngay lập tức các bài tập và hạn chót sắp tới.
  - `/progress`: Xem biểu đồ tiến độ thay vì chờ đến lịch báo cáo tự động.
  - `/sync_now`: Ép bot quét Moodle ngay lập tức.
- *Cách triển khai:* Sử dụng kiến trúc Webhook (nhận sự kiện từ Discord API) và deploy miễn phí trên Vercel, Render hoặc Cloudflare Workers để vẫn giữ được tính chất "Serverless".

## 2. Quản lý Deadline nội bộ (Custom Deadlines)
Moodle chỉ cung cấp deadline của môn học, nhưng khi làm việc nhóm, sinh viên thường có các mốc thời gian riêng.
- **Tính năng**: Cho phép thành viên dùng lệnh (ví dụ: `/add_deadline`) để thêm các mốc thời gian nội bộ (VD: "Chốt chia việc đồ án", "Họp nhóm tối nay", "Hạn chót gửi code cho Leader").
- **Lợi ích**: Bot sẽ quản lý, nhắc nhở và đưa các deadline này vào báo cáo tiến độ hằng ngày chung với deadline từ Moodle.

## 3. Tự động chia Thread để thảo luận bài tập
Thay vì gửi một tin nhắn báo deadline chung chung vào channel (dễ làm trôi các tin nhắn khác):
- **Tính năng**: Mỗi khi có bài tập mới, bot tự động tạo một **Thread (luồng tin nhắn)** đính kèm với thông báo đó (ví dụ: `Thread: Thảo luận Bài tập thực hành 1`).
- **Lợi ích**: Thành viên có thể gửi tài liệu, chia sẻ cách giải, hoặc đặt câu hỏi trực tiếp trong Thread đó, giúp channel luôn gọn gàng và dễ tra cứu.

## 4. Tích hợp AI (LLM) để tóm tắt thông báo
Giảng viên đôi khi gửi những thông báo (Announcements) rất dài trên diễn đàn Moodle.
- **Tính năng**: Tích hợp gọi API của Gemini hoặc OpenAI để "tóm tắt nhanh" (TL;DR) ý chính của thông báo (Ví dụ: "Cô dặn tuần sau nghỉ", "Dời hạn nộp bài HW2 sang thứ 6"). 
- **Lợi ích**: Đoạn tóm tắt được gửi kèm ngay đầu thông báo, giúp sinh viên nắm bắt thông tin quan trọng chỉ trong 3 giây.

## 5. Cá nhân hóa & Phân quyền (Role Management)
- **Gắn Role tự động (Auto-Roles)**: Bot tự động tạo Role tương ứng với từng môn (ví dụ: `@PTTKHT`, `@KTLT`). Ai học môn nào thì tự click nhận Role môn đó.
- **Smart Pinging**: Thay vì dùng `@everyone`, bot chỉ tag đúng Role của môn học đó (`@PTTKHT 🚨 DEADLINE MỚI`), tránh làm phiền những bạn không học môn này trong server.
- **Nhắc nhở qua Tin nhắn riêng (DM)**: Cho phép sinh viên đăng ký nhận thông báo deadline qua Direct Message với bot và tùy chỉnh thời gian nhắc (ví dụ: "Chỉ nhắc tôi trước 2 tiếng").

## 6. Mở rộng thành Bot đa người dùng / Đa server (SaaS Scale)
Hiện tại bot được thiết kế tối ưu cho 1 nhóm/1 cá nhân (dùng 1 token/lịch Moodle).
- **Tính năng**: Phát triển cơ chế cho phép nhiều sinh viên kết nối tài khoản Moodle của họ vào bot (bằng cách gửi link ICS qua tin nhắn riêng cho bot).
- **Lợi ích**: Bot sẽ tổng hợp và gộp (merge) tất cả môn học của mọi người. Rất phù hợp nếu dùng bot cho một Server tập thể lớp Đại học, nơi các bạn học các lớp/môn khác nhau nhưng vẫn muốn dùng chung một hệ thống nhắc nhở.

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
Moodle chỉ cung cấp hạn chót nộp bài cuối cùng của môn học. Tuy nhiên, khi làm bài tập lớn (Đồ án/Project), một nhóm thường cần chia nhỏ công việc thành nhiều mốc thời gian (milestones) khác nhau.

**Chi tiết tính năng & Cách hoạt động:**
- Thành viên có thể dùng lệnh `/add_deadline` trực tiếp trên Discord. Bot sẽ mở ra một Form (Modal) để nhập:
  - Tên công việc (VD: "Chốt chia việc", "Nộp bản nháp Word", "Họp review code").
  - Kênh/Môn học liên quan.
  - Hạn chót (Ngày & Giờ).
  - Ai phụ trách? (Tag user Discord để nhắc tên trực tiếp).
- **Lưu trữ & Nhắc nhở đồng bộ:** Các deadline này được lưu chung vào Database (ví dụ thêm trường `source = 'custom'`). Bot sẽ tự động áp dụng quy trình nhắc nhở (nhắc trước 3 ngày, khẩn cấp 1 ngày) và cho phép thả reaction ✅ để đánh dấu hoàn thành y hệt như deadline tải về từ Moodle.
- **Tích hợp báo cáo:** Trong báo cáo tóm tắt hằng ngày (Daily Summary), các "Deadline nội bộ" sẽ được liệt kê cùng để leader dễ dàng đôn đốc tiến độ nhóm.

## 3. Tự động tạo Thread Thảo luận bài tập (Auto-Threading)
Hiện tại, khi bot thông báo có bài tập mới vào channel (ví dụ `#khtn-toan`), tin nhắn này rất dễ bị trôi nếu mọi người bàn luận quá nhiều về cách làm bài ngay bên dưới.

**Chi tiết tính năng & Lợi ích:**
- **Tự động hóa luồng (Workflow):** Sử dụng API của Discord (`Create Thread`). Ngay sau khi bot gửi tin báo "🚨 DEADLINE MỚI", bot sẽ gọi API để tạo tự động một Thread đính kèm ngay dưới tin nhắn đó với tên `💬 Thảo luận: [Tên Bài Tập]`.
- **Lợi ích thực tế:**
  - **Gom nhóm thông tin:** Mọi thắc mắc, link tài liệu tham khảo, hay file code nháp liên quan đến bài tập đó đều được gửi vào trong Thread này.
  - **Giữ Channel gọn gàng:** Kênh chat chính của môn học sẽ chỉ chứa các tin nhắn quan trọng (cột mốc deadline, thông báo từ giảng viên), rất dễ lướt lên để tìm lại thông tin.
  - **Focus mục tiêu:** Ai làm bài nào thì join vào Thread bài đó, tránh bị loãng thông báo (Noti) cho những bạn không làm phần việc đó.

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

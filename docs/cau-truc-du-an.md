# Cấu trúc thư mục dự án `course_fit_bot`

Dưới đây là cấu trúc hiện tại của dự án cùng với giải thích chi tiết chức năng của từng thư mục và tập tin:

```text
Notification Project/
├── .git/                      # Chứa dữ liệu của kho lưu trữ (repository) Git nội bộ.
├── .github/
│   └── workflows/
│       └── notify.yml         # [QUAN TRỌNG] File cấu hình GitHub Actions. Nó lên lịch chạy tự động bot mỗi 30 phút.
├── doc/                       # Thư mục chứa tài liệu yêu cầu ban đầu của dự án.
├── .gitignore                 # Cấu hình Git để ẩn (không push) các file rác, file tạm lên GitHub.
├── main.py                    # [QUAN TRỌNG] File mã nguồn chính của bot. Chịu trách nhiệm lấy file ICS, phân tích và bắn thông báo qua Discord.
├── requirements.txt           # Danh sách các thư viện Python cần thiết (hiện tại chỉ cần `requests`).
├── state.json                 # [QUAN TRỌNG] File "trí nhớ" của bot. Nó lưu mã ID của những deadline ĐÃ thông báo để không bị spam 2 lần.
├── prompt-xay-dung-cong-cu.md # File lưu trữ prompt yêu cầu dự án.
├── yeu-cau-du-an.md           # File lưu trữ yêu cầu chi tiết dự án.
├── files.zip                  # File nén chứa tài liệu ban đầu bạn cung cấp.
├── (Các file rác/file tạm)    # Các file sinh ra trong quá trình mình test và phân tích cấu trúc web:
│   ├── calendar.ics           
│   ├── events.txt             
│   ├── extract.py             
│   ├── login_forms.txt        
│   ├── login_page.html        
│   ├── parsed.html            
│   ├── Đăng nhập vào trang...mhtml 
│   └── Moodle CQDT fit...mhtml
```

## Giải thích chức năng các file cốt lõi đang chạy trên GitHub

### 1. `main.py`
Đây là bộ não của con bot. Chức năng chính:
- Nhận URL Lịch (`MOODLE_CALENDAR_URL`) và URL Discord (`DISCORD_WEBHOOK_URL`) từ môi trường an toàn (GitHub Secrets).
- Đóng giả làm trình duyệt (User-Agent Chrome) để tải file dữ liệu lịch `.ics` trực tiếp từ Moodle mà không cần đăng nhập.
- Trích xuất thông tin Deadline (Tên sự kiện, Thời gian) bằng Regular Expressions.
- Đối chiếu với file `state.json`. Nếu gặp ID sự kiện mới tinh chưa từng gửi, nó sẽ gửi tin báo qua Discord (có ping `@everyone`).
- Cập nhật lại những ID mới gửi vào `state.json`.

### 2. `.github/workflows/notify.yml`
Đây là công nhân chạy tự động của bạn. Chức năng:
- Lên lịch báo thức (Cron): `*/30 * * * *` (Chạy lệnh mỗi 30 phút).
- Tự động tạo một máy ảo Ubuntu nhỏ, cài Python.
- Truyền các giá trị bảo mật (Secrets) vào cho `main.py` chạy.
- Sau khi `main.py` chạy xong, file `state.json` sẽ bị thay đổi (do thêm deadline mới vào bộ nhớ). File này sẽ chạy lệnh `git commit` để tự động đẩy sự thay đổi đó lưu ngược lại lên repository để lần chạy sau bot vẫn "nhớ" được.

### 3. `state.json`
Đơn giản là một file định dạng JSON. Cấu trúc của nó chỉ là:
```json
{
    "notified_items": [
        "57754@courses.fit.hcmus.edu.vn",
        "57755@courses.fit.hcmus.edu.vn"
    ]
}
```
*Chức năng:* Tránh spam. Nếu không có nó, cứ mỗi 30 phút bot sẽ bắn lại toàn bộ 10-20 cái deadline của bạn.

---

> [!TIP]
> Lưu ý: Những file được đánh dấu **[QUAN TRỌNG]** là những file đang được đẩy lên và vận hành trực tiếp trên GitHub Repository của bạn. Những file tạm/rác còn lại (như file `.mhtml`, `.html`) chỉ nằm ở máy cá nhân của bạn, không ảnh hưởng đến bot.

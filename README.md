# Hoàn tất Công cụ thông báo qua Discord

Mình đã code xong toàn bộ công cụ. Cơ chế hoạt động như sau:
- Script `main.py` sẽ sử dụng tài khoản của bạn để đăng nhập tự động vào `courses.fit.hcmus.edu.vn`.
- Sau đó nó sẽ vào thẳng mục Lịch (Calendar Upcoming) để lấy tất cả các sự kiện sắp diễn ra.
- Nó so sánh với file `state.json`, nếu có sự kiện nào chưa từng được thông báo thì nó sẽ gửi qua cái URL Webhook của Discord.
- Cuối cùng, nó ghi lại danh sách những cái đã thông báo vào `state.json` để lần sau chạy nó không gửi lặp lại.

## Hướng dẫn 3 bước để đưa lên GitHub chạy tự động

Bạn hãy làm theo các bước này để công cụ tự chạy 24/7 nhé:

### Bước 1: Tạo Repository và đẩy code lên GitHub
1. Vào GitHub của bạn, tạo một Repository mới (đặt tên là `course-fit-bot` chẳng hạn) và nhớ để chế độ **Private** (ẩn) để người khác không thấy code của bạn.
2. Tải toàn bộ các file trong thư mục `Notification Project` (trừ file html mẫu và file rác) gồm:
   - `main.py`
   - `requirements.txt`
   - `state.json`
   - Folder `.github` (bao gồm thư mục con `workflows` và file `notify.yml`)
   và đẩy chúng lên repository vừa tạo (có thể up thẳng trên giao diện web của GitHub).

> [!CAUTION]
> Repository phải bắt buộc chứa thư mục ẩn `.github/workflows` thì GitHub Actions mới nhận diện được file tự động hoá nhé!

### Bước 2: Thiết lập lại GitHub Secrets
Trong Repo trên GitHub, bạn thao tác như sau:
1. Vào tab **Settings** của Repo.
2. Chọn phần **Secrets and variables** (ở menu bên trái) -> Chọn **Actions**.
3. Bấm biểu tượng "Thùng rác" để xoá bỏ 2 biến cũ là `COURSE_FIT_USERNAME` và `COURSE_FIT_PASSWORD` đi nhé.
4. Bấm nút xanh lá cây **New repository secret** và thêm biến mới này:
   - Name: `MOODLE_CALENDAR_URL` | Value: *Đường link dài chứa ICS mà bạn vừa cung cấp ở trên*
5. Biến `DISCORD_WEBHOOK_URL` bạn vẫn giữ nguyên như cũ.

### Bước 3: Cấp quyền ghi (Write) cho GitHub Actions
Để script có thể lưu lại lịch sử `state.json` (chống spam), bạn cần cấp quyền cho nó có thể tự sửa code:
1. Cũng ở tab **Settings** của Repo.
2. Tìm mục **Actions** ở menu trái -> Chọn **General**.
3. Cuộn xuống dưới cùng tìm mục **Workflow permissions**.
4. Tích chọn **Read and write permissions**.
5. Bấm **Save**.

### Chạy thử (Manual Test)
- Bạn chuyển sang tab **Actions** trên repo GitHub của bạn.
- Bấm vào tên workflow **Notification Bot** ở bên trái.
- Bấm nút **Run workflow** (ở góc phải) để cho nó chạy thử lần đầu.
- Xong! Từ nay cứ mỗi 30 phút, nó sẽ tự động chạy ngầm và báo qua Discord nếu có deadline/thông báo mới.

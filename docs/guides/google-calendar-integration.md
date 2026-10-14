# Hướng dẫn Tích hợp Google Calendar cho Bot Deadline

Tài liệu hướng dẫn từng bước thiết lập đồng bộ deadline từ Moodle và Discord lên Google Calendar qua **Google Service Account** để nhận thông báo và theo dõi tiện lợi trên điện thoại di động (Android & iOS).

---

## 🌟 Vì sao sử dụng Google Service Account?
- **Hoàn toàn miễn phí:** Tận dụng Google Cloud Free Tier.
- **Serverless 100%:** Không cần mở trình duyệt đăng nhập thủ công, không bị giới hạn hết hạn token sau 7 ngày như OAuth thông thường.
- **Tự động hóa tuyệt đối:** Chạy mượt mà trong GitHub Actions hay máy chủ cá nhân.
- **Bảo mật:** Chỉ cấp quyền chỉnh sửa trên đúng Lịch mà bạn chỉ định chia sẻ, không can thiệp vào email hay dữ liệu cá nhân khác.

---

## 🛠️ Hướng dẫn cài đặt (5 bước đơn giản)

### Bước 1: Tạo dự án & Bật Google Calendar API trên Google Cloud
1. Truy cập [Google Cloud Console](https://console.cloud.google.com/).
2. Đăng nhập tài khoản Google của bạn và tạo một **Project mới** (ví dụ: `Fit-Deadline-Bot`).
3. Trên thanh tìm kiếm ở đầu trang, gõ **Google Calendar API** và bấm chọn.
4. Bấm nút **Enable** (Bật) để kích hoạt API cho dự án.

### Bước 2: Tạo Service Account và Tải file Key JSON
1. Vào menu bên trái: **APIs & Services** → **Credentials** (Thông tin xác thực).
2. Bấm nút **+ CREATE CREDENTIALS** ở trên cùng → chọn **Service Account**.
3. Điền tên (ví dụ: `deadline-bot-sync`) → bấm **Create and Continue** → các bước phân quyền tiếp theo có thể bấm **Done** (bỏ qua).
4. Trong danh sách Service Accounts vừa tạo, bấm vào email của Service Account (dạng: `deadline-bot-sync@xxx.iam.gserviceaccount.com`).
5. Chuyển sang tab **KEYS** → bấm **ADD KEY** → chọn **Create new key**.
6. Chọn định dạng **JSON** rồi bấm **Create**. Trình duyệt sẽ tự động tải về 1 file `.json` chứa private key.
7. **Lưu ý quan trọng:** Sao chép địa chỉ email của Service Account này (bạn sẽ cần nó ở Bước 3).

### Bước 3: Chia sẻ Lịch của bạn với Service Account
1. Mở [Google Calendar](https://calendar.google.com/) trên trình duyệt máy tính.
2. Bạn có thể dùng Lịch mặc định của mình, hoặc tạo một Lịch mới riêng cho việc học (khuyên dùng):
   - Bên cạnh mục **Lịch khác (Other calendars)** ở menu bên trái, bấm dấu `+` → chọn **Tạo lịch mới (Create new calendar)**.
   - Đặt tên ví dụ: `📚 FIT HCMUS Deadlines` → bấm **Tạo lịch**.
3. Di chuột vào Lịch bạn muốn đồng bộ → bấm dấu ba chấm `⋮` → chọn **Cài đặt và chia sẻ (Settings and sharing)**.
4. Cuộn xuống mục **Chia sẻ với những người hoặc nhóm cụ thể (Share with specific people or groups)**:
   - Bấm **Thêm người và nhóm (Add people and groups)**.
   - Dán địa chỉ email Service Account đã copy ở Bước 2 vào.
   - Ở ô Quyền (Permissions), chọn: **Thực hiện thay đổi đối với các sự kiện (Make changes to events)**.
   - Bấm **Gửi (Send)**.

### Bước 4: Lấy Calendar ID
1. Vẫn trong trang Cài đặt của Lịch đó, cuộn xuống mục **Tích hợp lịch (Integrate calendar)**.
2. Tìm dòng **Mã lịch (Calendar ID)**:
   - Nếu là lịch tạo mới, Calendar ID sẽ có dạng: `c_xxxxxxxxxxxxxxxxxxxxxxxxxx@group.calendar.google.com`.
   - Nếu là lịch chính cá nhân, Calendar ID là chính địa chỉ Gmail của bạn.
3. Sao chép Calendar ID này.

### Bước 5: Cấu hình Biến Môi Trường

#### Cách A: Chạy cục bộ (Local Development)
Mở file `.env` trong thư mục dự án và điền:
```env
# Cách 1: Đặt file JSON tải về cùng thư mục bot
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
GOOGLE_CALENDAR_ID=c_xxxxxxxxxxxxxxxxxxxx@group.calendar.google.com

# Cách 2 (hoặc): Dán toàn bộ nội dung file JSON vào 1 dòng:
# GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", "project_id": "...", ...}
```

#### Cách B: Chạy tự động qua GitHub Actions
Trong Repository GitHub của bạn:
1. Vào **Settings** → **Secrets and variables** → **Actions**.
2. Thêm 2 Secrets mới:
   - `GOOGLE_CALENDAR_ID`: Dán Calendar ID lấy ở Bước 4.
   - `GOOGLE_SERVICE_ACCOUNT_JSON`: Mở file JSON tải về ở Bước 2 bằng Notepad/VS Code, sao chép toàn bộ nội dung và dán vào secret này.

---

## 🚀 Thử nghiệm đồng bộ

### 1. Đồng bộ toàn bộ deadline hiện có trong database
Chạy lệnh sau trên terminal máy tính:
```bash
python main.py --sync-gcal
```
Bot sẽ quét toàn bộ deadline (cả Moodle và nội bộ Discord) trong database và đẩy lên Google Calendar của bạn.

### 2. Đồng bộ tự động
- Mỗi 30 phút, khi có deadline mới phát hiện từ Moodle hoặc được thêm qua `/add_deadline`, bot sẽ tự động tạo sự kiện lên Google Calendar.
- Khi có bạn thả cảm xúc `✅` trên tin nhắn Discord để báo xong bài, bot sẽ tự động cập nhật sự kiện trên Google Calendar thành màu **Xanh lá cây** và đổi tên thành `✅ [XONG] [Tên môn] Tên bài tập`!
- Ứng dụng Google Calendar trên điện thoại của bạn sẽ tự động rung/đẩy chuông thông báo:
  - **Trước 1 ngày** (24 giờ trước hạn chót).
  - **Trước 3 giờ** (nhắc nhở bài tập).
  - **Trước 30 phút** (cảnh báo khẩn cấp).

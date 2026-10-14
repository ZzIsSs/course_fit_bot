# 📱 Bộ Thiết Kế Giao Diện Mobile (Tối Ưu Cho Xiaomi 13T Pro)
> **Dự án:** HCMUS Course FIT Notification Bot  
> **Người thực hiện:** Nguyên  
> **Đặc tả màn hình Xiaomi 13T Pro:** Kích thước 6.67 inch AMOLED CrystalRes, tần số quét 144Hz, độ phân giải 1220 x 2712 pixels (Tỷ lệ ~20:9), hỗ trợ gam màu DCI-P3 & HDR10+.

---

## 🖼️ Danh Sách Các Bản Thiết Kế Mẫu

Thư mục này chứa 3 phương án thiết kế giao diện được sinh riêng cho dự án theo tỉ lệ màn hình dọc điện thoại:

### 1. `01_Huong1_Task_Urgency_TickTick.jpg`
* **Phong cách:** Modern Task & Urgency (Cảm hứng từ **TickTick** & **Todoist**).
* **Điểm nhấn:**
  * Header đo tiến độ tuần (`75% Done`) dạng vòng tròn trực quan.
  * Thẻ công việc nổi bật độ khẩn cấp (Khung phát sáng vàng cam với đếm ngược `4h left` cho bài nộp trong ngày).
  * Badge tự động `Moodle Auto-completed` màu xanh ngọc cho các bài tập bot phát hiện đã nộp trên trường.
  * Nút nổi FAB (+) để thêm deadline thủ công một chạm.
  * Phù hợp nhất cho nhu cầu kiểm tra nhanh bài tập hằng ngày.

### 2. `02_Huong2_Timeline_Planner_Structured.jpg`
* **Phong cách:** Visual Timeline & Student Planner (Cảm hứng từ **Structured** & **Notion Calendar**).
* **Điểm nhấn:**
  * Dải ngày trong tuần cuộn ngang mượt mà ở trên cùng.
  * Trục thời gian dọc (Vertical Chronological Timeline) với vạch chỉ thời gian thực phát sáng đỏ (`10:15 AM`).
  * Khối sự kiện được bo tròn mềm mại, phân màu theo môn học (`#NMTTNT` màu tím neon, `#KTLT` màu xanh dương, họp nhóm Discord màu xanh da trời).
  * Phù hợp cho việc lập kế hoạch biểu đồ học tập theo giờ và tuần.

### 3. `03_Huong3_Kanban_Project_Linear.jpg`
* **Phong cách:** Project & Team Kanban (Cảm hứng từ **Linear Mobile** & **Trello**).
* **Điểm nhấn:**
  * Thiết kế theo từng môn học `#CSC10014 - Nhập Môn Trí Tuệ Nhân Tạo`.
  * Các cột bảng kéo thả: `To Do` (Cần làm) và `Done` (Đã hoàn thành).
  * Hiển thị avatar thành viên phụ trách và thẻ phân loại `#Lab2`, `#AStar`, `#Report`.
  * Phù hợp tối đa cho việc quản lý bài tập nhóm và đồ án môn học.

---

## 🛠️ Hướng Triển Khai Tiếp Theo
* **Cách 1 (Nhanh nhất):** Chuyển đổi mã nguồn `frontend/` (React + Tailwind CSS) sang giao diện chuẩn Mobile Responsive và kích hoạt PWA để cài trực tiếp lên màn hình Xiaomi 13T Pro.
* **Cách 2 (Native):** Sử dụng React Native (Expo) hoặc Flutter để build file `.apk` cài trực tiếp lên máy.

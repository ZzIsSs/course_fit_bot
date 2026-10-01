# REPOSITORY CONTEXT PACK — TỔNG QUAN & CHỈ MỤC

> **Dự án:** Course FIT HCMUS Notification & Automation Platform (`course-fit-bot`)  
> **Người thực hiện:** Solution Architect  
> **Người nhận đề xuất:** Chuyên gia Prompt (Prompt Engineer) / AI Assistant  
> **Mục tiêu:** Cung cấp bộ ngữ cảnh chuẩn hóa, tinh gọn và phân tầng về toàn bộ hệ thống để làm cơ sở xây dựng system prompt, task prompt hoặc context window cho LLM.

---

## 1. Giới thiệu tổng quan hệ thống

Hệ thống **Course FIT HCMUS Bot** là nền tảng tự động hóa giám sát học tập, thông báo bài tập (deadlines) và đồng bộ dữ liệu đa kênh cho sinh viên Khoa Công nghệ Thông tin - Trường ĐH Khoa học Tự nhiên (HCMUS):

- **Nguồn cấp dữ liệu (Ingestion):** Tự động crawl và phân tích lịch học/hạn nộp (iCalendar/ICS) và tài liệu, bài đăng diễn đàn từ Moodle LMS (`courses.fit.hcmus.edu.vn`), hỗ trợ thêm hạn nộp thủ công qua Slash Commands (`/add_deadline`), API webhook và Web UI.
- **Phân phối & Tương tác (Distribution & Interactions):** Tự động phân loại môn học vào các nhóm kênh Discord theo học kỳ, gửi thông báo nhắc hạn (mới, 3 ngày, 1 ngày, tóm tắt 7h sáng), tạo Discord Scheduled Events và lắng nghe reaction `✅` để đánh dấu hoàn thành.
- **Đồng bộ ngoại vi (Sync Adapters):** Đồng bộ trạng thái công việc hai chiều sang **Notion Database** (Todo List) và **Google Calendar** (Lịch cá nhân với 3 mốc thông báo đẩy).
- **Giao diện quản trị (Web Dashboard):** Single Page Application xây dựng bằng React 18 + Vite + Tailwind CSS triển khai trên Vercel.

---

## 2. Bản đồ cấu trúc bộ tài liệu (Document Index)

Bộ tài liệu này được chia thành các tệp chuyên biệt, hỗ trợ nạp ngữ cảnh theo từng mục đích:

| Tên tệp | Nội dung trọng tâm | Trường hợp sử dụng cho Prompt |
| :--- | :--- | :--- |
| [`01_HIGH_LEVEL_ARCHITECTURE_AND_TREE.md`](./01_HIGH_LEVEL_ARCHITECTURE_AND_TREE.md) | Cây thư mục cấp cao (<= 3 cấp), phân tầng kiến trúc (API, Services, DAO, Frontend, DevOps) | Dùng khi prompt yêu cầu sửa đổi cấu trúc thư mục, bổ sung tính năng mới đúng tầng |
| [`02_TECH_STACK_AND_ENVIRONMENT.md`](./02_TECH_STACK_AND_ENVIRONMENT.md) | Chi tiết ngôn ngữ, framework, dependencies kèm phiên bản, môi trường runtime | Dùng khi sinh mã (code generation), cấu hình Docker/CI hoặc cài đặt thư viện |
| [`03_END_TO_END_DATA_FLOW.md`](./03_END_TO_END_DATA_FLOW.md) | Chi tiết 4 luồng dữ liệu chính (Cron, Slash Command, Web Dashboard, External Webhook), biểu đồ Mermaid | Dùng khi debug logic nghiệp vụ, thiết kế workflow, tối ưu luồng xử lý dữ liệu |
| [`04_CORE_MODULES_INVENTORY.md`](./04_CORE_MODULES_INVENTORY.md) | Bảng kiểm kê toàn diện các file/module cốt lõi: LOC, vai trò, độ phức tạp, input/output | Dùng khi phân chia task refactor, review code hoặc đánh giá phạm vi ảnh hưởng |
| [`05_CROSS_CUTTING_AND_HOTSPOTS.md`](./05_CROSS_CUTTING_AND_HOTSPOTS.md) | Cơ chế bảo mật (Ed25519, HMAC), DB pooling serverless, rà soát nợ kỹ thuật & điểm nóng | Dùng khi audit an toàn thông tin, hardening hệ thống, xử lý nợ kỹ thuật |
| [`FULL_REPOSITORY_CONTEXT_PACK.md`](./FULL_REPOSITORY_CONTEXT_PACK.md) | **Bản tổng hợp nguyên khối (All-in-One)** gộp toàn bộ 5 phần trên vào 1 file duy nhất | **Dành riêng để đính kèm (attach) hoặc copy/paste toàn bộ vào 1 prompt duy nhất** |

---

## 3. Hướng dẫn nhanh cho Chuyên gia Prompt (Prompting Guidelines)

Khi cung cấp bối cảnh này cho mô hình ngôn ngữ lớn (LLM):
1. **Nếu prompt yêu cầu viết code Backend/Bot:** Nạp kèm `02_TECH_STACK_AND_ENVIRONMENT.md`, `03_END_TO_END_DATA_FLOW.md` và `04_CORE_MODULES_INVENTORY.md`.
2. **Nếu prompt yêu cầu nâng cấp Frontend:** Nạp kèm `01_HIGH_LEVEL_ARCHITECTURE_AND_TREE.md` và mục Frontend trong `02_TECH_STACK_AND_ENVIRONMENT.md`.
3. **Nếu dùng cho một phiên làm việc toàn diện (Full Session):** Chỉ cần gửi duy nhất tệp `FULL_REPOSITORY_CONTEXT_PACK.md`.

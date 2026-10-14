# ĐẶC TẢ THIẾT KẾ FIGMA (FIGMA DESIGN SPECIFICATION)
## HỆ THỐNG: COURSE FIT HCMUS - STUDY & DEADLINE MANAGEMENT SYSTEM
**Role:** Senior UI/UX Designer & Frontend Architect  
**Target Platform:** Desktop Web Dashboard (Optimized for 1440x900px, Responsive down to 390px Mobile)  
**Design Paradigm:** Modern Functional B2B SaaS / Clean Educational Tech (Linear + Notion aesthetic with HCMUS Identity)

---

# MỤC LỤC
1. [Hệ thống Thiết kế (Design System & Design Tokens)](#1-hệ-thống-thiết-kế-design-system--design-tokens)
2. [UI Components & Biến thể Auto-Layout (Components & Variants)](#2-ui-components--biến-thể-auto-layout)
3. [Cấu trúc Sitemap & Điều hướng (Navigation Architecture)](#3-cấu-trúc-sitemap--điều-hướng)
4. [Đặc tả Chi tiết Layout 5 Màn hình Chính](#4-đặc-tả-chi-tiết-layout-5-màn-hình-chính)
   - [Màn 1: Dashboard Tổng quan (Overview & Progress)](#màn-1-dashboard-tổng-quan-overview--progress)
   - [Màn 2: Trung tâm Quản lý Deadline (List / Calendar / Kanban)](#màn-2-trung-tâm-quản-lý-deadline)
   - [Màn 3: Chi tiết Môn học & Kho Tài liệu Moodle](#màn-3-chi-tiết-môn-học--kho-tài-liệu-moodle)
   - [Màn 4: Bảng tin Thông báo & AI Tóm tắt (TL;DR)](#màn-4-bảng-tin-thông-báo--ai-tóm-tắt-tldr)
   - [Màn 5: Cài đặt Hệ thống & Tích hợp Đồng bộ](#màn-5-cài-đặt-hệ-thống--tích-hợp-đồng-bộ)
5. [Luồng Prototype & Tương tác Vi mô (Micro-interactions)](#5-luồng-prototype--tương-tác-vi-mô)

---

# 1. HỆ THỐNG THIẾT KẾ (DESIGN SYSTEM & DESIGN TOKENS)

### 1.1. Bảng Màu (Color Palette & Semantic Tokens)
Hệ màu được xây dựng dựa trên màu xanh truyền thống của trường ĐH Khoa học Tự nhiên (HCMUS Blue) kết hợp với các dải màu hiện đại của các SaaS hàng đầu:

#### A. Màu Thương hiệu (Brand & Identity)
| Tên Token | Hex Code | Figma Style Name | Mục đích sử dụng |
|---|---|---|---|
| `brand-primary-900` | `#0D2552` | `Brand/Primary-900` | Header nền tối, Brand Dark Accent |
| `brand-primary-700` | `#1D4ED8` | `Brand/Primary-700` | Primary Button Hover, Active States |
| `brand-primary-600` | `#2563EB` | `Brand/Primary-600` | **HCMUS Blue Chủ đạo**, Primary Buttons, Active Links |
| `brand-primary-500` | `#3B82F6` | `Brand/Primary-500` | Focus Rings, Secondary Accents |
| `brand-primary-100` | `#DBEAFE` | `Brand/Primary-100` | Badge nền xanh, Active Item Background |
| `brand-primary-50`  | `#EFF6FF` | `Brand/Primary-50`  | Hover background trên nền sáng |

#### B. Màu Trợ năng AI (AI Magic Token - Dành cho Gemini Summary)
| Tên Token | Hex Code | Figma Style Name | Mục đích sử dụng |
|---|---|---|---|
| `ai-gradient-start` | `#6366F1` | `AI/Indigo` | Gradient viền & icon tính năng AI |
| `ai-gradient-end`   | `#EC4899` | `AI/Pink`   | Gradient viền & icon tính năng AI |
| `ai-surface-subtle` | `#F5F3FF` | `AI/Surface-Light` | Nền thẻ tóm tắt AI (Light mode) |
| `ai-surface-dark`   | `#1E1B4B` | `AI/Surface-Dark`  | Nền thẻ tóm tắt AI (Dark mode) |

#### C. Màu Trạng thái Deadline (Semantic Status Colors)
| Trạng thái | Nền Light (`bg`) | Viền (`border`) | Chữ (`text`) | Nền Dark (`bg-dark`) | Chữ Dark (`text-dark`) |
|---|---|---|---|---|---|
| **Khẩn cấp (< 24h)** | `#FEF2F2` (Red-50) | `#FCA5A5` (Red-300) | `#DC2626` (Red-600) | `#450A0A` | `#F87171` |
| **Sắp tới (< 3 ngày)** | `#FFFBEB` (Amber-50) | `#FCD34D` (Amber-300) | `#D97706` (Amber-600) | `#451A03` | `#FBBF24` |
| **Còn hạn (> 3 ngày)** | `#F0FDF4` (Emerald-50) | `#86EFAC` (Emerald-300) | `#16A34A` (Emerald-600) | `#052E16` | `#4ADE80` |
| **Đã hoàn thành ✅** | `#F8FAFC` (Slate-50) | `#CBD5E1` (Slate-300) | `#64748B` (Slate-500) | `#1E293B` | `#94A3B8` |
| **Quá hạn / Trễ ⚠️** | `#FFF1F2` (Rose-50) | `#FDA4AF` (Rose-300) | `#BE123C` (Rose-700) | `#4C0519` | `#FB7185` |

#### D. Bề mặt & Chữ (Surface & Neutral System)
- **Light Theme:**
  - `bg-canvas`: `#F8FAFC` (Slate 50)
  - `bg-surface`: `#FFFFFF` (Pure White)
  - `bg-surface-elevated`: `#FFFFFF` (Shadow Level 2)
  - `border-subtle`: `#F1F5F9` (Slate 100)
  - `border-default`: `#E2E8F0` (Slate 200)
  - `text-primary`: `#0F172A` (Slate 900)
  - `text-secondary`: `#475569` (Slate 600)
  - `text-tertiary`: `#94A3B8` (Slate 400)
- **Dark Theme:**
  - `bg-canvas`: `#0B0F19` (Deep Navy Black)
  - `bg-surface`: `#111827` (Gray 900)
  - `bg-surface-elevated`: `#1F2937` (Gray 800)
  - `border-subtle`: `#1E293B` (Slate 800)
  - `border-default`: `#334155` (Slate 700)
  - `text-primary`: `#F8FAFC` (Slate 50)
  - `text-secondary`: `#94A3B8` (Slate 400)
  - `text-tertiary`: `#64748B` (Slate 500)

---

### 1.2. Typography (Inter / Plus Jakarta Sans)
Ưu tiên sử dụng font chữ **Plus Jakarta Sans** (hoặc **Inter**) với khả năng hiển thị tiếng Việt và số học sắc nét:

| Cấp bậc (Hierarchy) | Size / Line-height | Weight | Letter Spacing | Áp dụng trên Figma |
|---|---|---|---|---|
| **Display 1** | `32px / 40px` | Bold (700) | `-0.02em` | Tiêu đề chào mừng trang chính, Tỷ lệ % tiến độ lớn |
| **Heading 1** | `24px / 32px` | SemiBold (600) | `-0.015em` | Tiêu đề trang (Page Titles) |
| **Heading 2** | `20px / 28px` | SemiBold (600) | `-0.01em` | Tiêu đề Khối Module, Tên Modal |
| **Heading 3** | `16px / 24px` | SemiBold (600) | `0em` | Tên Môn học, Tên Bài tập, Tên Card |
| **Body Large** | `16px / 24px` | Regular (400) | `0em` | Đoạn văn bản mô tả, Nội dung tóm tắt AI |
| **Body Medium** | `14px / 20px` | Regular (400) | `0em` | Văn bản nội dung bảng, Mô tả deadline |
| **Body Medium Bold**| `14px / 20px` | SemiBold (600) | `0em` | Tên button, Header cột bảng, Label Input |
| **Caption / Meta** | `12px / 16px` | Medium (500) | `+0.01em` | Countdown chip, Tên giảng viên, Tag môn |
| **Micro / Overline**| `10px / 14px` | Bold (700) | `+0.05em` (Caps) | Nguồn dữ liệu (MOODLE, DISCORD, MANUAL) |

---

### 1.3. Spacing, Corner Radius & Elevation
- **Spacing Grid 8pt:**
  - `space-2` (2px), `space-4` (4px), `space-8` (8px), `space-12` (12px), `space-16` (16px), `space-24` (24px), `space-32` (32px), `space-48` (48px).
- **Corner Radius:**
  - `radius-sm`: `6px` (Badge, Button con, Checkbox)
  - `radius-md`: `8px` (Inputs, Standard Buttons, Dropdown items)
  - `radius-lg`: `12px` (Cards, Containers, Group list)
  - `radius-xl`: `16px` (Modal Popups, Dashboard Hero Banners)
  - `radius-full`: `9999px` (Avatars, Pill Badges, Status Dots)
- **Shadows (Elevation Levels):**
  - `shadow-xs`: `0 1px 2px rgba(15, 23, 42, 0.05)` (Cards phẳng)
  - `shadow-sm`: `0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04)` (Card nổi bật nhẹ)
  - `shadow-md`: `0 4px 6px -1px rgba(15, 23, 42, 0.1), 0 2px 4px -2px rgba(15, 23, 42, 0.06)` (Hover state, Dropdown menu)
  - `shadow-xl`: `0 20px 25px -5px rgba(15, 23, 42, 0.15), 0 8px 10px -6px rgba(15, 23, 42, 0.08)` (Modal dialogs)

---

# 2. UI COMPONENTS & BIẾN THỂ AUTO-LAYOUT

### 2.1. Button Component
- **Properties Figma:**
  - `Variant`: `Primary` | `Secondary` | `Outline` | `Ghost` | `Danger`
  - `Size`: `SM` (H: 32px) | `MD` (H: 40px) | `LG` (H: 48px)
  - `State`: `Default` | `Hover` | `Focused` | `Disabled` | `Loading`
  - `LeadingIcon`: `Boolean`
  - `TrailingIcon`: `Boolean`
- **Auto-Layout Specification (Size MD):**
  - Direction: Horizontal | Spacing: `8px`
  - Padding: `T/B: 10px, L/R: 16px` | Radius: `8px`
  - Fill/Hug: Width = Hug contents, Height = Fixed `40px`
  - *Primary Variant:* Fill `#2563EB`, Text `#FFFFFF` (14px SemiBold). Hover: `#1D4ED8`.
  - *Secondary Variant:* Fill `#EFF6FF`, Text `#2563EB`, Border `1px solid #DBEAFE`.

---

### 2.2. Deadline Status Badge
- **Properties Figma:**
  - `Type`: `Urgent` (<24h) | `Soon` (<3d) | `Normal` (>3d) | `Completed` (Đã xong) | `Overdue` (Trễ)
  - `Icon`: `Boolean` (Ví dụ: `Flame` cho gấp, `Clock` cho sắp tới, `CheckCircle` cho hoàn thành)
- **Auto-Layout Specification:**
  - Direction: Horizontal | Align: Center | Gap: `4px`
  - Padding: `T/B: 4px, L/R: 8px` | Radius: `9999px` (Pill)
  - Typography: 12px Medium
  - *Urgent Sample:* Fill `#FEF2F2`, Stroke `#FCA5A5`, Text `#DC2626`, Icon `flame` (12x12px).

---

### 2.3. Deadline Item Card (Core Interactive Component)
Thành phần hiển thị trên danh sách bài tập, cho phép tương tác hoàn thành tức thì.
- **Figma Layer Hierarchy:**
  ```
  [Frame] DeadlineItemCard (Auto-layout: Horizontal, Padding: 16px, Gap: 16px, Fill: bg-surface, Radius: 12px, Stroke: border-default)
  ├── [Interactive] Checkbox (Size: 20x20px, Radius: 6px, States: Unchecked / Checked with green tick)
  ├── [Frame] MainContent (Auto-layout: Vertical, Gap: 6px, Resizing: Fill container)
  │   ├── [Frame] HeaderRow (Auto-layout: Horizontal, Gap: 8px, Align: Center)
  │   │   ├── [Component] CourseBadge (e.g. "#nmttnt-csc10014" - Fill: #F1F5F9, Radius: 4px, 12px Medium)
  │   │   ├── [Text] DeadlineTitle ("Nộp bài tập thực hành Tuần 4 - Phân tích thuật toán")
  │   │   └── [Component] SourceTag (Text: "MOODLE" hoặc "THỦ CÔNG" - 10px Bold)
  │   └── [Frame] MetaRow (Auto-layout: Horizontal, Gap: 12px, Align: Center)
  │       ├── [Frame] DueTimeGroup (Icon: Calendar, Text: "23:59 25/09/2026")
  │       ├── [Component] CountdownChip ("Còn 14 giờ" - Màu Đỏ nhạt nếu gấp)
  │       └── [Frame] AssigneeInfo (Icon: User, Text: "@TruongBaoNguyen")
  └── [Frame] ActionsGroup (Auto-layout: Horizontal, Gap: 8px, Align: Center)
      ├── [Button Ghost] Icon Discord (Nhảy tới kênh chat của môn)
      ├── [Button Ghost] Icon External Link (Mở bài nộp trên Moodle)
      └── [Button Ghost] Icon More Menu (...)
  ```

---

### 2.4. Course Card Component
- **Figma Auto-Layout:**
  - Direction: Vertical | Padding: `20px` | Gap: `16px`
  - Fill: `bg-surface` | Radius: `16px` | Stroke: `1px solid border-default`
  - Header: Icon môn học (40x40px bo tròn), Mã môn tiếng Anh (`CSC10105`), Tag kỳ học (`HK1 24-25`).
  - Body: Tên tiếng Việt in đậm (`Nhập môn Tư duy Thuật toán`).
  - Footer: Badge số lượng bài tập còn hạn (`2 bài đang mở`), Nút bấm nhanh (`Kho tài liệu ↗`).

---

### 2.5. Modal Thêm Deadline Mới (Quick Add Modal)
- **Kích thước Frame:** `560px` Width, Height: Hug contents (Khoảng `620px`).
- **Auto-Layout:** Vertical, Padding: `24px`, Gap: `20px`, Radius: `16px`, Elevation: `shadow-xl`.
- **Form Controls:**
  1. *Header:* Tiêu đề "Thêm Mốc Deadline Mới", nút X đóng ở góc phải.
  2. *Field 1:* Dropdown chọn Môn học (Auto-complete, hiển thị mã môn + tên tiếng Việt).
  3. *Field 2:* Input Tiêu đề deadline (VD: "Chốt kịch bản thuyết trình Đồ án").
  4. *Field 3:* Date & Time Picker + 3 Nút Shortcut ("Hôm nay 23:59", "Tối mai 23:59", "+3 ngày").
  5. *Field 4:* Input Người phụ trách (Gõ Discord Tag hoặc tên thành viên).
  6. *Field 5:* Input Link tài liệu / Ghi chú (VD: Link Google Drive hoặc Google Docs).
  7. *Footer:* Auto-layout Horizontal, Right Align: Nút "Hủy bỏ" (Secondary) và "Tạo Deadline" (Primary).

---

# 3. CẤU TRÚC SITEMAP & ĐIỀU HƯỚNG

```
[Web Application (1440x900)]
├── Top Header (H: 64px, Fixed Top)
│   ├── Breadcrumbs & Tên Phân hệ
│   ├── Thanh Tìm kiếm Toàn cục (Cmd + K / Ctrl + K)
│   ├── Bộ chọn Học kỳ (Dropdown: "Học kỳ 1 - 2024-2025")
│   ├── Nút "+ Thêm Deadline" (Primary CTA)
│   ├── Trạng thái Serverless Bot (Pill Dot: 🟢 Live Sync 30m)
│   ├── Toggle Dark/Light Mode
│   └── User Avatar & Discord Tag
│
└── Left Sidebar (W: 240px Expanded / 72px Collapsed)
    ├── Brand Logo: Biểu tượng FIT HCMUS + Text "Course FIT"
    ├── Nhóm 1: TRUNG TÂM HỌC TẬP
    │   ├── 🏠 Dashboard Tổng quan (Overview)
    │   ├── 📅 Quản lý Deadline (Deadlines Hub)
    │   └── 📚 Môn học & Kho Tài liệu (Courses & Materials)
    ├── Nhóm 2: TRUYỀN THÔNG & AI
    │   └── 📢 Bảng tin Moodle & AI Tóm tắt (Announcements & AI TL;DR)
    ├── Nhóm 3: HỆ THỐNG
    │   └── ⚙️ Cài đặt & Đồng bộ (Integrations & Sync)
    └── Footer Sidebar: Phiên bản hệ thống `v2.0-serverless`
```

---

# 4. ĐẶC TẢ CHI TIẾT LAYOUT 5 MÀN HÌNH CHÍNH

---

## MÀN 1: DASHBOARD TỔNG QUAN (OVERVIEW & PROGRESS)
*Mục đích: Cung cấp bức tranh toàn cảnh về tiến độ học tập, các deadline cận kề và hành động khẩn cấp.*

- **Kích thước Frame:** `1440 x 900 px`
- **Cấu trúc Auto-Layout Body:**
  - Sidebar: `Width 240px`, Fill Height.
  - Main Content Container: `Width 1200px`, Padding: `28px 32px`, Gap: `24px`, Scroll Vertical.

```
+-----------------------------------------------------------------------------------------------+
| TOP HEADER (Search, Semester Selector, CTA '+ Thêm Deadline', Live Status, Dark/Light)        |
+-----------------------------------------------------------------------------------------------+
| BANNER TIẾN ĐỘ HỌC KỲ (Gradient Card: "Chào Nguyên! Bạn đã hoàn thành 75% bài tập kỳ này")   |
| [ Thước đo Progress Bar lớn: ████████████████░░░░ 18/24 bài tập đã nộp ✅ ]                   |
+-----------------------------------------------------------------------------------------------+
| 4 THẺ CHỈ SỐ KPI (Auto-layout Grid: 4 cột đều nhau)                                           |
| 1. [Tổng Deadline: 24] | 2. [Cần nộp gấp: 2 bài] | 3. [Đã xong: 18 bài] | 4. [Môn theo dõi: 6]|
+-------------------------------------------------------------+---------------------------------+
| CỘT TRÁI (8 Cột - 65% Width)                                | CỘT PHẢI (4 Cột - 35% Width)    |
|                                                             |                                 |
| 🔴 KHẨN CẤP (< 24 GIỜ)                                      | 📅 LỊCH THI & MỐC QUAN TRỌNG     |
| ----------------------------------------------------------- | ------------------------------- |
| Card: [CSC10105] Nộp Source Code Đồ án Giữa kỳ              | 28/09: Thi Giữa kỳ NM Trí Tuệ NT|
| - Hạn: 23:59 Hôm nay | Còn 4 giờ 12 phút ⚠️                 | 05/10: Hạn chót Nộp Đề cương    |
| - Nút: [✅ Đánh dấu Xong] [Mở Moodle ↗]                     | ------------------------------- |
|                                                             | ⚡ ĐỒNG BỘ NHANH (QUICK ACTIONS)|
| 🟡 SẮP TỚI TRONG 3 NGÀY                                     | - Bật Google Calendar Sync ↗   |
| ----------------------------------------------------------- | - Mở Notion Todo Board ↗        |
| Card: [CSC10014] Bài tập tuần 5 - Cây nhị phân tìm kiếm     | - Kiểm tra Discord Kênh chung   |
| - Hạn: 23:59 Ngày mai | Còn 1 ngày 8 giờ                    | ------------------------------- |
|                                                             | 🤖 TÓM TẮT AI GẦN NHẤT          |
| 🟢 HOẠT ĐỘNG GẦN ĐÂY                                        | "Cô Hà vừa dời hạn nộp HW2      |
| - Bạn đã đánh dấu ✅ bài tập NMCNTT lúc 14:20                | sang Thứ 6 tuần sau do bận công |
| - Moodle vừa sync 1 tài liệu mới môn PTTKHT                 | tác..." (Xem chi tiết)          |
+-------------------------------------------------------------+---------------------------------+
```

#### Chi tiết Dữ liệu & Trạng thái:
- **Loading State:** Sử dụng Skeleton Shimmer (Xám nhạt `bg-slate-200` có animation sóng) cho 4 thẻ KPI và 3 thanh danh sách deadline.
- **Empty State (Khi không có bài tập nào gần hạn):**
  - Minh họa: Icon `CheckCircle` xanh lá lớn (64x64px).
  - Tiêu đề: "Tuyệt vời! Không còn deadline nào khẩn cấp".
  - Phụ đề: "Bạn đã hoàn thành tất cả các mốc học tập trong 3 ngày tới. Hãy thư giãn hoặc ôn tập trước bài mới."

---

## MÀN 2: TRUNG TÂM QUẢN LÝ DEADLINE
*Mục đích: Không gian làm việc chuyên sâu cho việc tra cứu, lọc, sắp xếp và theo dõi deadline dưới 3 góc nhìn.*

- **Kích thước Frame:** `1440 x 900 px`
- **Header Thanh Công Cụ (Filter & View Switcher Toolbar):**
  - *Bên trái:* Search Box ("Tìm theo tên bài tập hoặc mã môn..."), Dropdown lọc Môn học, Filter Chip trạng thái (`Tất cả: 24`, `Cần nộp: 6`, `Đã xong: 18`, `Quá hạn: 0`).
  - *Bên phải:* View Switcher (Segmented Control 3 nút):
    1. 📋 **Danh sách (List View)** (Mặc định)
    2. 📆 **Lịch (Calendar View)**
    3. 🗂️ **Bảng Kanban (Board View)**

```
+-----------------------------------------------------------------------------------------------+
| TOOLBAR: [ 🔍 Tìm kiếm... ] [ Môn: Tất cả môn ▼ ] [ Chíp: Sắp tới (6) ]  |  [ 📋 List | 📆 Cal | 🗂️ Kanban ]|
+-----------------------------------------------------------------------------------------------+
| GÓC NHÌN LIST VIEW: Phân cụm nhóm theo thời gian                                             |
|                                                                                               |
| ▼ HÔM NAY (1 BÀI TẬP)                                                                         |
| [ ] [#nmttnt-csc10014] Nộp báo cáo Đồ án 1 | Hạn: 23:59 | [Còn 5h 20p] | @Nguyen | [Moodle ↗] |
|                                                                                               |
| ▼ TUẦN NÀY (3 BÀI TẬP)                                                                        |
| [ ] [#ktlt-csc10002] Quiz trắc nghiệm Đệ quy | Hạn: 21:00 24/09 | [Còn 2 ngày] | @Thinh      |
| [ ] [#pttkht-csc10006] Nộp biểu đồ Use Case | Hạn: 23:59 26/09 | [Còn 4 ngày] | @Nhom4       |
|                                                                                               |
| ▼ ĐÃ HOÀN THÀNH (18 BÀI TẬP) - [Ẩn / Hiện]                                                   |
| [x] [Gạch ngang chữ] [#nmttnt] Bài tập lý thuyết Tuần 2 | Hoàn thành bởi @Nguyen lúc 10:15    |
+-----------------------------------------------------------------------------------------------+
```

#### Đặc tả Góc nhìn Kanban Board (3 Cột Auto-Layout):
1. **Cột 1: Cần làm (To-Do - 4 bài):** Thẻ có viền xám, hiển thị ngày hạn chót.
2. **Cột 2: Đang thực hiện / Gấp (In Progress / Urgent - 2 bài):** Thẻ có dải màu đỏ bên trái, đếm ngược thời gian nhấp nháy.
3. **Cột 3: Đã hoàn thành (Done - 18 bài):** Thẻ mờ nhẹ (Opacity 80%), tick xanh lá. Có thể kéo thả (Drag & Drop) card sang cột Done để kích hoạt hoàn tất.

---

## MÀN 3: CHI TIẾT MÔN HỌC & KHO TÀI LIỆU MOODLE
*Mục đích: Quản lý các môn học được đồng bộ từ Moodle, kiểm tra cấu hình channel Discord và truy cập tài liệu tải lên.*

- **Kích thước Frame:** `1440 x 900 px`
- **Layout 2 Panel (Split Screen):**
  - *Panel Trái (Width: 420px):* Danh sách Thẻ Môn học theo từng Category học kỳ.
  - *Panel Phải (Width: 780px, Fill Container):* Không gian chi tiết môn đang chọn.

```
+-----------------------------------------------------------------------------------------------+
| TABS HỌC KỲ: [ ⭐ Học kỳ 1 (2024-2025) ]  [ Học kỳ 2 (2023-2024) ]  [ Kho lưu trữ cũ ]        |
+------------------------------------+----------------------------------------------------------+
| DANH SÁCH MÔN HỌC (420px)          | CHI TIẾT MÔN: NHẬP MÔN TRÍ TUỆ NHÂN TẠO                  |
|                                    | Mã môn: CSC10014 | Kênh Discord: #nmttnt-csc10014        |
| [Card Môn 1 - Đang chọn]           +----------------------------------------------------------+
| - Tên: Nhập môn Trí tuệ Nhân tạo   | 📂 KHO TÀI LIỆU MOODLE ĐÃ ĐỒNG BỘ                        |
| - Mã: CSC10014 | LMS ID: 4149      | (Quét tự động từ Moodle API - Tải trực tiếp)             |
| - Kênh: #nmttnt-csc10014           | -------------------------------------------------------- |
| - Trạng thái: 2 bài tập đang mở    | 📄 [PDF] Slide_Chuong_4_Search_Heuristic.pdf (4.2 MB)    |
|                                    |    Đăng ngày: 18/09/2026 bởi TS. Lê Văn A                |
| [Card Môn 2]                       | 📁 [Folder] Lab_02_Dataset_and_Jupyter_Notebook.zip      |
| - Tên: Kỹ thuật Lập trình          |    Cập nhật: 15/09/2026 bởi Trợ giảng                    |
| - Mã: CSC10002 | LMS ID: 4150      | 🔗 [Link] Trang tra cứu tài liệu tham khảo W3Schools     |
| - Trạng thái: Đã xong hết bài      +----------------------------------------------------------+
|                                    | 📝 DANH SÁCH BÀI TẬP RIÊNG CỦA MÔN                       |
| [Card Môn 3]                       | 1. Bài tập thực hành Tuần 4 (Hạn: 25/09) - [Chưa nộp]    |
| - Tên: Phương pháp Nghiên cứu KH   | 2. Đồ án nhóm giữa kỳ (Hạn: 10/10) - [Đang làm]          |
| - Mã: CSC10011                     +----------------------------------------------------------+
| - Trạng thái: 1 thông báo mới      | 💬 THẢO LUẬN TRÊN DISCORD: 3 threads đang hoạt động ↗    |
+------------------------------------+----------------------------------------------------------+
```

---

## MÀN 4: BẢNG TIN THÔNG BÁO & AI TÓM TẮT (TL;DR)
*Mục đích: Giúp sinh viên đọc nhanh mọi thông báo dài dòng từ giảng viên bằng công nghệ tóm tắt AI Gemini.*

- **Kích thước Frame:** `1440 x 900 px`
- **Layout Feed Dòng Thời Gian (Timeline Feed):** Danh sách dạng luồng dọc ở giữa màn hình (Max-width: `880px` căn giữa).

```
+-----------------------------------------------------------------------------------------------+
| FEED HEADER: [ 📢 Bảng tin Diễn đàn Moodle ]  [ Lọc theo môn học ▼ ]  [ ⚡ Chỉ hiện tin chưa đọc ]|
+-----------------------------------------------------------------------------------------------+
| ITEM THÔNG BÁO 1 (Card Nổi Bật)                                                               |
| 🎓 Môn: [CSC10014] Nhập môn Trí tuệ Nhân tạo | 👤 Giảng viên: TS. Trần Minh C | 🕒 2 giờ trước|
| Tiêu đề gốc: "Thông báo về việc thay đổi lịch phụ đạo và gia hạn bài nộp Lab 2"              |
|                                                                                               |
| ┌── ✨ AI SUMMARY (TL;DR bởi Gemini) ────────────────────────────────────────────────────────┐ |
| │ • Dời hạn nộp Lab 2 thêm 3 ngày: Hạn chót mới là 23:59 Chủ Nhật (27/09).                   │ |
| │ • Lớp phụ đạo chiều Thứ 5 tuần này nghỉ, chuyển sang học bù online tối Thứ 7 lúc 19:30.     │ |
| │ • Sinh viên nhớ mang theo laptop đã cài sẵn Python 3.12 và thư viện NumPy.                 │ |
| └────────────────────────────────────────────────────────────────────────────────────────────┘ |
|                                                                                               |
| [Văn bản gốc từ diễn đàn Moodle - Thu gọn lại ▼]                                             |
| Kính gửi các em sinh viên lớp CSC10014, do tuần này thầy có lịch họp hội đồng khoa học...     |
|                                                                                               |
| [ Nút: Mở bài gốc trên Moodle ↗ ]   [ Nút: Chia sẻ vào Discord Kênh Môn #nmttnt ]             |
+-----------------------------------------------------------------------------------------------+
| ITEM THÔNG BÁO 2 (Card Tiêu Chuẩn)                                                            |
| 🎓 Môn: [LCN_CQ2024/3] Lớp Chủ Nhiệm | 👤 Cố vấn học tập | 🕒 1 ngày trước                     |
| Tiêu đề: "Khảo sát đăng ký chuyên ngành và xét học bổng khuyến khích học tập kỳ 1"            |
|                                                                                               |
| ┌── ✨ AI SUMMARY ───────────────────────────────────────────────────────────────────────────┐ |
| │ • Link khảo sát đóng vào lúc 17:00 ngày 30/09 (bắt buộc toàn bộ sinh viên điền).           │ |
| │ • Điều kiện nộp học bổng: Đạt GPA từ 8.0 trở lên và ĐRL từ 80 điểm.                         │ |
| └────────────────────────────────────────────────────────────────────────────────────────────┘ |
+-----------------------------------------------------------------------------------------------+
```

---

## MÀN 5: CÀI ĐẶT HỆ THỐNG & TÍCH HỢP ĐỒNG BỘ
*Mục đích: Cấu hình chìa khóa API, kiểm tra tình trạng kết nối 3 bên và cưỡng chế đồng bộ tức thời.*

- **Kích thước Frame:** `1440 x 900 px`
- **Layout:** Cột trái điều hướng Tab cài đặt, Cột phải là các Thẻ cấu hình tích hợp.

```
+-----------------------------------------------------------------------------------------------+
| CÀI ĐẶT HỆ THỐNG & ĐỒNG BỘ (SYSTEM & INTEGRATIONS SETTINGS)                                    |
+------------------------------------+----------------------------------------------------------+
| MENU CÀI ĐẶT:                      | THÔNG TIN TRẠNG THÁI TOÀN HỆ THỐNG                       |
| • 🔗 Tích hợp 3 bên (Đang chọn)    | Trạng thái: 🟢 Hoạt động bình thường (All Systems Healthy) |
| • 🎓 Lịch Moodle & Token           | Lần quét gần nhất: 12 phút trước | Cron: Mỗi 30 phút       |
| • 🎨 Giao diện & Cá nhân hóa       | [ Nút: 🔄 Ép buộc Quét Moodle Ngay Lập Tức ]              |
| • 🛡️ Bảo mật & Passkey             +----------------------------------------------------------+
|                                    | 1. DISCORD SERVER & BOT (Đang kết nối ✅)                 |
|                                    | - Server: "K2024 - Khoa CNTT HCMUS" (ID: 149900535...)   |
|                                    | - Kênh theo dõi: 18 kênh môn học đã gán Category         |
|                                    | - Tùy chọn: [x] Tự động tạo Scheduled Events             |
|                                    |             [x] Tự động mở Thread thảo luận cho bài mới  |
|                                    |             [x] Nhắc nhở khẩn cấp trước 24 giờ           |
|                                    +----------------------------------------------------------+
|                                    | 2. GOOGLE CALENDAR (Service Account ✅)                  |
|                                    | - Lịch đồng bộ: fit_hcmus_deadlines@group.calendar...    |
|                                    | - Màu sự kiện: Mặc định Đỏ (Chưa xong) -> Xanh (Đã xong) |
|                                    | - Chuông thông báo: 24 giờ và 3 giờ trước hạn            |
|                                    +----------------------------------------------------------+
|                                    | 3. NOTION WORKSPACE (Connected ✅)                       |
|                                    | - Database: "📚 FIT HCMUS Todo List"                     |
|                                    | - Tự động đồng bộ Checkbox hoàn thành hai chiều          |
+------------------------------------+----------------------------------------------------------+
```

---

# 5. LUỒNG PROTOTYPE & TƯƠNG TÁC VI MÔ

### 5.1. Luồng Tương tác Cốt lõi (Core Prototype Flows)
1. **Luồng Hoàn Thành Deadline (Check-off Flow):**
   - *Trigger:* User bấm vào checkbox trên `DeadlineItemCard` ở Màn 1 hoặc Màn 2.
   - *Micro-interaction:* 
     - Checkbox chuyển từ border xám sang Fill xanh lá `#16A34A` có icon check trắng (Transition: Ease-out 150ms).
     - Tiêu đề deadline chuyển sang màu xám Slate-400 và có hiệu ứng gạch ngang (`line-through`).
     - Bật một Toast Notification ở góc dưới bên phải: `"✅ Đã đánh dấu hoàn thành bài tập. Google Calendar & Notion đã được cập nhật!"` (Tự tắt sau 3s).
     - Tỷ lệ % trên Progress Bar của Banner chính tăng mượt mà (Spring animation).

2. **Luồng Mở Modal Thêm Deadline Mới:**
   - *Trigger:* User bấm nút `+ Thêm Deadline` ở Top Header.
   - *Action:* Mở Frame `AddDeadlineModal` dạng **Overlay**:
     - Background Dim: `rgba(15, 23, 42, 0.45)` kèm `backdrop-filter: blur(4px)`.
     - Vị trí: Căn chính giữa màn hình (Center).
     - Hiệu ứng: Scale in từ `95%` lên `100%`, Opacity từ `0` đến `1` trong `200ms` (Ease-out).

3. **Luồng Chuyển Đổi View (List ↔ Kanban ↔ Calendar):**
   - *Trigger:* Bấm vào Segmented Control ở Toolbar Màn 2.
   - *Action:* Áp dụng **Smart Animate** giữa các Frame (Match các thẻ bài tập có chung ID) với thời lượng `250ms Ease-in-out` để người dùng cảm nhận được vị trí thẻ di chuyển sang cột Kanban tương ứng.

### 5.2. Nguyên tắc Bố cục Auto-Layout Khắt khe trên Figma
- **100% Không dùng Fixed Position** trừ các thành phần nổi (Floating Overlay, Tooltip, Toast, Modal).
- Mọi Card danh sách phải thiết lập thuộc tính `Horizontal Resizing: Fill container` để tự co giãn linh hoạt khi thay đổi độ rộng màn hình.
- Các khoảng cách Padding và Gap luôn luôn là bội số của 4 hoặc 8 (`8px`, `12px`, `16px`, `24px`).
- Text layer luôn bật chế độ `Auto-height` cho tiêu đề bài tập (tránh trường hợp tên bài tập quá dài làm vỡ bố cục dòng).

---
*Tài liệu đặc tả này đã sẵn sàng để Designer khởi tạo Figma File, thiết lập Variables (Color & Number tokens), dựng Auto-Layout Components và đóng gói Design System hoàn chỉnh.*

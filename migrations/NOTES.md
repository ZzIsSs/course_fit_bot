# Ghi chú Migration — PostgreSQL

## Kiểu dữ liệu & Từ khoá

- `SERIAL` = `INT` + `AUTO_INCREMENT` + `NOT NULL` + `PRIMARY KEY`
- `TEXT` = Chuỗi không giới hạn độ dài (khác với `VARCHAR(n)` có giới hạn)
- `JSONB` = JSON dạng nhị phân, truy vấn nhanh hơn `JSON`, hỗ trợ index
- `TIMESTAMP` = Ngày giờ, không kèm timezone (nếu cần timezone thì dùng `TIMESTAMPTZ`)

## Constraint

- `CHECK(col IN ('a', 'b'))` = Giới hạn giá trị cột chỉ được nằm trong danh sách cho trước
- `UNIQUE` = Không cho phép trùng giá trị trong cột
- `DEFAULT NOW()` = Tự động gán thời điểm hiện tại khi INSERT mà không truyền giá trị

## Index

- `CREATE INDEX idx_name ON table (col)` = Tạo index để truy vấn nhanh hơn theo cột
- `CREATE INDEX ... WHERE condition` = Partial Index — chỉ index những dòng thoả điều kiện, tiết kiệm dung lượng

## Lưu ý thiết kế

- Bảng `notifications` dùng **polymorphic reference**: cột `reference_id` trỏ đến `deadlines_id` hoặc `announcements_id` tuỳ theo giá trị cột `type`. Không thể dùng Foreign Key cho kiểu thiết kế này.
- Bảng `courses.chat_id` cho phép `NULL` vì khi bot quét khóa học từ Moodle, channel Discord tương ứng chưa chắc đã được tạo ngay.

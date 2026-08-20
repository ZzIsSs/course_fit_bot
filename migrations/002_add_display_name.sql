-- Thêm cột display_name để lưu tên tiếng Việt đầy đủ của môn học.
-- Ví dụ: course_name = 'CSC10014', display_name = 'Nhập Môn Trí Tuệ Nhân Tạo'

ALTER TABLE courses ADD COLUMN IF NOT EXISTS display_name varchar(255);

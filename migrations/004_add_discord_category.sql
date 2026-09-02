-- Lưu Category ID (kì học) trên Discord mà môn học này nên được xếp vào khi
-- bot tạo channel mới. NULL = tạo ở gốc như hành vi cũ (không phá gì cả).
ALTER TABLE courses ADD COLUMN IF NOT EXISTS discord_category_id varchar(50);

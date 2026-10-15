"""Repository cho nội dung Moodle: course_modules, forum_discussions, announcements.

Mỗi hàm nhận conn (connection) làm tham số đầu tiên.
"""
from datetime import datetime, timezone

from course_bot.db.connection import execute, fetch_one, fetch_all


def get_known_modules_for_course(conn, courses_id):
    """Lấy modules đã biết của một khóa học.

    Returns: dict { lms_module_id: time_modified_unix_timestamp }
    """
    rows = fetch_all(conn,
        "SELECT lms_module_id, time_modified FROM course_modules WHERE courses_id = %s",
        (courses_id,))
    result = {}
    for row in rows:
        ts = row['time_modified']
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            result[row['lms_module_id']] = int(ts.timestamp())
        else:
            result[row['lms_module_id']] = int(ts) if ts else 0
    return result


def upsert_module(conn, courses_id, lms_module_id, module_type, module_name, time_modified):
    """Thêm hoặc cập nhật module. Dùng ON CONFLICT để upsert."""
    # Chuyển unix timestamp sang datetime nếu cần
    if isinstance(time_modified, (int, float)):
        time_modified = datetime.fromtimestamp(time_modified, tz=timezone.utc) if time_modified else None

    execute(conn,
        """INSERT INTO course_modules (courses_id, lms_module_id, module_type, module_name, time_modified)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (courses_id, lms_module_id) DO UPDATE SET
               module_name = EXCLUDED.module_name,
               time_modified = EXCLUDED.time_modified""",
        (courses_id, lms_module_id, module_type, module_name, time_modified))


def has_modules(conn):
    """Kiểm tra đã có dữ liệu modules chưa (xác định lần chạy đầu tiên)."""
    row = fetch_one(conn, "SELECT EXISTS(SELECT 1 FROM course_modules) AS has_data")
    return row['has_data'] if row else False


def get_known_discussion_ids(conn):
    """Lấy tất cả discussion IDs đã biết.

    Returns: set of lms_discussion_id strings.
    """
    rows = fetch_all(conn, "SELECT lms_discussion_id FROM forum_discussions")
    return {row['lms_discussion_id'] for row in rows}


def insert_discussion(conn, courses_id, lms_discussion_id, forum_name=None, subject=None, author=None):
    """Thêm discussion mới (bỏ qua nếu đã tồn tại)."""
    execute(conn,
        """INSERT INTO forum_discussions (courses_id, lms_discussion_id, forum_name, subject, author)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (lms_discussion_id) DO NOTHING""",
        (courses_id, lms_discussion_id, forum_name, subject, author))


def get_recent_announcements_with_course(conn, limit=20):
    """Lấy danh sách thông báo môn học gần nhất."""
    return fetch_all(conn,
        """SELECT a.announcements_id, a.courses_id, a.announcements_name, a.created_time, a.source_url,
                  c.course_name, c.display_name AS course_display_name
           FROM announcements a
           JOIN courses c ON a.courses_id = c.courses_id
           ORDER BY a.created_time DESC
           LIMIT %s""",
        (limit,))

"""Database queries for the notification bot.

Tập trung toàn bộ câu SQL vào một file duy nhất.
Mỗi hàm nhận conn (connection) làm tham số đầu tiên.
"""
import json
import logging
from datetime import datetime, timezone

from src.database import execute, fetch_one, fetch_all


# ==================== COURSES ====================

def get_or_create_course(conn, course_name, lms_courses_id=None, display_name=None):
    """Tìm hoặc tạo khóa học theo tên (subject code).

    Ưu tiên tìm theo course_name. Nếu có lms_courses_id mới thì cập nhật.
    Nếu có display_name thì cập nhật tên hiển thị tiếng Việt.
    Returns: courses_id (int)
    """
    # Tìm theo tên môn (subject code)
    row = fetch_one(conn,
        "SELECT courses_id, lms_courses_id, display_name FROM courses WHERE course_name = %s",
        (course_name,))

    if row:
        # Cập nhật lms_courses_id nếu có giá trị thực từ Moodle API
        updates = []
        params = []
        if lms_courses_id and str(lms_courses_id) != row.get('lms_courses_id'):
            updates.append("lms_courses_id = %s")
            params.append(str(lms_courses_id))
        if display_name and display_name != row.get('display_name'):
            updates.append("display_name = %s")
            params.append(display_name)
        if updates:
            params.append(row['courses_id'])
            execute(conn,
                f"UPDATE courses SET {', '.join(updates)} WHERE courses_id = %s",
                tuple(params))
        return row['courses_id']

    # Tạo mới — dùng subject code làm lms_courses_id tạm nếu chưa có
    effective_lms_id = str(lms_courses_id) if lms_courses_id else course_name
    row = fetch_one(conn,
        """INSERT INTO courses (course_name, lms_courses_id, display_name)
           VALUES (%s, %s, %s)
           ON CONFLICT (course_name) DO UPDATE SET course_name = EXCLUDED.course_name
           RETURNING courses_id""",
        (course_name, effective_lms_id, display_name))
    return row['courses_id']


def update_course_chat_id(conn, courses_id, chat_id):
    """Cập nhật Discord channel ID cho khóa học."""
    execute(conn,
        "UPDATE courses SET chat_id = %s WHERE courses_id = %s",
        (chat_id, courses_id))


def update_course_crawl_time(conn, courses_id):
    """Đánh dấu thời điểm crawl gần nhất."""
    execute(conn,
        "UPDATE courses SET last_crawled_time = now() WHERE courses_id = %s",
        (courses_id,))


def get_all_courses(conn):
    """Lấy toàn bộ courses (phục vụ sync kênh).

    Returns: list of dicts chứa courses_id, course_name, display_name, chat_id, lms_courses_id.
    """
    return fetch_all(conn,
        "SELECT courses_id, course_name, display_name, chat_id, lms_courses_id FROM courses")


def get_course_display_name(conn, course_name):
    """Lấy display_name của một course theo course_name (subject code).

    Returns: display_name (str) hoặc None.
    """
    row = fetch_one(conn,
        "SELECT display_name FROM courses WHERE course_name = %s",
        (course_name,))
    return row['display_name'] if row else None


def get_course_discord_category(conn, course_name):
    """Lấy Category ID đã gán cho môn học — dùng khi tạo channel mới.
    Trả về None nếu chưa gán (bot sẽ tạo ở gốc như hành vi cũ)."""
    row = fetch_one(conn,
        "SELECT discord_category_id FROM courses WHERE course_name = %s",
        (course_name,))
    return row['discord_category_id'] if row else None


def set_course_discord_category(conn, course_name, category_id):
    """Gán/ghi nhận Category ID cho môn học."""
    execute(conn,
        "UPDATE courses SET discord_category_id = %s WHERE course_name = %s",
        (category_id, course_name))


# ==================== DEADLINES ====================

def get_deadline_by_lms_id(conn, lms_deadlines_id):
    """Tìm deadline theo LMS ID (ICS UID).

    Returns: dict chứa deadline + course_name, hoặc None.
    """
    return fetch_one(conn,
        """SELECT d.*, c.course_name
           FROM deadlines d
           JOIN courses c ON d.courses_id = c.courses_id
           WHERE d.lms_deadlines_id = %s""",
        (lms_deadlines_id,))


def get_tracked_deadlines(conn):
    """Lấy các deadline chưa completed và đang theo dõi reaction (có message_id)."""
    return fetch_all(conn,
        """SELECT d.*, c.course_name
           FROM deadlines d
           JOIN courses c ON d.courses_id = c.courses_id
           WHERE d.completed = false AND d.discord_message_id IS NOT NULL""")


def get_all_deadlines_with_course(conn):
    """Lấy tất cả deadline kèm thông tin khóa học (cho summary/progress)."""
    return fetch_all(conn,
        """SELECT d.*, c.course_name
           FROM deadlines d
           JOIN courses c ON d.courses_id = c.courses_id
           ORDER BY d.due_time""")


def insert_deadline(conn, courses_id, deadline_name, lms_deadlines_id, due_time, source_url):
    """Thêm deadline mới.

    Returns: deadlines_id (int)
    """
    row = fetch_one(conn,
        """INSERT INTO deadlines (courses_id, deadline_name, lms_deadlines_id, due_time, source_url)
           VALUES (%s, %s, %s, %s, %s)
           RETURNING deadlines_id""",
        (courses_id, deadline_name, lms_deadlines_id, due_time, source_url))
    return row['deadlines_id']


def update_deadline_notified(conn, deadlines_id, field):
    """Đánh dấu đã gửi thông báo.

    Args:
        field: 'notified_new', 'reminded_3d', hoặc 'reminded_1d'
    """
    allowed = ('notified_new', 'reminded_3d', 'reminded_1d')
    if field not in allowed:
        raise ValueError(f"Invalid field: {field}. Must be one of {allowed}")
    execute(conn,
        f"UPDATE deadlines SET {field} = true WHERE deadlines_id = %s",
        (deadlines_id,))


def update_deadline_discord_info(conn, deadlines_id, message_id, channel_id, event_id=None):
    """Cập nhật Discord message/channel/event ID cho deadline."""
    execute(conn,
        """UPDATE deadlines
           SET discord_message_id = %s, discord_channel_id = %s, discord_event_id = %s
           WHERE deadlines_id = %s""",
        (message_id, channel_id, event_id, deadlines_id))


def mark_deadline_completed(conn, deadlines_id, completed_by):
    """Đánh dấu deadline đã hoàn thành."""
    execute(conn,
        "UPDATE deadlines SET completed = true, completed_by = %s WHERE deadlines_id = %s",
        (completed_by, deadlines_id))


def get_pending_manual_deadlines(conn):
    """Deadline thêm qua /add_deadline, chưa từng được cron xử lý lần đầu."""
    return fetch_all(conn,
        """SELECT d.*, c.course_name
           FROM deadlines d
           JOIN courses c ON d.courses_id = c.courses_id
           WHERE d.source = 'manual' AND d.notified_new = false""")


def insert_deadline_manual(conn, courses_id, deadline_name, lms_deadlines_id, due_time, source_url, added_by):
    """ON CONFLICT DO NOTHING: an toàn nếu Discord gửi lặp interaction (retry)."""
    row = fetch_one(conn,
        """INSERT INTO deadlines (courses_id, deadline_name, lms_deadlines_id, due_time, source_url, source, added_by)
           VALUES (%s, %s, %s, %s, %s, 'manual', %s)
           ON CONFLICT (lms_deadlines_id) DO NOTHING
           RETURNING deadlines_id""",
        (courses_id, deadline_name, lms_deadlines_id, due_time, source_url, added_by))
    return row['deadlines_id'] if row else None


def get_course_name_by_chat_id(conn, chat_id):
    """Tự nhận diện môn học dựa vào kênh đang gõ lệnh — khỏi cần gõ mã môn."""
    row = fetch_one(conn, "SELECT course_name FROM courses WHERE chat_id = %s", (str(chat_id),))
    return row['course_name'] if row else None


def get_deadlines_for_course_or_all(conn, course_name=None):
    """Lấy deadline kèm course_name, lọc theo môn nếu có.
    Việc lọc theo thời gian/đã hoàn thành thực hiện ở Python
    để nhất quán với phần còn lại của code, tránh lệch timezone.
    """
    if course_name:
        return fetch_all(conn,
            """SELECT d.*, c.course_name
               FROM deadlines d
               JOIN courses c ON d.courses_id = c.courses_id
               WHERE c.course_name = %s
               ORDER BY d.due_time""",
            (course_name,))
    return get_all_deadlines_with_course(conn)


# ==================== COURSE MODULES ====================

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


# ==================== FORUM DISCUSSIONS ====================

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


# ==================== NOTIFICATIONS ====================

def insert_notification(conn, notif_type, message, reference_id):
    """Ghi lại thông báo đã gửi vào lịch sử."""
    execute(conn,
        """INSERT INTO notifications (type, message, sent_at, reference_id)
           VALUES (%s, %s, now(), %s)""",
        (notif_type, message, reference_id))


# ==================== ERROR LOGS ====================

def insert_error_log(conn, source, error_message, severity='error', command=None,
                     reference_type=None, reference_id=None, error_detail=None, context=None):
    """Ghi log lỗi vào database."""
    execute(conn,
        """INSERT INTO error_logs (source, severity, command, reference_type, reference_id,
                                   error_message, error_detail, context)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (source, severity, command, reference_type, reference_id,
         error_message, error_detail, json.dumps(context) if context else None))

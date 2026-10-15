"""Repository cho bảng deadlines.

Mỗi hàm nhận conn (connection) làm tham số đầu tiên.
"""
import logging

from course_bot.db.connection import execute, fetch_one, fetch_all


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
    """Lấy các deadline chưa completed và đang theo dõi reaction (có message_id).

    Bỏ qua deadline đã quá hạn hơn 3 ngày: mỗi deadline tốn 1 request Discord
    (lấy reactions), nên nếu giữ mãi deadline cũ thì số request tăng dần và
    dễ chạm rate limit.
    """
    return fetch_all(conn,
        """SELECT d.*, c.course_name
           FROM deadlines d
           JOIN courses c ON d.courses_id = c.courses_id
           WHERE d.completed = false AND d.discord_message_id IS NOT NULL
             AND d.due_time >= now() - interval '3 days'""")


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
    """Deadline thêm thủ công (Discord /add_deadline hoặc API bên thứ 3),
    chưa từng được cron xử lý lần đầu."""
    return fetch_all(conn,
        """SELECT d.*, c.course_name
           FROM deadlines d
           JOIN courses c ON d.courses_id = c.courses_id
           WHERE d.source != 'moodle' AND d.notified_new = false""")


def insert_deadline_manual(conn, courses_id, deadline_name, lms_deadlines_id, due_time, source_url, added_by, source='manual'):
    """Thêm deadline thủ công kèm cơ chế chống trùng lặp nghiệp vụ (Business Idempotency).

    Chống trùng lặp kép:
    1. Kiểm tra nếu cùng môn học đã tồn tại bài tập cùng tên (case-insensitive) và cùng hạn chót.
    2. Sử dụng ON CONFLICT (lms_deadlines_id) DO NOTHING để chống retry từ Discord/client.
    Cắt chuỗi an toàn theo schema để tránh StringDataRightTruncation.

    Returns:
        deadlines_id (int) nếu tạo mới thành công, None nếu là bản ghi trùng lặp.
    """
    clean_name = " ".join((deadline_name or '').strip().split())[:250]
    clean_url = (source_url or '').strip()[:500]
    clean_added_by = (added_by or '').strip()[:95]
    clean_lms_id = (lms_deadlines_id or '').strip()[:50]
    clean_source = (source or 'manual').strip()[:20]

    # Kiểm tra trùng lặp mức nghiệp vụ: cùng môn, cùng tên bài (case-insensitive), cùng hạn chót
    existing = fetch_one(conn,
        """SELECT deadlines_id FROM deadlines
           WHERE courses_id = %s AND LOWER(deadline_name) = LOWER(%s) AND due_time = %s
           LIMIT 1""",
        (courses_id, clean_name, due_time))
    if existing:
        logging.info("Bỏ qua deadline trùng nghiệp vụ: '%s' (ID: %s)", clean_name, existing['deadlines_id'])
        return None

    row = fetch_one(conn,
        """INSERT INTO deadlines (courses_id, deadline_name, lms_deadlines_id, due_time, source_url, source, added_by)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (lms_deadlines_id) DO NOTHING
           RETURNING deadlines_id""",
        (courses_id, clean_name, clean_lms_id, due_time, clean_url, clean_source, clean_added_by))
    return row['deadlines_id'] if row else None


def upsert_deadline_from_api(conn, courses_id, deadline_name, lms_deadlines_id, due_time, source_url, source='moodle_api'):
    """Upsert deadline thu thập từ Moodle REST API (assign/quiz).

    Khác với insert_deadline thường:
    - Dùng ON CONFLICT để CẬP NHẬT due_time nếu giảng viên thay đổi hạn chót.
    - Không tạo trùng nếu ICS đã có cùng assignment/quiz (kiểm tra cả tên + môn).
    - Trả về ('inserted' | 'updated' | 'skipped', deadlines_id | None).

    Returns:
        Tuple (action, deadlines_id):
            - ('inserted', id) khi tạo mới
            - ('updated', id) khi cập nhật due_time
            - ('skipped', None) khi đã tồn tại và không thay đổi gì
    """
    clean_name = " ".join((deadline_name or '').strip().split())[:250]
    clean_url = (source_url or '').strip()[:500]
    clean_lms_id = (lms_deadlines_id or '').strip()[:50]
    clean_source = (source or 'moodle_api').strip()[:20]

    # Kiểm tra đã tồn tại theo lms_deadlines_id chưa
    existing = fetch_one(conn,
        """SELECT deadlines_id, due_time, source FROM deadlines
           WHERE lms_deadlines_id = %s
           LIMIT 1""",
        (clean_lms_id,))

    if existing:
        # Đã tồn tại — kiểm tra xem due_time có thay đổi không
        from course_bot.core.time_utils import ensure_tz
        old_due = ensure_tz(existing['due_time'])
        new_due = ensure_tz(due_time) if due_time else None

        if new_due and abs((new_due - old_due).total_seconds()) > 60:
            # GV đổi hạn chót → cập nhật
            execute(conn,
                """UPDATE deadlines SET due_time = %s, deadline_name = %s,
                   source_url = %s, reminded_3d = false, reminded_1d = false
                   WHERE deadlines_id = %s""",
                (new_due, clean_name, clean_url, existing['deadlines_id']))
            logging.info("Cập nhật due_time cho deadline '%s' (ID: %s)", clean_name, existing['deadlines_id'])
            return ('updated', existing['deadlines_id'])
        return ('skipped', existing['deadlines_id'])

    # Kiểm tra trùng lặp mức nghiệp vụ: cùng môn, cùng tên (case-insensitive), cùng hạn chót
    # Có thể ICS đã tạo deadline này trước → không tạo lại
    biz_existing = fetch_one(conn,
        """SELECT deadlines_id FROM deadlines
           WHERE courses_id = %s AND LOWER(deadline_name) = LOWER(%s) AND due_time = %s
           LIMIT 1""",
        (courses_id, clean_name, due_time))
    if biz_existing:
        logging.info("Deadline '%s' đã tồn tại từ nguồn khác (ID: %s), bỏ qua.", clean_name, biz_existing['deadlines_id'])
        return ('skipped', biz_existing['deadlines_id'])

    # Tạo mới
    row = fetch_one(conn,
        """INSERT INTO deadlines (courses_id, deadline_name, lms_deadlines_id, due_time, source_url, source)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (lms_deadlines_id) DO NOTHING
           RETURNING deadlines_id""",
        (courses_id, clean_name, clean_lms_id, due_time, clean_url, clean_source))

    if row:
        logging.info("Tạo deadline mới từ API: '%s' (ID: %s)", clean_name, row['deadlines_id'])
        return ('inserted', row['deadlines_id'])
    return ('skipped', None)


def get_api_deadlines_for_auto_complete(conn):
    """Lấy các deadline từ Moodle API (assign) chưa completed, để kiểm tra trạng thái nộp bài."""
    return fetch_all(conn,
        """SELECT d.deadlines_id, d.lms_deadlines_id, d.deadline_name, c.course_name
           FROM deadlines d
           JOIN courses c ON d.courses_id = c.courses_id
           WHERE d.completed = false
             AND d.lms_deadlines_id LIKE 'moodle-assign-%%'
             AND d.due_time >= now() - interval '7 days'""")


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


def toggle_deadline_completed(conn, deadlines_id, completed, completed_by=None):
    """Đánh dấu hoặc bỏ đánh dấu hoàn thành deadline."""
    execute(conn,
        """UPDATE deadlines
           SET completed = %s, completed_by = %s
           WHERE deadlines_id = %s""",
        (completed, completed_by if completed else None, deadlines_id))


def get_dashboard_stats(conn):
    """Tính toán thống kê tổng thể cho Dashboard."""
    row = fetch_one(conn,
        """SELECT
            COUNT(*)::int AS total_deadlines,
            COUNT(*) FILTER (WHERE completed = true)::int AS completed_deadlines,
            COUNT(*) FILTER (WHERE completed = false)::int AS pending_deadlines,
            COUNT(*) FILTER (WHERE completed = false AND due_time <= now() + interval '24 hours' AND due_time >= now() - interval '1 day')::int AS urgent_24h,
            COUNT(*) FILTER (WHERE completed = false AND due_time <= now() + interval '3 days' AND due_time > now() + interval '24 hours')::int AS upcoming_3d,
            COUNT(*) FILTER (WHERE completed = false AND due_time < now())::int AS overdue
           FROM deadlines""")

    course_row = fetch_one(conn, "SELECT COUNT(*)::int AS total_courses FROM courses")

    total = row['total_deadlines'] if row else 0
    completed = row['completed_deadlines'] if row else 0
    rate = round((completed / total * 100), 1) if total > 0 else 0.0

    return {
        "total_deadlines": total,
        "completed_deadlines": completed,
        "pending_deadlines": row['pending_deadlines'] if row else 0,
        "completion_rate": rate,
        "urgent_24h": row['urgent_24h'] if row else 0,
        "upcoming_3d": row['upcoming_3d'] if row else 0,
        "overdue": row['overdue'] if row else 0,
        "total_courses": course_row['total_courses'] if course_row else 0,
    }


def get_all_deadlines_with_course_details(conn, course_name=None):
    """Lấy danh sách deadlines kèm tên hiển thị môn học."""
    if course_name:
        return fetch_all(conn,
            """SELECT d.*, c.course_name, c.display_name AS course_display_name
               FROM deadlines d
               JOIN courses c ON d.courses_id = c.courses_id
               WHERE c.course_name = %s
               ORDER BY d.due_time ASC""",
            (course_name,))
    return fetch_all(conn,
        """SELECT d.*, c.course_name, c.display_name AS course_display_name
           FROM deadlines d
           JOIN courses c ON d.courses_id = c.courses_id
           ORDER BY d.due_time ASC""")

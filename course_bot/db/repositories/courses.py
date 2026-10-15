"""Repository cho bảng courses.

Mỗi hàm nhận conn (connection) làm tham số đầu tiên.
"""
from course_bot.db.connection import execute, fetch_one, fetch_all


def get_or_create_course(conn, course_name, lms_courses_id=None, display_name=None):
    """Tìm hoặc tạo khóa học theo tên (subject code).

    Ưu tiên tìm theo course_name. Nếu có lms_courses_id mới thì cập nhật.
    Nếu có display_name thì cập nhật tên hiển thị tiếng Việt.
    Returns: courses_id (int)
    """
    clean_course_name = (course_name or '').strip().upper()[:250]
    clean_display_name = display_name.strip()[:250] if display_name else None
    clean_lms_id = str(lms_courses_id).strip()[:50] if lms_courses_id else None

    # Tìm theo tên môn (subject code)
    row = fetch_one(conn,
        "SELECT courses_id, lms_courses_id, display_name FROM courses WHERE course_name = %s",
        (clean_course_name,))

    if row:
        # Cập nhật lms_courses_id nếu có giá trị thực từ Moodle API
        updates = []
        params = []
        if clean_lms_id and clean_lms_id != row.get('lms_courses_id'):
            updates.append("lms_courses_id = %s")
            params.append(clean_lms_id)
        if clean_display_name and clean_display_name != row.get('display_name'):
            updates.append("display_name = %s")
            params.append(clean_display_name)
        if updates:
            params.append(row['courses_id'])
            execute(conn,
                f"UPDATE courses SET {', '.join(updates)} WHERE courses_id = %s",
                tuple(params))
        return row['courses_id']

    # Tạo mới — dùng subject code làm lms_courses_id tạm nếu chưa có
    effective_lms_id = clean_lms_id if clean_lms_id else clean_course_name[:50]
    row = fetch_one(conn,
        """INSERT INTO courses (course_name, lms_courses_id, display_name)
           VALUES (%s, %s, %s)
           ON CONFLICT (course_name) DO UPDATE SET course_name = EXCLUDED.course_name
           RETURNING courses_id""",
        (clean_course_name, effective_lms_id, clean_display_name))
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


def get_course_name_by_chat_id(conn, chat_id):
    """Tự nhận diện môn học dựa vào kênh đang gõ lệnh — khỏi cần gõ mã môn."""
    row = fetch_one(conn, "SELECT course_name FROM courses WHERE chat_id = %s", (str(chat_id),))
    return row['course_name'] if row else None


def get_courses_with_deadline_counts(conn):
    """Lấy danh sách khóa học kèm số lượng deadline chưa hoàn thành."""
    return fetch_all(conn,
        """SELECT c.courses_id, c.course_name, c.display_name, c.lms_courses_id, c.chat_id, c.discord_category_id,
                  COUNT(d.deadlines_id) FILTER (WHERE d.completed = false AND d.due_time >= now() - interval '1 day') AS pending_deadlines_count
           FROM courses c
           LEFT JOIN deadlines d ON c.courses_id = d.courses_id
           GROUP BY c.courses_id, c.course_name, c.display_name, c.lms_courses_id, c.chat_id, c.discord_category_id
           ORDER BY c.course_name""")

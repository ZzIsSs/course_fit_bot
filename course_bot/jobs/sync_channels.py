"""Job --sync-channels: đồng bộ kênh Discord theo khóa học Moodle."""
import logging

from course_bot.core.config import load_env
from course_bot.db.connection import get_db
from course_bot.db.repositories.courses import get_or_create_course, update_course_chat_id
from course_bot.integrations.discord.rest import get_guild_channels
from course_bot.domain.course_naming import slugify_channel_name, extract_display_name, extract_subject
from course_bot.domain.semester import extract_semester_index
from course_bot.integrations.moodle.webservice import get_site_info, get_enrolled_courses
from course_bot.services.channel_resolver import resolve_course_channel, EXISTED, RENAMED, CREATED


# ==================== ĐỒNG BỘ KÊNH DISCORD ====================

def sync_channels():
    """Đồng bộ kênh Discord từ danh sách môn học trên Moodle.

    Luồng xử lý:
    1. Gọi Moodle API lấy danh sách tất cả môn đang học.
    2. Trích mã môn + tên tiếng Việt, lưu vào DB (display_name).
    3. Tạo kênh Discord mới hoặc rename kênh cũ theo format: viết-tắt-mã-môn
       (ví dụ: nmttnt-csc10014).
    """
    env = load_env()
    if not env:
        return

    moodle_token = env.get('moodle_token')
    if not moodle_token:
        logging.error("MOODLE_TOKEN chưa được thiết lập. Không thể đồng bộ kênh.")
        return

    bot_token = env['bot_token']
    guild_id = env['guild_id']
    database_url = env['database_url']

    # === Bước 1: Xác thực Moodle ===
    site_info = get_site_info(moodle_token)
    if not site_info or 'userid' not in site_info:
        logging.error("Không thể xác thực Moodle token.")
        return

    userid = site_info['userid']
    logging.info(f"Moodle: Đã xác thực — {site_info.get('fullname', '?')} (ID: {userid})")

    # === Bước 2: Lấy danh sách môn học ===
    courses = get_enrolled_courses(moodle_token, userid)
    if not courses:
        logging.warning("Moodle: Không tìm thấy khóa học nào.")
        return

    logging.info(f"Moodle: Tìm thấy {len(courses)} khóa học.")

    # === Bước 3: Lấy danh sách kênh Discord hiện tại ===
    discord_channels = get_guild_channels(bot_token, guild_id)
    # Map: channel_name → channel_id (chỉ text channels)
    channel_map = {c['name']: c['id'] for c in discord_channels if c.get('type') == 0}
    category_map = {c['name']: c['id'] for c in discord_channels if c.get('type') == 4}
    # Map: channel_id → channel_name (để tra ngược)
    channel_id_to_name = {c['id']: c['name'] for c in discord_channels if c.get('type') == 0}

    stats = {'created': 0, 'renamed': 0, 'existed': 0, 'skipped': 0}

    with get_db(database_url) as conn:
        for course in courses:
            course_id = course['id']
            shortname = course.get('shortname', '')
            fullname = course.get('fullname', shortname)

            # Trích mã môn + tên tiếng Việt
            subject_code = extract_subject(shortname)
            display_name = extract_display_name(fullname)

            if not subject_code or subject_code == 'General':
                logging.debug(f"Bỏ qua khóa học không rõ mã: {fullname}")
                stats['skipped'] += 1
                continue

            # Cập nhật DB (tạo mới hoặc cập nhật display_name)
            db_course_id = get_or_create_course(
                conn, subject_code, lms_courses_id=course_id, display_name=display_name
            )

            # Kênh theo format viết-tắt-mã-môn: dùng lại, rename kênh cũ, hoặc tạo mới
            channel_id, outcome = resolve_course_channel(
                bot_token, guild_id, conn, channel_map, category_map,
                subject_code, display_name, extract_semester_index(shortname),
            )

            if outcome == EXISTED:
                logging.info(f"Kênh #{slugify_channel_name(subject_code, display_name)} đã tồn tại.")
            if outcome in (EXISTED, RENAMED, CREATED):
                # Đảm bảo chat_id trong DB đúng
                update_course_chat_id(conn, db_course_id, channel_id)
                stats[outcome] += 1
            else:
                stats['skipped'] += 1

    logging.info(
        f"Đồng bộ kênh hoàn tất: "
        f"{stats['created']} tạo mới, {stats['renamed']} rename, "
        f"{stats['existed']} đã tồn tại, {stats['skipped']} bỏ qua."
    )

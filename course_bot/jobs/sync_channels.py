"""Job --sync-channels: đồng bộ kênh Discord theo khóa học Moodle."""
import logging

from course_bot.core.config import load_env
from course_bot.db.connection import get_db
from course_bot.db.repositories.courses import (
    get_or_create_course,
    update_course_chat_id,
    get_course_discord_category,
    set_course_discord_category,
)
from course_bot.integrations.discord.rest import (
    get_guild_channels,
    create_channel,
    rename_channel,
    resolve_category,
)
from course_bot.domain.course_naming import slugify_channel_name, extract_display_name, extract_subject
from course_bot.domain.semester import extract_semester_index
from course_bot.integrations.moodle.webservice import get_site_info, get_enrolled_courses


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

            # Tên kênh mới theo format viết-tắt-mã-môn
            new_chan_name = slugify_channel_name(subject_code, display_name)
            # Tên kênh cũ (chỉ mã môn, không có viết tắt)
            old_chan_name = slugify_channel_name(subject_code)

            if new_chan_name in channel_map:
                # Kênh đã tồn tại với tên đúng format
                logging.info(f"Kênh #{new_chan_name} đã tồn tại.")
                # Đảm bảo chat_id trong DB đúng
                update_course_chat_id(conn, db_course_id, channel_map[new_chan_name])
                stats['existed'] += 1

            elif old_chan_name in channel_map and old_chan_name != new_chan_name:
                # Kênh cũ tồn tại với tên ngắn → rename
                old_chan_id = channel_map[old_chan_name]
                result = rename_channel(bot_token, old_chan_id, new_chan_name)
                if result:
                    # Cập nhật channel_map
                    channel_map[new_chan_name] = old_chan_id
                    del channel_map[old_chan_name]
                    update_course_chat_id(conn, db_course_id, old_chan_id)
                    logging.info(f"Đã rename #{old_chan_name} → #{new_chan_name}")
                    stats['renamed'] += 1
                else:
                    stats['skipped'] += 1

            else:
                # Tạo kênh mới
                ky = extract_semester_index(shortname)
                if ky is not None:
                    category_id = resolve_category(bot_token, guild_id, category_map, f"kì {ky}")
                else:
                    category_id = get_course_discord_category(conn, subject_code)

                new_channel = create_channel(bot_token, guild_id, new_chan_name, parent_id=category_id)
                if new_channel:
                    channel_map[new_chan_name] = new_channel['id']
                    update_course_chat_id(conn, db_course_id, new_channel['id'])
                    if category_id:
                        set_course_discord_category(conn, subject_code, category_id)
                    stats['created'] += 1
                else:
                    stats['skipped'] += 1

    logging.info(
        f"Đồng bộ kênh hoàn tất: "
        f"{stats['created']} tạo mới, {stats['renamed']} rename, "
        f"{stats['existed']} đã tồn tại, {stats['skipped']} bỏ qua."
    )

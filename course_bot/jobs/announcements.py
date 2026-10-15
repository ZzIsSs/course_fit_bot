"""Job --announcements: kiểm tra nội dung Moodle mới (logic ở services/announcement_tracker.py)."""
import logging

from course_bot.core.config import load_env
from course_bot.db.connection import get_db
from course_bot.services.announcement_tracker import check_moodle_updates


# ==================== KIỂM TRA THÔNG BÁO MOODLE ====================

def check_announcements():
    """Kiểm tra thông báo Moodle độc lập (dùng cho debug/test)."""
    env = load_env()
    if not env:
        return

    moodle_token = env.get('moodle_token')
    if not moodle_token:
        logging.error("MOODLE_TOKEN chưa được thiết lập. Không thể kiểm tra thông báo Moodle.")
        return

    bot_token = env['bot_token']
    guild_id = env['guild_id']
    database_url = env['database_url']

    with get_db(database_url) as conn:
        check_moodle_updates(bot_token, guild_id, moodle_token, conn)

    logging.info("Moodle announcement check completed.")

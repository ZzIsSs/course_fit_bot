import os
import logging
from datetime import timezone, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==================== HẰNG SỐ ====================

DISCORD_API_BASE = "https://discord.com/api/v10"
LOCAL_TZ = timezone(timedelta(hours=7))

# ==================== BIẾN MÔI TRƯỜNG ====================

def load_env():
    """Đọc và kiểm tra các biến môi trường cần thiết.
    Trả về dict chứa các giá trị, hoặc None nếu thiếu biến.

    Biến bắt buộc: MOODLE_CALENDAR_URL, DISCORD_BOT_TOKEN, DISCORD_SERVER_ID, DATABASE_URL
    Biến tùy chọn: MOODLE_TOKEN (bật tính năng theo dõi thông báo Moodle)
    """
    calendar_url = os.environ.get('MOODLE_CALENDAR_URL')
    bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    guild_id = os.environ.get('DISCORD_SERVER_ID')
    database_url = os.environ.get('DATABASE_URL')
    moodle_token = os.environ.get('MOODLE_TOKEN')

    if not all([calendar_url, bot_token, guild_id, database_url]):
        logging.error(
            "Missing environment variables: "
            "MOODLE_CALENDAR_URL, DISCORD_BOT_TOKEN, DISCORD_SERVER_ID, or DATABASE_URL"
        )
        return None

    if moodle_token:
        logging.info("MOODLE_TOKEN detected — Moodle announcement tracking enabled.")
    else:
        logging.info("MOODLE_TOKEN not set — Moodle announcement tracking disabled.")

    return {
        'calendar_url': calendar_url,
        'bot_token': bot_token,
        'guild_id': guild_id,
        'database_url': database_url,
        'moodle_token': moodle_token,
    }

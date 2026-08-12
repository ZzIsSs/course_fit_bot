import os
import logging
from datetime import timezone, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==================== HẰNG SỐ ====================

DISCORD_API_BASE = "https://discord.com/api/v10"
LOCAL_TZ = timezone(timedelta(hours=7))
STATE_FILE = 'data/state.json'

# ==================== BIẾN MÔI TRƯỜNG ====================

def load_env():
    """Đọc và kiểm tra các biến môi trường cần thiết.
    Trả về dict chứa các giá trị, hoặc None nếu thiếu biến.
    """
    calendar_url = os.environ.get('MOODLE_CALENDAR_URL')
    bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    guild_id = os.environ.get('DISCORD_SERVER_ID')

    if not all([calendar_url, bot_token, guild_id]):
        logging.error("Missing environment variables: MOODLE_CALENDAR_URL, DISCORD_BOT_TOKEN, or DISCORD_SERVER_ID")
        return None

    return {
        'calendar_url': calendar_url,
        'bot_token': bot_token,
        'guild_id': guild_id
    }

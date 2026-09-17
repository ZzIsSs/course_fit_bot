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
    Hỗ trợ đọc từ file .env cục bộ nếu có.
    Biến bắt buộc: MOODLE_CALENDAR_URL, DISCORD_BOT_TOKEN, DISCORD_SERVER_ID, DATABASE_URL
    Biến tùy chọn: MOODLE_TOKEN (bật tính năng theo dõi thông báo Moodle)
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # Nếu không cài python-dotenv hoặc chạy trên GitHub Actions thì bỏ qua
    calendar_url = os.environ.get('MOODLE_CALENDAR_URL')
    bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    guild_id = os.environ.get('DISCORD_SERVER_ID')
    database_url = os.environ.get('DATABASE_URL')
    moodle_token = os.environ.get('MOODLE_TOKEN')
    notion_token = os.environ.get('NOTION_API_TOKEN')
    notion_db_id = os.environ.get('NOTION_DATABASE_ID')
    google_sa_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    google_sa_file = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
    google_cal_id = os.environ.get('GOOGLE_CALENDAR_ID')

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

    if notion_token and notion_db_id:
        logging.info("NOTION detected — Notion Todo List sync enabled.")
    else:
        logging.info("NOTION not configured — Notion sync disabled.")

    if (google_sa_json or google_sa_file) and google_cal_id:
        logging.info("GOOGLE CALENDAR detected — Google Calendar sync enabled.")
    else:
        logging.info("GOOGLE CALENDAR not configured — Google Calendar sync disabled.")

    return {
        'calendar_url': calendar_url,
        'bot_token': bot_token,
        'guild_id': guild_id,
        'database_url': database_url,
        'moodle_token': moodle_token,
        'notion_token': notion_token,
        'notion_db_id': notion_db_id,
        'google_sa_json': google_sa_json,
        'google_sa_file': google_sa_file,
        'google_cal_id': google_cal_id,
    }

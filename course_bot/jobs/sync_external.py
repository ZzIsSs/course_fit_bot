"""Job --sync-notion và --sync-gcal: đẩy deadline sang Notion và Google Calendar."""
import logging

from course_bot.core.config import load_env
from course_bot.db.connection import get_db
from course_bot.db.repositories.deadlines import get_all_deadlines_with_course
from course_bot.integrations.notion.client import NotionSync
from course_bot.integrations.google_calendar.client import GoogleCalendarSync


# ==================== ĐỒNG BỘ NOTION ====================

def sync_notion():
    """Đồng bộ toàn bộ deadline hiện có từ DB lên Notion Todo List.

    Dùng cho lần chạy đầu tiên sau khi cấu hình Notion,
    hoặc khi muốn đảm bảo dữ liệu Notion đồng bộ với DB.
    Chạy bằng: python main.py --sync-notion
    """
    env = load_env()
    if not env:
        return

    notion_token = env.get('notion_token')
    notion_db_id = env.get('notion_db_id')
    if not notion_token or not notion_db_id:
        logging.error("NOTION_API_TOKEN hoặc NOTION_DATABASE_ID chưa được thiết lập.")
        return

    database_url = env['database_url']
    notion = NotionSync(notion_token, notion_db_id)

    with get_db(database_url) as conn:
        all_deadlines = get_all_deadlines_with_course(conn)
        logging.info(f"Bắt đầu đồng bộ {len(all_deadlines)} deadline lên Notion...")
        stats = notion.sync_all_deadlines(all_deadlines)

    logging.info(
        f"Đồng bộ Notion hoàn tất: "
        f"{stats['added']} thêm mới, {stats['skipped']} đã có, "
        f"{stats['failed']} lỗi."
    )


# ==================== ĐỒNG BỘ GOOGLE CALENDAR ====================

def sync_google_calendar():
    """Đồng bộ toàn bộ deadline hiện có từ DB lên Google Calendar.

    Dùng cho lần chạy đầu tiên sau khi cấu hình Google Calendar,
    hoặc khi muốn đảm bảo dữ liệu Google Calendar đồng bộ với DB.
    Chạy bằng: python main.py --sync-gcal
    """
    env = load_env()
    if not env:
        return

    google_sa_json = env.get('google_sa_json')
    google_sa_file = env.get('google_sa_file')
    google_cal_id = env.get('google_cal_id')
    if not (google_sa_json or google_sa_file) or not google_cal_id:
        logging.error("GOOGLE_SERVICE_ACCOUNT_JSON/FILE hoặc GOOGLE_CALENDAR_ID chưa được thiết lập.")
        return

    database_url = env['database_url']
    gcal = GoogleCalendarSync(sa_json=google_sa_json, sa_file=google_sa_file, calendar_id=google_cal_id)
    if not gcal.is_available():
        logging.error("Không thể khởi tạo Google Calendar Service. Vui lòng kiểm tra lại Credentials.")
        return

    with get_db(database_url) as conn:
        all_deadlines = get_all_deadlines_with_course(conn)
        logging.info(f"Bắt đầu đồng bộ {len(all_deadlines)} deadline lên Google Calendar...")
        stats = gcal.sync_all_deadlines(all_deadlines)

    logging.info(
        f"Đồng bộ Google Calendar hoàn tất: "
        f"{stats['added']} thêm mới, {stats['skipped']} đã có, "
        f"{stats['failed']} lỗi."
    )

"""Job --crawl-deadlines: thu thập deadline từ Moodle API (logic ở services/deadline_crawler.py)."""
import logging

from course_bot.core.config import load_env
from course_bot.db.connection import get_db
from course_bot.services.deadline_crawler import crawl_moodle_deadlines


# ==================== THU THẬP DEADLINE TỪ MOODLE API ====================

def crawl_deadlines_standalone():
    """Chạy riêng module thu thập deadline từ Moodle API.

    Sử dụng: python main.py --crawl-deadlines
    Yêu cầu: MOODLE_TOKEN phải được cấu hình.
    """
    env = load_env()
    if not env:
        return

    moodle_token = env.get('moodle_token')
    if not moodle_token:
        logging.error("MOODLE_TOKEN chưa được cấu hình. Không thể thu thập deadline từ API.")
        return

    database_url = env['database_url']

    with get_db(database_url) as conn:
        stats = crawl_moodle_deadlines(moodle_token, conn)

    logging.info(
        "Kết quả thu thập: Assignments=%d, Quizzes=%d, Calendar=%d | "
        "Mới=%d, Cập nhật=%d, Auto-complete=%d",
        stats['assignments'], stats['quizzes'], stats['calendar'],
        stats['inserted'], stats['updated'], stats['auto_completed']
    )

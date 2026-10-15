import logging
from datetime import datetime, timezone

from course_bot.core.config import load_env
from course_bot.db.connection import get_db
from course_bot.db.repositories.courses import get_or_create_course, get_course_display_name
from course_bot.db.repositories.deadlines import (
    get_deadline_by_lms_id,
    insert_deadline,
    update_deadline_notified,
    update_deadline_discord_info,
    get_pending_manual_deadlines,
)
from course_bot.db.repositories.notifications import insert_notification
from course_bot.integrations.discord.rest import (
    get_bot_user,
    get_guild_channels,
    send_message,
    add_reaction,
    create_scheduled_event,
)
from course_bot.domain.semester import extract_semester_index
from course_bot.domain.reminders import decide_reminder, NEW, NOTIFIED_FIELDS
from course_bot.domain.messages import build_event_url, build_deadline_message
from course_bot.integrations.moodle.ics_feed import fetch_and_parse_events
from course_bot.services.channel_resolver import resolve_course_channel
from course_bot.services.completion_tracker import check_completions
from course_bot.services.announcement_tracker import check_moodle_updates
from course_bot.services.deadline_crawler import crawl_moodle_deadlines
from course_bot.integrations.notion.client import NotionSync
from course_bot.integrations.google_calendar.client import GoogleCalendarSync
from course_bot.core.time_utils import ensure_tz as _ensure_tz


# ==================== HÀM CHÍNH ====================

def run_main_bot():
    """Kịch bản chính: Kiểm tra deadline mới, gửi thông báo & nhắc nhở."""
    env = load_env()
    if not env:
        return

    bot_token = env['bot_token']
    guild_id = env['guild_id']
    calendar_url = env['calendar_url']
    database_url = env['database_url']

    # Get bot's own user ID (to distinguish bot reactions from user reactions)
    bot_user = get_bot_user(bot_token)
    bot_user_id = bot_user['id'] if bot_user else None

    # Khởi tạo Notion sync (tùy chọn — bỏ qua nếu chưa cấu hình)
    notion = None
    notion_token = env.get('notion_token')
    notion_db_id = env.get('notion_db_id')
    if notion_token and notion_db_id:
        notion = NotionSync(notion_token, notion_db_id)

    # Khởi tạo Google Calendar sync (tùy chọn — bỏ qua nếu chưa cấu hình)
    gcal = None
    google_sa_json = env.get('google_sa_json')
    google_sa_file = env.get('google_sa_file')
    google_cal_id = env.get('google_cal_id')
    if (google_sa_json or google_sa_file) and google_cal_id:
        gcal = GoogleCalendarSync(sa_json=google_sa_json, sa_file=google_sa_file, calendar_id=google_cal_id)

    events = fetch_and_parse_events(calendar_url)
    if events is None:
        logging.warning("Không tải được ICS, vẫn tiếp tục xử lý deadline thủ công (nếu có).")
        events = []

    # Cache channels
    channels = get_guild_channels(bot_token, guild_id)
    channel_map = {c['name']: c['id'] for c in channels if c.get('type') == 0}
    category_map = {c['name']: c['id'] for c in channels if c.get('type') == 4}

    with get_db(database_url) as conn:
        # Check completions from previous runs (check ✅ reactions)
        if bot_user_id:
            check_completions(bot_token, guild_id, bot_user_id, conn, notion=notion, gcal=gcal)

        # ===== Thu thập deadline từ Moodle API (assignments, quizzes, auto-complete) =====
        moodle_token = env.get('moodle_token')
        if moodle_token:
            logging.info("Bắt đầu thu thập deadline từ Moodle API...")
            try:
                crawl_stats = crawl_moodle_deadlines(moodle_token, conn)
                if crawl_stats.get('inserted', 0) > 0 or crawl_stats.get('updated', 0) > 0:
                    logging.info(
                        "Moodle API Crawler: %d deadline mới, %d cập nhật, %d auto-complete.",
                        crawl_stats['inserted'], crawl_stats['updated'], crawl_stats['auto_completed']
                    )
            except Exception as e:
                logging.error("Lỗi khi thu thập deadline từ Moodle API: %s", e)

        now = datetime.now(timezone.utc)

        # Gộp deadline thêm qua /add_deadline vào cùng pipeline xử lý
        manual_rows = get_pending_manual_deadlines(conn)
        manual_events = [{
            "uid": row['lms_deadlines_id'],
            "summary": row['deadline_name'],
            "deadline": _ensure_tz(row['due_time']),
            "subject": row['course_name'],
        } for row in manual_rows]

        # Process events (Moodle + manual)
        for event in events + manual_events:
            eid = event['uid']

            # Tìm deadline trong DB
            deadline = get_deadline_by_lms_id(conn, eid)

            if not deadline:
                # Tạo course và deadline mới trong DB
                course_id = get_or_create_course(conn, event['subject'])
                event_url = build_event_url(eid)
                insert_deadline(
                    conn, course_id, event['summary'],
                    eid, event['deadline'], event_url
                )
                deadline = get_deadline_by_lms_id(conn, eid)

            msg_type = decide_reminder(deadline, event['deadline'], now)

            if msg_type:
                # Lấy display_name từ DB (nếu đã có từ Moodle sync)
                display_name = get_course_display_name(conn, event['subject'])
                target_chan_id, _ = resolve_course_channel(
                    bot_token, guild_id, conn, channel_map, category_map,
                    event['subject'], display_name,
                    extract_semester_index(event.get('category_raw', '')),
                )
                if not target_chan_id:
                    continue

                # Deadline thủ công dùng source_url đã lưu, Moodle dùng link build từ uid
                if eid.startswith('manual-'):
                    event_url = deadline.get('source_url', '')
                else:
                    event_url = build_event_url(eid)
                content = build_deadline_message(
                    msg_type, event['subject'], event['summary'], event['deadline'], event_url)

                # Cập nhật trạng thái thông báo trong DB
                update_deadline_notified(conn, deadline['deadlines_id'], NOTIFIED_FIELDS[msg_type])

                msg_result = send_message(bot_token, target_chan_id, content)

                if msg_result:
                    # Add ✅ reaction as hint for users
                    add_reaction(bot_token, target_chan_id, msg_result['id'])

                    # Create scheduled event for NEW deadlines only
                    sched_event_id = None
                    if msg_type == NEW:
                        sched_event = create_scheduled_event(bot_token, guild_id, event)
                        if sched_event:
                            sched_event_id = sched_event['id']

                    # Lưu thông tin Discord vào DB
                    update_deadline_discord_info(
                        conn, deadline['deadlines_id'],
                        msg_result['id'], target_chan_id, sched_event_id
                    )

                    # Ghi log notification
                    insert_notification(conn, 'deadline', content[:500], deadline['deadlines_id'])

                    # Commit ngay vào DB để chốt trạng thái đã gửi Discord (chống gửi lặp nếu các bước sau lỗi)
                    conn.commit()

                    # ===== Đồng bộ lên Notion Todo List (chỉ deadline MỚI) =====
                    if notion and msg_type == NEW:
                        try:
                            source = "Discord" if eid.startswith('manual-') else "Moodle"
                            notion.add_deadline(
                                task_name=event['summary'],
                                course_name=event['subject'],
                                deadline_dt=event['deadline'],
                                url=event_url,
                                lms_id=eid,
                                source=source,
                            )
                        except Exception as e:
                            logging.warning(f"Notion sync error (bỏ qua để không ảnh hưởng bot): {e}")

                    # ===== Đồng bộ lên Google Calendar (chỉ deadline MỚI) =====
                    if gcal and msg_type == NEW:
                        try:
                            source = "Discord" if eid.startswith('manual-') else "Moodle"
                            gcal.add_deadline(
                                task_name=event['summary'],
                                course_name=event['subject'],
                                deadline_dt=event['deadline'],
                                url=event_url,
                                lms_id=eid,
                                source=source,
                            )
                        except Exception as e:
                            logging.warning(f"Google Calendar sync error (bỏ qua để không ảnh hưởng bot): {e}")


        # ===== Kiểm tra thông báo Moodle (nếu có token) =====
        moodle_token = env.get('moodle_token')
        if moodle_token:
            logging.info("Bắt đầu kiểm tra thông báo Moodle...")
            try:
                check_moodle_updates(bot_token, guild_id, moodle_token, conn)
                conn.commit()
            except Exception as e:
                logging.error(f"Lỗi khi quét thông báo Moodle: {e}")
        else:
            logging.info("Bỏ qua kiểm tra Moodle (chưa có MOODLE_TOKEN).")

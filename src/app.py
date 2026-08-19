import logging
import re
from datetime import datetime, timezone, timedelta

from src.config import load_env, LOCAL_TZ
from src.database import get_db
from src.db_queries import (
    get_or_create_course, get_deadline_by_lms_id, insert_deadline,
    update_deadline_notified, update_deadline_discord_info,
    get_all_deadlines_with_course, insert_notification
)
from src.discord_api import (
    get_bot_user, get_guild_channels, create_channel,
    send_message, add_reaction, create_scheduled_event
)
from src.moodle_parser import fetch_and_parse_events, slugify_channel_name
from src.event_tracker import check_completions
from src.announcement_tracker import check_moodle_updates


# ==================== TIỆN ÍCH ====================

def _build_event_url(uid):
    """Tạo URL đến sự kiện trên Moodle từ UID."""
    base_url = "https://courses.fit.hcmus.edu.vn/calendar/view.php?view=upcoming"
    id_match = re.search(r'^(\d+)@', uid)
    if id_match:
        return (
            f"https://courses.fit.hcmus.edu.vn/calendar/view.php"
            f"?view=day&course=1&time=upcoming#event_{id_match.group(1)}"
        )
    return base_url


def _ensure_tz(dt):
    """Đảm bảo datetime có timezone (mặc định UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


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

    events = fetch_and_parse_events(calendar_url)
    if events is None:
        return

    # Cache channels
    channels = get_guild_channels(bot_token, guild_id)
    channel_map = {c['name']: c['id'] for c in channels if c.get('type') == 0}

    with get_db(database_url) as conn:
        # Check completions from previous runs (check ✅ reactions)
        if bot_user_id:
            check_completions(bot_token, guild_id, bot_user_id, conn)

        now = datetime.now(timezone.utc)

        # Process events
        for event in events:
            eid = event['uid']

            # Tìm deadline trong DB
            deadline = get_deadline_by_lms_id(conn, eid)

            if not deadline:
                # Tạo course và deadline mới trong DB
                course_id = get_or_create_course(conn, event['subject'])
                event_url = _build_event_url(eid)
                insert_deadline(
                    conn, course_id, event['summary'],
                    eid, event['deadline'], event_url
                )
                deadline = get_deadline_by_lms_id(conn, eid)

            time_left = event['deadline'] - now
            if time_left.total_seconds() < 0:
                continue

            msg_type = None
            if not deadline['notified_new']:
                msg_type = "NEW"
            elif time_left <= timedelta(days=3) and not deadline['reminded_3d']:
                msg_type = "3_DAYS"
            elif time_left <= timedelta(days=1) and not deadline['reminded_1d']:
                msg_type = "1_DAY"

            if msg_type:
                chan_name = slugify_channel_name(event['subject'])

                if chan_name not in channel_map:
                    new_channel = create_channel(bot_token, guild_id, chan_name)
                    if new_channel:
                        channel_map[chan_name] = new_channel['id']
                    else:
                        continue

                target_chan_id = channel_map[chan_name]

                event_url = _build_event_url(eid)
                deadline_local = event['deadline'].astimezone(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')
                completion_hint = "\n\n✅ *React ✅ vào tin nhắn này khi đã hoàn thành!*"

                if msg_type == "NEW":
                    content = f"@everyone 🚨 **DEADLINE MỚI** 🚨\n\n📌 **Môn:** {event['subject']}\n📝 **Nội dung:** {event['summary']}\n⏰ **Hạn chót:** {deadline_local}\n🔗 **Xem:** {event_url}{completion_hint}"
                elif msg_type == "3_DAYS":
                    content = f"@everyone ⚠️ **NHẮC NHỞ: CÒN 3 NGÀY** ⚠️\n\n📌 **Môn:** {event['subject']}\n📝 **Nội dung:** {event['summary']}\n⏰ **Hạn chót:** {deadline_local}\n🔗 **Xem:** {event_url}{completion_hint}"
                elif msg_type == "1_DAY":
                    content = f"@everyone 🆘 **KHẨN CẤP: CÒN 24 GIỜ** 🆘\n\n📌 **Môn:** {event['subject']}\n📝 **Nội dung:** {event['summary']}\n⏰ **Hạn chót:** {deadline_local}\n🔗 **Xem:** {event_url}{completion_hint}"

                # Cập nhật trạng thái thông báo trong DB
                field_map = {"NEW": "notified_new", "3_DAYS": "reminded_3d", "1_DAY": "reminded_1d"}
                update_deadline_notified(conn, deadline['deadlines_id'], field_map[msg_type])

                msg_result = send_message(bot_token, target_chan_id, content)

                if msg_result:
                    # Add ✅ reaction as hint for users
                    add_reaction(bot_token, target_chan_id, msg_result['id'])

                    # Create scheduled event for NEW deadlines only
                    sched_event_id = None
                    if msg_type == "NEW":
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

        # ===== Kiểm tra thông báo Moodle (nếu có token) =====
        moodle_token = env.get('moodle_token')
        if moodle_token:
            logging.info("Bắt đầu kiểm tra thông báo Moodle...")
            check_moodle_updates(bot_token, guild_id, moodle_token, conn)
        else:
            logging.info("Bỏ qua kiểm tra Moodle (chưa có MOODLE_TOKEN).")


# ==================== BÁO CÁO HẰNG NGÀY ====================

def send_daily_summary():
    """Send a daily summary of all upcoming deadlines with completion status."""
    env = load_env()
    if not env:
        return

    bot_token = env['bot_token']
    guild_id = env['guild_id']
    database_url = env['database_url']

    with get_db(database_url) as conn:
        # Check completions before generating summary
        bot_user = get_bot_user(bot_token)
        bot_user_id = bot_user['id'] if bot_user else None
        if bot_user_id:
            check_completions(bot_token, guild_id, bot_user_id, conn)

        # Lấy tất cả deadlines từ DB (thay vì parse ICS lại)
        all_deadlines = get_all_deadlines_with_course(conn)

        now = datetime.now(timezone.utc)
        today_str = now.astimezone(LOCAL_TZ).strftime('%d/%m/%Y')

        # Categorize deadlines
        overdue = []
        urgent_1d = []
        warning_3d = []
        upcoming = []
        subjects = set()
        completed_count = 0

        for dl in all_deadlines:
            due_time = _ensure_tz(dl['due_time'])
            time_left = due_time - now
            subjects.add(dl['course_name'])

            if dl['completed']:
                completed_count += 1

            if time_left.total_seconds() < 0:
                overdue.append(dl)
            elif time_left <= timedelta(days=1):
                urgent_1d.append(dl)
            elif time_left <= timedelta(days=3):
                warning_3d.append(dl)
            else:
                upcoming.append(dl)

        # Build summary message
        lines = []
        lines.append("@everyone")
        lines.append(f"📊 **TỔNG KẾT DEADLINE — {today_str}**")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📚 **Số môn đang theo dõi:** {len(subjects)}")
        lines.append(f"📌 **Tổng deadline:** {len(all_deadlines)}")
        lines.append(f"✅ **Đã hoàn thành:** {completed_count}/{len(all_deadlines)}")
        lines.append(f"🔴 **Quá hạn:** {len(overdue)}")
        lines.append(f"🟠 **Còn < 24 giờ:** {len(urgent_1d)}")
        lines.append(f"🟡 **Còn < 3 ngày:** {len(warning_3d)}")
        lines.append(f"🟢 **Còn nhiều thời gian:** {len(upcoming)}")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")

        def format_deadline_line(d):
            dt = _ensure_tz(d['due_time'])
            dl_str = dt.astimezone(LOCAL_TZ).strftime('%d/%m %H:%M')
            status = "✅" if d['completed'] else "❌"
            by = f" (bởi {d['completed_by']})" if d.get('completed_by') else ""
            return f"  {status} [{d['course_name']}] {d['deadline_name']} — ⏰ {dl_str}{by}"

        # Detail urgent deadlines
        if urgent_1d:
            lines.append("\n🆘 **KHẨN CẤP (< 24 giờ):**")
            for d in urgent_1d:
                lines.append(format_deadline_line(d))

        if warning_3d:
            lines.append("\n⚠️ **SẮP TỚI (< 3 ngày):**")
            for d in warning_3d:
                lines.append(format_deadline_line(d))

        if upcoming:
            lines.append("\n📅 **DEADLINE SẮP TỚI:**")
            for d in sorted(upcoming, key=lambda x: x['due_time']):
                lines.append(format_deadline_line(d))

        if overdue:
            lines.append("\n🔴 **QUÁ HẠN:**")
            for d in overdue:
                lines.append(format_deadline_line(d))

        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 *React ✅ vào tin nhắn deadline để đánh dấu hoàn thành!*")

        content = "\n".join(lines)

        # Find or create the summary channel
        channels = get_guild_channels(bot_token, guild_id)
        channel_map = {c['name']: c['id'] for c in channels if c.get('type') == 0}

        summary_channel = "tong-ket-deadline"
        if summary_channel not in channel_map:
            new_ch = create_channel(bot_token, guild_id, summary_channel)
            if new_ch:
                channel_map[summary_channel] = new_ch['id']
            else:
                logging.error("Cannot create summary channel.")
                return

        send_message(bot_token, channel_map[summary_channel], content)
        logging.info("Daily summary sent successfully!")


# ==================== BÁO CÁO TIẾN ĐỘ ====================

def send_progress_report():
    """Gửi báo cáo tiến độ deadline chi tiết vào channel #tien-do-deadline."""
    env = load_env()
    if not env:
        return

    bot_token = env['bot_token']
    guild_id = env['guild_id']
    database_url = env['database_url']

    with get_db(database_url) as conn:
        # Check completions before reporting
        bot_user = get_bot_user(bot_token)
        bot_user_id = bot_user['id'] if bot_user else None
        if bot_user_id:
            check_completions(bot_token, guild_id, bot_user_id, conn)

        # Lấy tất cả deadlines từ DB
        all_deadlines = get_all_deadlines_with_course(conn)

        now = datetime.now(timezone.utc)
        now_str = now.astimezone(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')

        # Group deadlines by subject
        by_subject = {}
        for dl in all_deadlines:
            subj = dl['course_name']
            if subj not in by_subject:
                by_subject[subj] = []
            by_subject[subj].append(dl)

        total = len(all_deadlines)
        completed = sum(1 for d in all_deadlines if d['completed'])

        lines = []
        lines.append(f"📋 **TIẾN ĐỘ DEADLINE — Cập nhật lúc {now_str}**")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Progress bar
        if total > 0:
            pct = int(completed / total * 100)
            filled = int(pct / 5)
            bar = "🟩" * filled + "⬜" * (20 - filled)
            lines.append(f"\n📊 **Tổng tiến độ:** {completed}/{total} ({pct}%)")
            lines.append(bar)
        else:
            lines.append("\n📊 **Không có deadline nào đang được theo dõi.**")

        for subj in sorted(by_subject.keys()):
            subj_deadlines = by_subject[subj]
            subj_completed = sum(1 for d in subj_deadlines if d['completed'])
            lines.append(f"\n📚 **{subj}** — {subj_completed}/{len(subj_deadlines)} hoàn thành")

            for d in sorted(subj_deadlines, key=lambda x: x['due_time']):
                due_time = _ensure_tz(d['due_time'])
                dl_str = due_time.astimezone(LOCAL_TZ).strftime('%d/%m %H:%M')
                time_left = due_time - now

                if d['completed']:
                    status = "✅ Đã hoàn thành"
                    if d.get('completed_by'):
                        status += f" (bởi {d['completed_by']})"
                elif time_left.total_seconds() < 0:
                    status = "🔴 Quá hạn!"
                elif time_left <= timedelta(days=1):
                    hours = max(1, int(time_left.total_seconds() / 3600))
                    status = f"🟠 Còn {hours} giờ"
                elif time_left <= timedelta(days=3):
                    days = max(1, int(time_left.total_seconds() / 86400))
                    status = f"🟡 Còn {days} ngày"
                else:
                    days = int(time_left.total_seconds() / 86400)
                    status = f"🟢 Còn {days} ngày"

                lines.append(f"  ▸ {d['deadline_name']}")
                lines.append(f"    ⏰ {dl_str} | {status}")

        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 *React ✅ vào tin nhắn deadline gốc để đánh dấu hoàn thành!*")

        content = "\n".join(lines)

        # Send to tien-do-deadline channel
        channels = get_guild_channels(bot_token, guild_id)
        channel_map = {c['name']: c['id'] for c in channels if c.get('type') == 0}

        progress_channel = "tien-do-deadline"
        if progress_channel not in channel_map:
            new_ch = create_channel(bot_token, guild_id, progress_channel)
            if new_ch:
                channel_map[progress_channel] = new_ch['id']
            else:
                logging.error("Cannot create progress channel.")
                return

        send_message(bot_token, channel_map[progress_channel], content)
        logging.info("Progress report sent successfully!")


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

"""Job --summary và --progress: báo cáo deadline hằng ngày và tiến độ."""
import logging
from datetime import datetime, timezone, timedelta

from course_bot.core.config import load_env
from course_bot.core.time_utils import LOCAL_TZ
from course_bot.db.connection import get_db
from course_bot.db.repositories.deadlines import get_all_deadlines_with_course
from course_bot.integrations.discord.rest import (
    get_bot_user,
    get_guild_channels,
    create_channel,
    send_message,
)
from course_bot.services.completion_tracker import check_completions
from course_bot.core.time_utils import ensure_tz as _ensure_tz


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

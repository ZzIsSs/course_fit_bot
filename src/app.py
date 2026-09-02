import logging
import re
from datetime import datetime, timezone, timedelta

from src.config import load_env, LOCAL_TZ
from src.database import get_db
from src.db_queries import (
    get_or_create_course, get_deadline_by_lms_id, insert_deadline,
    update_deadline_notified, update_deadline_discord_info,
    get_all_deadlines_with_course, insert_notification,
    update_course_chat_id, get_all_courses, get_course_display_name,
    get_course_discord_category, set_course_discord_category,
    get_pending_manual_deadlines
)
from src.discord_api import (
    get_bot_user, get_guild_channels, create_channel, rename_channel,
    send_message, add_reaction, create_scheduled_event,
    resolve_category
)
from src.moodle_parser import (
    fetch_and_parse_events, slugify_channel_name,
    extract_display_name, extract_subject, extract_semester_index
)
from src.moodle_api import get_site_info, get_enrolled_courses
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


from src.utils import ensure_tz as _ensure_tz


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
        logging.warning("Không tải được ICS, vẫn tiếp tục xử lý deadline thủ công (nếu có).")
        events = []

    # Cache channels
    channels = get_guild_channels(bot_token, guild_id)
    channel_map = {c['name']: c['id'] for c in channels if c.get('type') == 0}
    category_map = {c['name']: c['id'] for c in channels if c.get('type') == 4}

    with get_db(database_url) as conn:
        # Check completions from previous runs (check ✅ reactions)
        if bot_user_id:
            check_completions(bot_token, guild_id, bot_user_id, conn)

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
                # Lấy display_name từ DB (nếu đã có từ Moodle sync)
                display_name = get_course_display_name(conn, event['subject'])
                chan_name = slugify_channel_name(event['subject'], display_name)
                old_chan_name = slugify_channel_name(event['subject'])

                if chan_name in channel_map:
                    target_chan_id = channel_map[chan_name]
                elif old_chan_name in channel_map:
                    # Fallback: kênh cũ (chỉ mã môn) vẫn tồn tại
                    target_chan_id = channel_map[old_chan_name]
                else:
                    ky = extract_semester_index(event.get('category_raw', ''))
                    if ky is not None:
                        category_id = resolve_category(bot_token, guild_id, category_map, f"kì {ky}")
                    else:
                        # Không nhận diện được tự động → dùng category đã gán tay
                        # qua scripts/set_category.py (nếu có)
                        category_id = get_course_discord_category(conn, event['subject'])

                    new_channel = create_channel(bot_token, guild_id, chan_name, parent_id=category_id)
                    if new_channel:
                        channel_map[chan_name] = new_channel['id']
                        target_chan_id = new_channel['id']
                        if category_id:
                            set_course_discord_category(conn, event['subject'], category_id)
                    else:
                        continue

                # Deadline thủ công dùng source_url đã lưu, Moodle dùng link build từ uid
                if eid.startswith('manual-'):
                    event_url = deadline.get('source_url', '')
                else:
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

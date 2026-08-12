import os
import json
import logging
import re
from datetime import datetime, timezone, timedelta

from src.config import load_env, LOCAL_TZ, STATE_FILE
from src.discord_api import (
    get_bot_user, get_guild_channels, create_channel,
    send_message, add_reaction, create_scheduled_event
)
from src.moodle_parser import fetch_and_parse_events, slugify_channel_name
from src.event_tracker import check_completions

# ==================== HÀM CHÍNH ====================

def run_main_bot():
    """Kịch bản chính: Kiểm tra deadline mới, gửi thông báo & nhắc nhở."""
    env = load_env()
    if not env:
        return

    bot_token = env['bot_token']
    guild_id = env['guild_id']
    calendar_url = env['calendar_url']

    # Get bot's own user ID (to distinguish bot reactions from user reactions)
    bot_user = get_bot_user(bot_token)
    bot_user_id = bot_user['id'] if bot_user else None

    events = fetch_and_parse_events(calendar_url)
    if events is None:
        return

    # Cache channels
    channels = get_guild_channels(bot_token, guild_id)
    channel_map = {c['name']: c['id'] for c in channels if c.get('type') == 0}

    # Load state
    os.makedirs('data', exist_ok=True)
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError:
                state = {}
    else:
        state = {}

    if "events" not in state:
        state["events"] = {}

    # Check completions from previous runs (check ✅ reactions)
    state_changed = False
    if bot_user_id:
        if check_completions(bot_token, guild_id, bot_user_id, state):
            state_changed = True

    now = datetime.now(timezone.utc)

    # Process events
    for event in events:
        eid = event['uid']
        if eid not in state['events']:
            state['events'][eid] = {
                "notified_new": False,
                "reminded_3d": False,
                "reminded_1d": False,
                "scheduled_event_id": None,
                "message_id": None,
                "channel_id": None,
                "completed": False,
                "completed_by": None
            }
        else:
            # Ensure backward compatibility with new fields
            evt = state['events'][eid]
            evt.setdefault('scheduled_event_id', None)
            evt.setdefault('message_id', None)
            evt.setdefault('channel_id', None)
            evt.setdefault('completed', False)
            evt.setdefault('completed_by', None)

        evt_state = state['events'][eid]
        time_left = event['deadline'] - now

        if time_left.total_seconds() < 0:
            continue

        msg_type = None
        if not evt_state['notified_new']:
            msg_type = "NEW"
            evt_state['notified_new'] = True
        elif time_left <= timedelta(days=3) and not evt_state['reminded_3d']:
            msg_type = "3_DAYS"
            evt_state['reminded_3d'] = True
        elif time_left <= timedelta(days=1) and not evt_state['reminded_1d']:
            msg_type = "1_DAY"
            evt_state['reminded_1d'] = True

        if msg_type:
            state_changed = True
            chan_name = slugify_channel_name(event['subject'])

            if chan_name not in channel_map:
                new_channel = create_channel(bot_token, guild_id, chan_name)
                if new_channel:
                    channel_map[chan_name] = new_channel['id']
                else:
                    continue

            target_chan_id = channel_map[chan_name]

            event_url = "https://courses.fit.hcmus.edu.vn/calendar/view.php?view=upcoming"
            id_match = re.search(r'^(\d+)@', eid)
            if id_match:
                event_url = f"https://courses.fit.hcmus.edu.vn/calendar/view.php?view=day&course=1&time=upcoming#event_{id_match.group(1)}"

            deadline_local = event['deadline'].astimezone(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')

            completion_hint = "\n\n✅ *React ✅ vào tin nhắn này khi đã hoàn thành!*"

            if msg_type == "NEW":
                content = f"@everyone 🚨 **DEADLINE MỚI** 🚨\n\n📌 **Môn:** {event['subject']}\n📝 **Nội dung:** {event['summary']}\n⏰ **Hạn chót:** {deadline_local}\n🔗 **Xem:** {event_url}{completion_hint}"
            elif msg_type == "3_DAYS":
                content = f"@everyone ⚠️ **NHẮC NHỞ: CÒN 3 NGÀY** ⚠️\n\n📌 **Môn:** {event['subject']}\n📝 **Nội dung:** {event['summary']}\n⏰ **Hạn chót:** {deadline_local}\n🔗 **Xem:** {event_url}{completion_hint}"
            elif msg_type == "1_DAY":
                content = f"@everyone 🆘 **KHẨN CẤP: CÒN 24 GIỜ** 🆘\n\n📌 **Môn:** {event['subject']}\n📝 **Nội dung:** {event['summary']}\n⏰ **Hạn chót:** {deadline_local}\n🔗 **Xem:** {event_url}{completion_hint}"

            msg_result = send_message(bot_token, target_chan_id, content)

            if msg_result:
                # Store message info for reaction tracking
                evt_state['message_id'] = msg_result['id']
                evt_state['channel_id'] = target_chan_id

                # Add ✅ reaction as hint for users
                add_reaction(bot_token, target_chan_id, msg_result['id'])

            # Create scheduled event for NEW deadlines only
            if msg_type == "NEW":
                sched_event = create_scheduled_event(bot_token, guild_id, event)
                if sched_event:
                    evt_state['scheduled_event_id'] = sched_event['id']

    if state_changed:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)
        logging.info("State file updated.")

# ==================== BÁO CÁO HẰNG NGÀY ====================

def send_daily_summary():
    """Send a daily summary of all upcoming deadlines with completion status."""
    env = load_env()
    if not env:
        return

    bot_token = env['bot_token']
    guild_id = env['guild_id']
    calendar_url = env['calendar_url']

    events = fetch_and_parse_events(calendar_url)
    if events is None:
        return

    # Load state for completion tracking
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError:
                state = {}

    # Check completions before generating summary
    bot_user = get_bot_user(bot_token)
    bot_user_id = bot_user['id'] if bot_user else None
    if bot_user_id and 'events' in state:
        if check_completions(bot_token, guild_id, bot_user_id, state):
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4)

    now = datetime.now(timezone.utc)
    today_str = now.astimezone(LOCAL_TZ).strftime('%d/%m/%Y')

    # Categorize events
    overdue = []
    urgent_1d = []
    warning_3d = []
    upcoming = []
    subjects = set()
    completed_count = 0

    for event in events:
        time_left = event['deadline'] - now
        subjects.add(event['subject'])

        # Get completion status from state
        eid = event['uid']
        evt_state = state.get('events', {}).get(eid, {})
        event['completed'] = evt_state.get('completed', False)
        event['completed_by'] = evt_state.get('completed_by')

        if event['completed']:
            completed_count += 1

        if time_left.total_seconds() < 0:
            overdue.append(event)
        elif time_left <= timedelta(days=1):
            urgent_1d.append(event)
        elif time_left <= timedelta(days=3):
            warning_3d.append(event)
        else:
            upcoming.append(event)

    # Build summary message
    lines = []
    lines.append(f"@everyone")
    lines.append(f"📊 **TỔNG KẾT DEADLINE — {today_str}**")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📚 **Số môn đang theo dõi:** {len(subjects)}")
    lines.append(f"📌 **Tổng deadline:** {len(events)}")
    lines.append(f"✅ **Đã hoàn thành:** {completed_count}/{len(events)}")
    lines.append(f"🔴 **Quá hạn:** {len(overdue)}")
    lines.append(f"🟠 **Còn < 24 giờ:** {len(urgent_1d)}")
    lines.append(f"🟡 **Còn < 3 ngày:** {len(warning_3d)}")
    lines.append(f"🟢 **Còn nhiều thời gian:** {len(upcoming)}")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━")

    def format_event_line(e):
        dl = e['deadline'].astimezone(LOCAL_TZ).strftime('%d/%m %H:%M')
        status = "✅" if e.get('completed') else "❌"
        by = f" (bởi {e['completed_by']})" if e.get('completed_by') else ""
        return f"  {status} [{e['subject']}] {e['summary']} — ⏰ {dl}{by}"

    # Detail urgent deadlines
    if urgent_1d:
        lines.append(f"\n🆘 **KHẨN CẤP (< 24 giờ):**")
        for e in urgent_1d:
            lines.append(format_event_line(e))

    if warning_3d:
        lines.append(f"\n⚠️ **SẮP TỚI (< 3 ngày):**")
        for e in warning_3d:
            lines.append(format_event_line(e))

    if upcoming:
        lines.append(f"\n📅 **DEADLINE SẮP TỚI:**")
        for e in sorted(upcoming, key=lambda x: x['deadline']):
            lines.append(format_event_line(e))

    if overdue:
        lines.append(f"\n🔴 **QUÁ HẠN:**")
        for e in overdue:
            lines.append(format_event_line(e))

    lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"💡 *React ✅ vào tin nhắn deadline để đánh dấu hoàn thành!*")

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
    calendar_url = env['calendar_url']

    events = fetch_and_parse_events(calendar_url)
    if events is None:
        return

    # Load state
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError:
                state = {}

    # Check completions before reporting
    bot_user = get_bot_user(bot_token)
    bot_user_id = bot_user['id'] if bot_user else None
    if bot_user_id and 'events' in state:
        if check_completions(bot_token, guild_id, bot_user_id, state):
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4)

    now = datetime.now(timezone.utc)
    now_str = now.astimezone(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')

    # Group events by subject
    by_subject = {}
    for event in events:
        eid = event['uid']
        evt_state = state.get('events', {}).get(eid, {})
        event['completed'] = evt_state.get('completed', False)
        event['completed_by'] = evt_state.get('completed_by')

        subj = event['subject']
        if subj not in by_subject:
            by_subject[subj] = []
        by_subject[subj].append(event)

    total = len(events)
    completed = sum(1 for e in events if e.get('completed'))

    lines = []
    lines.append(f"📋 **TIẾN ĐỘ DEADLINE — Cập nhật lúc {now_str}**")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Progress bar
    if total > 0:
        pct = int(completed / total * 100)
        filled = int(pct / 5)
        bar = "🟩" * filled + "⬜" * (20 - filled)
        lines.append(f"\n📊 **Tổng tiến độ:** {completed}/{total} ({pct}%)")
        lines.append(f"{bar}")
    else:
        lines.append(f"\n📊 **Không có deadline nào đang được theo dõi.**")

    for subj in sorted(by_subject.keys()):
        subj_events = by_subject[subj]
        subj_completed = sum(1 for e in subj_events if e.get('completed'))
        lines.append(f"\n📚 **{subj}** — {subj_completed}/{len(subj_events)} hoàn thành")

        for e in sorted(subj_events, key=lambda x: x['deadline']):
            dl = e['deadline'].astimezone(LOCAL_TZ).strftime('%d/%m %H:%M')
            time_left = e['deadline'] - now

            if e.get('completed'):
                status = "✅ Đã hoàn thành"
                if e.get('completed_by'):
                    status += f" (bởi {e['completed_by']})"
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

            lines.append(f"  ▸ {e['summary']}")
            lines.append(f"    ⏰ {dl} | {status}")

    lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"💡 *React ✅ vào tin nhắn deadline gốc để đánh dấu hoàn thành!*")

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

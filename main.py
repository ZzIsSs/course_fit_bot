import os
import sys
import json
import logging
import requests
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from urllib.parse import quote as url_quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DISCORD_API_BASE = "https://discord.com/api/v10"

def get_headers(token):
    return {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }

def get_bot_user(token):
    """Lấy thông tin user của bot (để phân biệt reaction của bot vs người dùng)."""
    url = f"{DISCORD_API_BASE}/users/@me"
    response = requests.get(url, headers=get_headers(token))
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to get bot user: {response.status_code} {response.text}")
        return None

def get_guild_channels(token, guild_id):
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}/channels"
    response = requests.get(url, headers=get_headers(token))
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to fetch channels: {response.status_code} {response.text}")
        return []

def create_channel(token, guild_id, channel_name):
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}/channels"
    payload = {
        "name": channel_name,
        "type": 0 # 0 is Text Channel
    }
    response = requests.post(url, headers=get_headers(token), json=payload)
    if response.status_code == 201:
        logging.info(f"Created channel {channel_name}")
        return response.json()
    else:
        logging.error(f"Failed to create channel {channel_name}: {response.status_code} {response.text}")
        return None

def send_message(token, channel_id, content):
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
    payload = {"content": content}
    response = requests.post(url, headers=get_headers(token), json=payload)
    if response.status_code not in (200, 201):
        logging.error(f"Failed to send message: {response.status_code} {response.text}")
        return None
    return response.json()

def slugify_channel_name(name):
    """Chuyển tên môn học thành tên kênh hợp lệ cho Discord.
    Bỏ dấu tiếng Việt, chuyển thường, thay ký tự đặc biệt bằng '-'.
    Ví dụ: 'Toán Rời Rạc' → 'toan-roi-rac'
           'CSC10014' → 'csc10014'
    """
    # Bỏ dấu tiếng Việt
    normalized = unicodedata.normalize("NFD", name)
    no_accents = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    no_accents = no_accents.replace("đ", "d").replace("Đ", "D")
    # Chuyển thường, thay ký tự đặc biệt bằng '-'
    slug = no_accents.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug if slug else "general"

def extract_subject(category):
    """Trích xuất tên môn học từ trường CATEGORIES của ICS.
    Hỗ trợ nhiều format:
        'CQ2526HK2_CSC10014_CQ2024/2' → 'CSC10014'
        'CSC10014'                     → 'CSC10014'
        'Toán Rời Rạc'                 → 'Toán Rời Rạc'
        ''  hoặc None                  → 'General'
    """
    if not category or category.strip() == "":
        return "General"

    # Pattern 1: Mã môn chuẩn FIT dạng _CSC10014_ (3-4 chữ + 5 số, bao quanh bởi _)
    match = re.search(r'_([A-Z]{2,5}\d{4,6})_', category)
    if match:
        return match.group(1)

    # Pattern 2: Mã môn đứng riêng hoặc đầu/cuối chuỗi (CSC10014, MTH00003, ...)
    match = re.search(r'\b([A-Z]{2,5}\d{4,6})\b', category)
    if match:
        return match.group(1)

    # Pattern 3: Không tìm được mã môn → dùng nguyên category làm tên
    # (ví dụ: 'Toán Rời Rạc', 'User event', ...)
    return category.strip()

# ==================== SCHEDULED EVENTS ====================

def create_scheduled_event(token, guild_id, event):
    """Tạo Discord Scheduled Event cho deadline mới."""
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}/scheduled-events"

    local_tz = timezone(timedelta(hours=7))
    deadline_local = event['deadline'].astimezone(local_tz).strftime('%d/%m/%Y %H:%M')

    # Build Moodle event URL
    event_url = "https://courses.fit.hcmus.edu.vn/calendar/view.php?view=upcoming"
    id_match = re.search(r'^(\d+)@', event['uid'])
    if id_match:
        event_url = f"https://courses.fit.hcmus.edu.vn/calendar/view.php?view=day&course=1&time=upcoming#event_{id_match.group(1)}"

    # Name max 100 chars
    name = f"📌 {event['subject']} — {event['summary']}"
    if len(name) > 100:
        name = name[:97] + "..."

    # Description max 1000 chars
    description = f"⏰ Hạn chót: {deadline_local} (GMT+7)\n📝 {event['summary']}\n🔗 {event_url}"
    if len(description) > 1000:
        description = description[:997] + "..."

    payload = {
        "name": name,
        "privacy_level": 2,  # GUILD_ONLY
        "scheduled_start_time": event['deadline'].isoformat(),
        "scheduled_end_time": (event['deadline'] + timedelta(minutes=5)).isoformat(),
        "entity_type": 3,  # EXTERNAL
        "entity_metadata": {"location": event_url},
        "description": description
    }

    response = requests.post(url, headers=get_headers(token), json=payload)
    if response.status_code in (200, 201):
        result = response.json()
        logging.info(f"Created scheduled event: {name} (ID: {result['id']})")
        return result
    else:
        logging.error(f"Failed to create scheduled event: {response.status_code} {response.text}")
        return None

def update_scheduled_event(token, guild_id, event_id, status):
    """Cập nhật trạng thái Scheduled Event. status: 2=ACTIVE, 3=COMPLETED, 4=CANCELED."""
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}/scheduled-events/{event_id}"
    payload = {"status": status}
    response = requests.patch(url, headers=get_headers(token), json=payload)
    if response.status_code == 200:
        logging.info(f"Updated scheduled event {event_id} to status {status}")
        return True
    else:
        logging.error(f"Failed to update scheduled event: {response.status_code} {response.text}")
        return False

# ==================== REACTION TRACKING ====================

def add_reaction(token, channel_id, message_id, emoji="✅"):
    """Thêm reaction emoji vào tin nhắn (gợi ý người dùng react để đánh dấu hoàn thành)."""
    encoded_emoji = url_quote(emoji)
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me"
    # PUT reaction requires no Content-Type for empty body
    headers = {"Authorization": f"Bot {token}"}
    response = requests.put(url, headers=headers)
    if response.status_code == 204:
        logging.info(f"Added reaction {emoji} to message {message_id}")
        return True
    else:
        logging.error(f"Failed to add reaction: {response.status_code} {response.text}")
        return False

def get_reaction_users(token, channel_id, message_id, emoji="✅"):
    """Lấy danh sách user đã react emoji vào tin nhắn."""
    encoded_emoji = url_quote(emoji)
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}"
    response = requests.get(url, headers=get_headers(token))
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to get reactions: {response.status_code} {response.text}")
        return []

def check_completions(token, guild_id, bot_user_id, state):
    """Kiểm tra reactions ✅ trên tin nhắn deadline, đánh dấu hoàn thành nếu có người react."""
    changed = False
    for eid, evt_state in state.get('events', {}).items():
        # Skip if already completed or no message tracked
        if evt_state.get('completed') or not evt_state.get('message_id'):
            continue

        users = get_reaction_users(token, evt_state['channel_id'], evt_state['message_id'])
        # Filter out bot's own reaction
        non_bot_users = [u for u in users if u.get('id') != bot_user_id]

        if non_bot_users:
            evt_state['completed'] = True
            evt_state['completed_by'] = non_bot_users[0].get('username', 'Unknown')
            changed = True
            logging.info(f"Deadline {eid} marked as completed by {evt_state['completed_by']}")

            # Update scheduled event status to COMPLETED
            if evt_state.get('scheduled_event_id'):
                update_scheduled_event(token, guild_id, evt_state['scheduled_event_id'], 3)

    return changed

# ==================== ICS PARSING ====================

def fetch_and_parse_events(calendar_url):
    """Fetch ICS and parse events. Returns list of event dicts or None on failure."""
    try:
        logging.info("Fetching calendar ICS file...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(calendar_url, headers=headers, timeout=15)

        if response.status_code != 200:
            logging.error(f"Failed to load calendar. HTTP Status: {response.status_code}")
            return None

        ics_data = response.text
    except Exception as e:
        logging.error(f"Error fetching calendar: {e}")
        return None

    events = []
    vevent_blocks = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', ics_data, re.DOTALL)

    for block in vevent_blocks:
        uid_match = re.search(r'\nUID:(.*?)\n', block)
        summary_match = re.search(r'\nSUMMARY:(.*?)\n', block)
        dtend_match = re.search(r'\nDTEND:(.*?)\n', block)
        cat_match = re.search(r'\nCATEGORIES:(.*?)\n', block)

        if uid_match and summary_match and dtend_match:
            uid = uid_match.group(1).strip()
            summary = summary_match.group(1).strip()
            dtend_str = dtend_match.group(1).strip()
            category = cat_match.group(1).strip() if cat_match else "General"

            subject = extract_subject(category)

            try:
                dtend = datetime.strptime(dtend_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                events.append({
                    "uid": uid,
                    "summary": summary,
                    "deadline": dtend,
                    "subject": subject
                })
            except Exception as e:
                logging.error(f"Error parsing date {dtend_str}: {e}")

    logging.info(f"Found {len(events)} events in calendar.")
    return events

# ==================== MAIN FUNCTIONS ====================

def main():
    calendar_url = os.environ.get('MOODLE_CALENDAR_URL')
    bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    guild_id = os.environ.get('DISCORD_SERVER_ID')

    if not all([calendar_url, bot_token, guild_id]):
        logging.error("Missing environment variables: MOODLE_CALENDAR_URL, DISCORD_BOT_TOKEN, or DISCORD_SERVER_ID")
        return

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
    state_file = 'data/state.json'
    os.makedirs('data', exist_ok=True)
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
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
    local_tz = timezone(timedelta(hours=7))

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

            deadline_local = event['deadline'].astimezone(local_tz).strftime('%d/%m/%Y %H:%M')

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
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)
        logging.info("State file updated.")

def send_daily_summary():
    """Send a daily summary of all upcoming deadlines with completion status."""
    calendar_url = os.environ.get('MOODLE_CALENDAR_URL')
    bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    guild_id = os.environ.get('DISCORD_SERVER_ID')

    if not all([calendar_url, bot_token, guild_id]):
        logging.error("Missing environment variables.")
        return

    events = fetch_and_parse_events(calendar_url)
    if events is None:
        return

    # Load state for completion tracking
    state_file = 'data/state.json'
    state = {}
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError:
                state = {}

    # Check completions before generating summary
    bot_user = get_bot_user(bot_token)
    bot_user_id = bot_user['id'] if bot_user else None
    if bot_user_id and 'events' in state:
        if check_completions(bot_token, guild_id, bot_user_id, state):
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4)

    now = datetime.now(timezone.utc)
    local_tz = timezone(timedelta(hours=7))
    today_str = now.astimezone(local_tz).strftime('%d/%m/%Y')

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
        dl = e['deadline'].astimezone(local_tz).strftime('%d/%m %H:%M')
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

def send_progress_report():
    """Gửi báo cáo tiến độ deadline chi tiết vào channel #tien-do-deadline."""
    calendar_url = os.environ.get('MOODLE_CALENDAR_URL')
    bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    guild_id = os.environ.get('DISCORD_SERVER_ID')

    if not all([calendar_url, bot_token, guild_id]):
        logging.error("Missing environment variables.")
        return

    events = fetch_and_parse_events(calendar_url)
    if events is None:
        return

    # Load state
    state_file = 'data/state.json'
    state = {}
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError:
                state = {}

    # Check completions before reporting
    bot_user = get_bot_user(bot_token)
    bot_user_id = bot_user['id'] if bot_user else None
    if bot_user_id and 'events' in state:
        if check_completions(bot_token, guild_id, bot_user_id, state):
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4)

    now = datetime.now(timezone.utc)
    local_tz = timezone(timedelta(hours=7))
    now_str = now.astimezone(local_tz).strftime('%d/%m/%Y %H:%M')

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
            dl = e['deadline'].astimezone(local_tz).strftime('%d/%m %H:%M')
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

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--summary":
            send_daily_summary()
        elif sys.argv[1] == "--progress":
            send_progress_report()
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: python main.py [--summary | --progress]")
    else:
        main()

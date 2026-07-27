import os
import json
import logging
import requests
import re
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DISCORD_API_BASE = "https://discord.com/api/v10"

def get_headers(token):
    return {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }

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

def clean_channel_name(name):
    # Discord channel names must be lowercase, no spaces
    name = re.sub(r'[^a-zA-Z0-9-]', '-', name.lower())
    name = re.sub(r'-+', '-', name).strip('-')
    return name if name else "general"

def main():
    calendar_url = os.environ.get('MOODLE_CALENDAR_URL')
    bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    guild_id = os.environ.get('DISCORD_SERVER_ID')

    if not all([calendar_url, bot_token, guild_id]):
        logging.error("Missing environment variables: MOODLE_CALENDAR_URL, DISCORD_BOT_TOKEN, or DISCORD_SERVER_ID")
        return

    # 1. Fetch Calendar ICS
    try:
        logging.info("Fetching calendar ICS file...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(calendar_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            logging.error(f"Failed to load calendar. HTTP Status: {response.status_code}")
            return
            
        ics_data = response.text
    except Exception as e:
        logging.error(f"Error fetching calendar: {e}")
        return
        
    # 2. Parse ICS
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
            
            # Extract subject from category (e.g. CQ2526HK2_CSC10014_CQ2024/2 -> CSC10014)
            subject = category
            subj_match = re.search(r'_([A-Z]{3,4}\d{5})_', category)
            if subj_match:
                subject = subj_match.group(1)
            
            try:
                # dtend format is usually 20260722T165500Z
                dtend = datetime.strptime(dtend_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                events.append({
                    "uid": uid,
                    "summary": summary,
                    "deadline": dtend,
                    "subject": subject
                })
            except Exception as e:
                logging.error(f"Error parsing date {dtend_str}: {e}")

    # 3. Cache channels
    channels = get_guild_channels(bot_token, guild_id)
    channel_map = {c['name']: c['id'] for c in channels if c.get('type') == 0} # map name -> id

    # 4. Load state
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
        
    now = datetime.now(timezone.utc)
    state_changed = False
    
    # 5. Process events
    for event in events:
        eid = event['uid']
        # Initialize state for new event
        if eid not in state['events']:
            state['events'][eid] = {
                "notified_new": False,
                "reminded_3d": False,
                "reminded_1d": False
            }
        
        evt_state = state['events'][eid]
        time_left = event['deadline'] - now
        
        # We only care about events in the future
        if time_left.total_seconds() < 0:
            continue
            
        # Determine notification type
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
            chan_name = clean_channel_name(event['subject'])
            
            # Create channel if not exists
            if chan_name not in channel_map:
                new_channel = create_channel(bot_token, guild_id, chan_name)
                if new_channel:
                    channel_map[chan_name] = new_channel['id']
                else:
                    continue # Failed to create channel, skip
                    
            target_chan_id = channel_map[chan_name]
            
            # Build message URL
            event_url = "https://courses.fit.hcmus.edu.vn/calendar/view.php?view=upcoming"
            id_match = re.search(r'^(\d+)@', eid)
            if id_match:
                event_url = f"https://courses.fit.hcmus.edu.vn/calendar/view.php?view=day&course=1&time=upcoming#event_{id_match.group(1)}"
            
            # Format time
            local_tz = timezone(timedelta(hours=7)) # Vietnam Time
            deadline_local = event['deadline'].astimezone(local_tz).strftime('%d/%m/%Y %H:%M')
            
            if msg_type == "NEW":
                content = f"@everyone 🚨 **DEADLINE MỚI** 🚨\n\n📌 **Môn:** {event['subject']}\n📝 **Nội dung:** {event['summary']}\n⏰ **Hạn chót:** {deadline_local}\n🔗 **Xem:** {event_url}"
            elif msg_type == "3_DAYS":
                content = f"@everyone ⚠️ **NHẮC NHỞ: CÒN 3 NGÀY** ⚠️\n\n📌 **Môn:** {event['subject']}\n📝 **Nội dung:** {event['summary']}\n⏰ **Hạn chót:** {deadline_local}\n🔗 **Xem:** {event_url}"
            elif msg_type == "1_DAY":
                content = f"@everyone 🆘 **KHẨN CẤP: CÒN 24 GIỜ** 🆘\n\n📌 **Môn:** {event['subject']}\n📝 **Nội dung:** {event['summary']}\n⏰ **Hạn chót:** {deadline_local}\n🔗 **Xem:** {event_url}"
                
            send_message(bot_token, target_chan_id, content)

    if state_changed:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)
        logging.info("State file updated.")

if __name__ == "__main__":
    main()

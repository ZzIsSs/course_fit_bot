import logging
import re
import requests
from datetime import timedelta
from urllib.parse import quote as url_quote

from src.config import DISCORD_API_BASE, LOCAL_TZ

# ==================== HEADERS ====================

def get_headers(token):
    return {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }

# ==================== USER & CHANNELS ====================

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
        "type": 0  # 0 is Text Channel
    }
    response = requests.post(url, headers=get_headers(token), json=payload)
    if response.status_code == 201:
        logging.info(f"Created channel {channel_name}")
        return response.json()
    else:
        logging.error(f"Failed to create channel {channel_name}: {response.status_code} {response.text}")
        return None

def rename_channel(token, channel_id, new_name):
    """Đổi tên kênh Discord."""
    url = f"{DISCORD_API_BASE}/channels/{channel_id}"
    payload = {"name": new_name}
    response = requests.patch(url, headers=get_headers(token), json=payload)
    if response.status_code == 200:
        logging.info(f"Renamed channel {channel_id} → {new_name}")
        return response.json()
    else:
        logging.error(f"Failed to rename channel {channel_id}: {response.status_code} {response.text}")
        return None

def send_message(token, channel_id, content):
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
    payload = {"content": content}
    response = requests.post(url, headers=get_headers(token), json=payload)
    if response.status_code not in (200, 201):
        logging.error(f"Failed to send message: {response.status_code} {response.text}")
        return None
    return response.json()

# ==================== SCHEDULED EVENTS ====================

def create_scheduled_event(token, guild_id, event):
    """Tạo Discord Scheduled Event cho deadline mới."""
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}/scheduled-events"

    deadline_local = event['deadline'].astimezone(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')

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

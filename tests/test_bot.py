"""
Script test bot Discord — Dùng để debug và kiểm tra chức năng.

Chạy:
    1. Kiểm tra calendar URL trả về gì:
        python test_bot.py --check-calendar

    2. Test tạo kênh mới + gửi thông báo + tạo lịch Discord:
        python test_bot.py --test-create

    3. Dọn dẹp kênh test đã tạo:
        python test_bot.py --cleanup

Cần set biến môi trường trước khi chạy:
    $env:DISCORD_BOT_TOKEN="token_của_bot"
    $env:DISCORD_SERVER_ID="id_server"
    $env:MOODLE_CALENDAR_URL="link_calendar"   (chỉ cần cho --check-calendar)
"""

import os
import sys
import json
import requests
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import quote as url_quote

DISCORD_API_BASE = "https://discord.com/api/v10"

def get_headers(token):
    return {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }

# ==================== CHECK CALENDAR ====================

def check_calendar():
    """Fetch calendar URL và hiển thị tất cả events tìm được."""
    calendar_url = os.environ.get('MOODLE_CALENDAR_URL')
    if not calendar_url:
        print("❌ Thiếu biến MOODLE_CALENDAR_URL")
        return

    print(f"🔗 Đang fetch calendar từ URL...")
    print(f"   URL: {calendar_url[:80]}...")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(calendar_url, headers=headers, timeout=15)
        print(f"   HTTP Status: {response.status_code}")

        if response.status_code != 200:
            print(f"❌ Không fetch được calendar!")
            print(f"   Response: {response.text[:200]}")
            return

        ics_data = response.text
        print(f"   Kích thước: {len(ics_data)} bytes")
        print()

    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return

    # Parse events
    vevent_blocks = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', ics_data, re.DOTALL)
    print(f"📊 Tìm thấy {len(vevent_blocks)} event(s) trong ICS")
    print("=" * 60)

    now = datetime.now(timezone.utc)
    local_tz = timezone(timedelta(hours=7))

    for i, block in enumerate(vevent_blocks, 1):
        uid_match = re.search(r'\nUID:(.*?)\n', block)
        summary_match = re.search(r'\nSUMMARY:(.*?)\n', block)
        dtend_match = re.search(r'\nDTEND:(.*?)\n', block)
        dtstart_match = re.search(r'\nDTSTART:(.*?)\n', block)
        cat_match = re.search(r'\nCATEGORIES:(.*?)\n', block)

        uid = uid_match.group(1).strip() if uid_match else "N/A"
        summary = summary_match.group(1).strip() if summary_match else "N/A"
        dtend_str = dtend_match.group(1).strip() if dtend_match else "N/A"
        dtstart_str = dtstart_match.group(1).strip() if dtstart_match else "N/A"
        category = cat_match.group(1).strip() if cat_match else "N/A"

        # Parse subject
        subject = category
        subj_match = re.search(r'_([A-Z]{3,4}\d{5})_', category)
        if subj_match:
            subject = subj_match.group(1)

        # Parse deadline
        try:
            dtend = datetime.strptime(dtend_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            deadline_local = dtend.astimezone(local_tz).strftime('%d/%m/%Y %H:%M')
            time_left = dtend - now
            if time_left.total_seconds() < 0:
                status = "🔴 QUÁ HẠN"
            elif time_left <= timedelta(days=1):
                status = "🟠 < 24 giờ"
            elif time_left <= timedelta(days=3):
                status = "🟡 < 3 ngày"
            else:
                days = int(time_left.total_seconds() / 86400)
                status = f"🟢 Còn {days} ngày"
        except:
            deadline_local = dtend_str
            status = "⚪ Không parse được"

        print(f"\n📌 Event #{i}:")
        print(f"   UID:        {uid}")
        print(f"   Summary:    {summary}")
        print(f"   Category:   {category}")
        print(f"   Subject:    {subject}")
        print(f"   DTSTART:    {dtstart_str}")
        print(f"   DTEND:      {dtend_str}")
        print(f"   Deadline:   {deadline_local} (GMT+7)")
        print(f"   Trạng thái: {status}")

        # Show what channel name would be generated
        chan_name = re.sub(r'[^a-zA-Z0-9-]', '-', subject.lower())
        chan_name = re.sub(r'-+', '-', chan_name).strip('-')
        print(f"   Tên kênh:   #{chan_name}")

    if not vevent_blocks:
        print("\n⚠️ Không có event nào! Kiểm tra lại Calendar URL.")
        print("   Mẹo: Vào Moodle → Calendar → Export Calendar → Chọn 'All events'")
        print("         và copy lại URL mới.")

    print("\n" + "=" * 60)
    print(f"🕐 Thời gian hiện tại: {now.astimezone(local_tz).strftime('%d/%m/%Y %H:%M')} (GMT+7)")

    # Show raw ICS for debugging
    print("\n📄 Raw ICS data (first 2000 chars):")
    print("-" * 60)
    print(ics_data[:2000])

# ==================== TEST CREATE ====================

def test_create():
    """Test tạo kênh + gửi thông báo + tạo Scheduled Event với deadline giả."""
    bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    guild_id = os.environ.get('DISCORD_SERVER_ID')

    if not bot_token or not guild_id:
        print("❌ Thiếu DISCORD_BOT_TOKEN hoặc DISCORD_SERVER_ID")
        return

    headers = get_headers(bot_token)

    # Step 1: Check bot connection
    print("🤖 Kiểm tra kết nối bot...")
    r = requests.get(f"{DISCORD_API_BASE}/users/@me", headers=headers)
    if r.status_code != 200:
        print(f"❌ Bot không kết nối được! Status: {r.status_code}")
        print(f"   Response: {r.text}")
        return
    bot_info = r.json()
    print(f"✅ Bot: {bot_info['username']}#{bot_info.get('discriminator', '0')} (ID: {bot_info['id']})")

    # Step 2: Check guild access
    print(f"\n🏠 Kiểm tra server {guild_id}...")
    r = requests.get(f"{DISCORD_API_BASE}/guilds/{guild_id}/channels", headers=headers)
    if r.status_code != 200:
        print(f"❌ Không truy cập được server! Status: {r.status_code}")
        print(f"   Bot đã được mời vào server chưa?")
        return
    channels = r.json()
    text_channels = [c for c in channels if c.get('type') == 0]
    print(f"✅ Truy cập OK! Có {len(text_channels)} text channel(s):")
    for c in text_channels:
        print(f"   #{c['name']} (ID: {c['id']})")

    # Step 3: Create test channel
    test_channel_name = "test-bot-deadline"
    print(f"\n📢 Tạo kênh test: #{test_channel_name}...")

    existing = {c['name']: c['id'] for c in text_channels}
    if test_channel_name in existing:
        print(f"   Kênh #{test_channel_name} đã tồn tại, dùng kênh cũ.")
        channel_id = existing[test_channel_name]
    else:
        payload = {
            "name": test_channel_name,
            "type": 0,
            "topic": "🧪 Kênh test cho bot deadline — có thể xóa sau khi test"
        }
        r = requests.post(f"{DISCORD_API_BASE}/guilds/{guild_id}/channels", headers=headers, json=payload)
        if r.status_code == 201:
            channel_id = r.json()['id']
            print(f"✅ Đã tạo kênh #{test_channel_name} (ID: {channel_id})")
        else:
            print(f"❌ Không tạo được kênh! Status: {r.status_code}")
            print(f"   Response: {r.text}")
            return

    # Step 4: Send test notification
    print(f"\n📨 Gửi tin nhắn test...")
    now = datetime.now(timezone.utc)
    local_tz = timezone(timedelta(hours=7))
    fake_deadline = now + timedelta(days=2)
    deadline_str = fake_deadline.astimezone(local_tz).strftime('%d/%m/%Y %H:%M')

    content = (
        f"@everyone 🚨 **DEADLINE MỚI** 🚨 *(TEST)*\n\n"
        f"📌 **Môn:** TEST101\n"
        f"📝 **Nội dung:** Bài tập test bot deadline\n"
        f"⏰ **Hạn chót:** {deadline_str}\n"
        f"🔗 **Xem:** https://courses.fit.hcmus.edu.vn\n\n"
        f"✅ *React ✅ vào tin nhắn này khi đã hoàn thành!*"
    )
    payload = {"content": content}
    r = requests.post(f"{DISCORD_API_BASE}/channels/{channel_id}/messages", headers=headers, json=payload)
    if r.status_code in (200, 201):
        msg = r.json()
        msg_id = msg['id']
        print(f"✅ Đã gửi tin nhắn (ID: {msg_id})")

        # Add ✅ reaction
        emoji_encoded = url_quote("✅")
        react_url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{msg_id}/reactions/{emoji_encoded}/@me"
        react_headers = {"Authorization": f"Bot {bot_token}"}
        r2 = requests.put(react_url, headers=react_headers)
        if r2.status_code == 204:
            print(f"✅ Đã thêm reaction ✅")
        else:
            print(f"⚠️ Không thêm được reaction: {r2.status_code} {r2.text}")
    else:
        print(f"❌ Không gửi được tin nhắn! Status: {r.status_code}")
        print(f"   Response: {r.text}")

    # Step 5: Create Scheduled Event
    print(f"\n🗓️ Tạo Scheduled Event test...")
    event_payload = {
        "name": "📌 TEST101 — Bài tập test bot deadline",
        "privacy_level": 2,
        "scheduled_start_time": fake_deadline.isoformat(),
        "scheduled_end_time": (fake_deadline + timedelta(minutes=5)).isoformat(),
        "entity_type": 3,
        "entity_metadata": {"location": "https://courses.fit.hcmus.edu.vn"},
        "description": f"⏰ Hạn chót: {deadline_str} (GMT+7)\n📝 Bài tập test bot deadline\n🧪 Đây là event test, có thể xóa."
    }
    r = requests.post(f"{DISCORD_API_BASE}/guilds/{guild_id}/scheduled-events", headers=headers, json=event_payload)
    if r.status_code in (200, 201):
        event_data = r.json()
        print(f"✅ Đã tạo Scheduled Event (ID: {event_data['id']})")
        print(f"   Tên: {event_data['name']}")
        print(f"   Thời gian: {event_data['scheduled_start_time']}")

        # Save event ID for cleanup
        cleanup_data = {
            "test_channel_id": channel_id,
            "test_channel_name": test_channel_name,
            "test_event_id": event_data['id'],
            "test_message_id": msg_id if 'msg_id' in dir() else None
        }
        with open('data/test_cleanup.json', 'w') as f:
            json.dump(cleanup_data, f, indent=2)
        print(f"\n💾 Đã lưu thông tin cleanup vào data/test_cleanup.json")
    else:
        print(f"❌ Không tạo được Scheduled Event! Status: {r.status_code}")
        print(f"   Response: {r.text}")

    print(f"\n{'=' * 60}")
    print(f"🎉 Test hoàn tất! Kiểm tra Discord server để xem kết quả.")
    print(f"   - Kênh #{test_channel_name} với tin nhắn + reaction ✅")
    print(f"   - Scheduled Event ở thanh bên trái")
    print(f"\n🧹 Chạy 'python test_bot.py --cleanup' để dọn dẹp sau khi test.")

# ==================== CLEANUP ====================

def cleanup():
    """Xóa kênh test và scheduled event đã tạo."""
    bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    guild_id = os.environ.get('DISCORD_SERVER_ID')

    if not bot_token or not guild_id:
        print("❌ Thiếu DISCORD_BOT_TOKEN hoặc DISCORD_SERVER_ID")
        return

    headers = get_headers(bot_token)
    cleanup_file = 'data/test_cleanup.json'

    if not os.path.exists(cleanup_file):
        print("⚠️ Không tìm thấy file data/test_cleanup.json")
        print("   Có thể bạn chưa chạy --test-create hoặc đã cleanup rồi.")
        return

    with open(cleanup_file, 'r') as f:
        data = json.load(f)

    # Delete test channel
    if data.get('test_channel_id'):
        print(f"🗑️ Xóa kênh #{data.get('test_channel_name', '?')}...")
        r = requests.delete(f"{DISCORD_API_BASE}/channels/{data['test_channel_id']}", headers=headers)
        if r.status_code in (200, 204):
            print(f"✅ Đã xóa kênh")
        else:
            print(f"⚠️ Không xóa được: {r.status_code} {r.text}")

    # Delete scheduled event
    if data.get('test_event_id'):
        print(f"🗑️ Xóa Scheduled Event...")
        r = requests.delete(
            f"{DISCORD_API_BASE}/guilds/{guild_id}/scheduled-events/{data['test_event_id']}",
            headers=headers
        )
        if r.status_code in (200, 204):
            print(f"✅ Đã xóa Scheduled Event")
        else:
            print(f"⚠️ Không xóa được: {r.status_code} {r.text}")

    # Remove cleanup file
    os.remove(cleanup_file)
    print(f"\n🧹 Dọn dẹp xong!")

# ==================== MAIN ====================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("📋 Cách dùng:")
        print("   python test_bot.py --check-calendar   Kiểm tra calendar URL trả về gì")
        print("   python test_bot.py --test-create       Test tạo kênh + thông báo + lịch")
        print("   python test_bot.py --cleanup           Dọn dẹp kênh/event test")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "--check-calendar":
        check_calendar()
    elif cmd == "--test-create":
        test_create()
    elif cmd == "--cleanup":
        cleanup()
    else:
        print(f"❌ Lệnh không hợp lệ: {cmd}")

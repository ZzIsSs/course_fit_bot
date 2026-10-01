import logging
import re
import time
import requests
from datetime import datetime, timezone, timedelta
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

def create_channel(token, guild_id, channel_name, parent_id=None):
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}/channels"
    payload = {
        "name": channel_name,
        "type": 0  # 0 = Text Channel
    }
    if parent_id:
        payload["parent_id"] = parent_id
    response = requests.post(url, headers=get_headers(token), json=payload)
    if response.status_code == 201:
        loc = f" (trong category {parent_id})" if parent_id else ""
        logging.info(f"Created channel {channel_name}{loc}")
        return response.json()
    else:
        logging.error(f"Failed to create channel {channel_name}: {response.status_code} {response.text}")
        return None

def create_category(token, guild_id, category_name):
    """Tạo Category (nhóm kênh) mới trên Discord."""
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}/channels"
    payload = {"name": category_name, "type": 4}  # 4 = GUILD_CATEGORY
    response = requests.post(url, headers=get_headers(token), json=payload)
    if response.status_code == 201:
        logging.info(f"Created category '{category_name}'")
        return response.json()
    else:
        logging.error(f"Failed to create category '{category_name}': {response.status_code} {response.text}")
        return None

def resolve_category(token, guild_id, category_map, category_name):
    """Tìm category theo tên trong cache; nếu chưa có thì tạo mới trên Discord.
    
    category_map: dict {tên: id}, build 1 lần/lượt chạy (lọc type == 4 từ
    get_guild_channels) để tránh gọi API dư thừa và tránh tạo trùng category.
    """
    if category_name in category_map:
        return category_map[category_name]
    new_cat = create_category(token, guild_id, category_name)
    if new_cat:
        category_map[category_name] = new_cat['id']
        return new_cat['id']
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


# ==================== MESSAGE MANAGEMENT & DEDUPLICATION ====================

def _request_with_retry(method, url, max_retries=5, **kwargs):
    """Gửi HTTP request với cơ chế tự động retry khi gặp Discord Rate Limit (HTTP 429).
    
    Args:
        method (str): Phương thức HTTP (GET, POST, DELETE, ...).
        url (str): Endpoint URL.
        max_retries (int): Số lần thử lại tối đa khi bị Rate Limit. Mặc định 5.
        **kwargs: Tham số truyền thêm cho requests.request.
        
    Returns:
        requests.Response: Response từ server hoặc None nếu thất bại toàn bộ.
    """
    for attempt in range(max_retries):
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code == 429:
                retry_after = 1.0
                try:
                    data = resp.json()
                    retry_after = float(data.get("retry_after", 1.0))
                except Exception:
                    retry_after = float(resp.headers.get("Retry-After", 1.0))

                logging.warning(
                    f"Discord Rate Limit (429) khi gọi {method} {url}. "
                    f"Chờ {retry_after:.2f}s trước khi thử lại (lần {attempt + 1}/{max_retries})..."
                )
                time.sleep(retry_after + 0.1)
                continue
            return resp
        except requests.RequestException as e:
            logging.error(f"Lỗi mạng khi gọi {method} {url}: {e}")
            if attempt == max_retries - 1:
                return None
            time.sleep(1.0)
    return None


def get_channel_messages(token, channel_id, limit=100, before=None):
    """Lấy danh sách tin nhắn trong kênh theo thứ tự từ mới nhất đến cũ nhất.
    
    Hỗ trợ phân trang tự động nếu `limit > 100` (Discord API giới hạn tối đa 100 tin/request).
    
    Args:
        token (str): Discord Bot Token.
        channel_id (str): ID kênh Discord.
        limit (int): Tổng số tin nhắn tối đa cần lấy. Mặc định 100.
        before (str, optional): Message ID mốc để lấy các tin nhắn gửi trước nó.
        
    Returns:
        list[dict]: Danh sách tin nhắn (mới nhất ở đầu index 0, cũ nhất ở cuối).
    """
    messages = []
    current_before = before
    remaining = limit

    while remaining > 0:
        batch_limit = min(remaining, 100)
        url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages?limit={batch_limit}"
        if current_before:
            url += f"&before={current_before}"

        resp = _request_with_retry("GET", url, headers=get_headers(token))
        if not resp or resp.status_code != 200:
            status = resp.status_code if resp else "No Response"
            logging.error(f"Không thể lấy tin nhắn kênh {channel_id}: {status}")
            break

        batch = resp.json()
        if not batch:
            break

        messages.extend(batch)
        remaining -= len(batch)
        current_before = batch[-1]["id"]

        # Nếu số lượng trả về ít hơn batch_limit thì đã tới tin nhắn đầu tiên của kênh
        if len(batch) < batch_limit:
            break

    return messages


def delete_message(token, channel_id, message_id, delay=0.25):
    """Xóa một tin nhắn đơn lẻ trong kênh Discord.
    
    Bot luôn có quyền tự xóa tin nhắn của chính mình mà không cần quyền MANAGE_MESSAGES.
    Tự động xử lý Rate Limit (HTTP 429) và giữ khoảng nghỉ nhỏ giữa các request.
    
    Args:
        token (str): Discord Bot Token.
        channel_id (str): ID kênh Discord.
        message_id (str): ID tin nhắn cần xóa.
        delay (float): Khoảng nghỉ (giây) sau khi gọi API để phòng tránh Rate Limit. Mặc định 0.25s.
        
    Returns:
        bool: True nếu xóa thành công (hoặc tin đã bị xóa trước đó - 404), False nếu lỗi.
    """
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}"
    resp = _request_with_retry("DELETE", url, headers=get_headers(token))

    if delay > 0:
        time.sleep(delay)

    if not resp:
        return False

    if resp.status_code == 204:
        logging.debug(f"Đã xóa tin nhắn {message_id} trong kênh {channel_id}")
        return True
    elif resp.status_code == 404:
        logging.debug(f"Tin nhắn {message_id} không tồn tại hoặc đã bị xóa trước đó.")
        return True
    elif resp.status_code == 403:
        logging.error(f"Thiếu quyền xóa tin nhắn {message_id} trong kênh {channel_id} (403 Forbidden)")
        return False
    else:
        logging.error(f"Lỗi khi xóa tin nhắn {message_id}: {resp.status_code} {resp.text}")
        return False


def bulk_delete_messages(token, channel_id, message_ids):
    """Xóa hàng loạt tin nhắn trong kênh bằng Discord Bulk Delete API.
    
    Ràng buộc của Discord API:
    - Danh sách phải từ 2 đến 100 message IDs.
    - Không hỗ trợ tin nhắn cũ hơn 14 ngày (sẽ trả về 400 Bad Request).
    - Cần quyền MANAGE_MESSAGES. Nếu thiếu quyền sẽ trả về 403 Forbidden.
    
    Args:
        token (str): Discord Bot Token.
        channel_id (str): ID kênh Discord.
        message_ids (list[str]): Danh sách 2-100 ID tin nhắn cần xóa.
        
    Returns:
        tuple[bool, int, str]:
            - success (bool): True nếu bulk delete thành công.
            - status_code (int): HTTP status code trả về.
            - error_reason (str): Lý do lỗi ngắn gọn ('PERMISSION_DENIED', 'OLDER_THAN_14_DAYS', etc.)
    """
    if not message_ids or len(message_ids) < 2:
        return False, 400, "MIN_2_MESSAGES_REQUIRED"

    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages/bulk-delete"
    payload = {"messages": message_ids[:100]}

    resp = _request_with_retry("POST", url, headers=get_headers(token), json=payload)
    if not resp:
        return False, 0, "REQUEST_FAILED"

    if resp.status_code == 204:
        logging.info(f"Bulk delete thành công {len(payload['messages'])} tin nhắn trong kênh {channel_id}")
        return True, 204, ""
    elif resp.status_code == 403:
        logging.warning(f"Bot thiếu quyền MANAGE_MESSAGES để bulk delete trong kênh {channel_id}")
        return False, 403, "PERMISSION_DENIED"
    elif resp.status_code == 400:
        logging.warning(f"Bulk delete thất bại trong kênh {channel_id} (chứa tin nhắn >14 ngày): {resp.text}")
        return False, 400, "OLDER_THAN_14_DAYS"
    else:
        logging.error(f"Bulk delete lỗi: {resp.status_code} {resp.text}")
        return False, resp.status_code, "UNKNOWN_ERROR"


def is_message_under_14_days(message):
    """Kiểm tra xem tin nhắn có được gửi trong vòng 14 ngày qua không.
    
    Discord API cấm bulk delete các tin nhắn >= 14 ngày tuổi.
    
    Args:
        message (dict): Discord message object chứa trường 'timestamp'.
        
    Returns:
        bool: True nếu tin nhắn < 14 ngày tuổi (trừ thêm 5 phút buffer), ngược lại False.
    """
    ts_str = message.get("timestamp")
    if not ts_str:
        return False
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        # 14 ngày = 14 * 86400s. Trừ 300s (5 phút) buffer an toàn
        return (now - dt).total_seconds() < (14 * 86400 - 300)
    except Exception as e:
        logging.warning(f"Không thể parse timestamp '{ts_str}': {e}")
        return False


def filter_duplicate_bot_messages(messages, bot_user_id=None):
    """Lọc danh sách tin nhắn để phát hiện các tin nhắn trùng lặp do bot gửi.
    
    Tiêu chí xác định trùng lặp:
    1. Người gửi: Do chính bot gửi (author.id == bot_user_id hoặc author.bot == True).
    2. Tiêu chí trùng:
       - Cùng nội dung text (content.strip()), HOẶC
       - Cùng tiêu đề Embed (embed.title.strip()).
    3. Quy tắc giữ lại:
       - Danh sách `messages` sắp xếp từ mới nhất (index 0) đến cũ nhất.
       - Giữ lại DUY NHẤT 1 tin nhắn mới nhất gặp đầu tiên cho mỗi nội dung / tiêu đề embed.
       - Đưa tất cả các bản sao cũ hơn vào danh sách trùng lặp (duplicates) để xóa.
       
    Args:
        messages (list[dict]): Danh sách tin nhắn lấy từ API (mới nhất đến cũ nhất).
        bot_user_id (str, optional): ID user của bot để lọc chuẩn xác.
        
    Returns:
        tuple[list[dict], list[dict]]:
            - duplicates (list[dict]): Các tin nhắn trùng lặp cần xóa.
            - kept (list[dict]): Các tin nhắn mới nhất được giữ lại.
    """
    seen_contents = set()
    seen_embed_titles = set()

    duplicates = []
    kept = []

    for msg in messages:
        author = msg.get("author", {})
        author_id = author.get("id")
        is_bot = author.get("bot", False)

        # Chỉ xử lý tin nhắn do bot gửi
        if bot_user_id:
            if author_id != bot_user_id:
                continue
        elif not is_bot:
            continue

        content = (msg.get("content") or "").strip()
        embeds = msg.get("embeds") or []
        embed_titles = [
            (e.get("title") or "").strip()
            for e in embeds
            if (e.get("title") or "").strip()
        ]

        # Bỏ qua tin nhắn không có text lẫn embed title để tránh false positive
        if not content and not embed_titles:
            kept.append(msg)
            continue

        is_duplicate = False

        # Kiểm tra trùng nội dung text
        if content and content in seen_contents:
            is_duplicate = True

        # Kiểm tra trùng tiêu đề embed
        if not is_duplicate and embed_titles:
            for title in embed_titles:
                if title in seen_embed_titles:
                    is_duplicate = True
                    break

        if is_duplicate:
            duplicates.append(msg)
        else:
            # Ghi nhận là tin mới nhất cho nội dung/embed title này và giữ lại
            if content:
                seen_contents.add(content)
            for title in embed_titles:
                seen_embed_titles.add(title)
            kept.append(msg)

    return duplicates, kept


def deduplicate_channel_messages(token, channel_id, bot_user_id=None, scan_limit=100, dry_run=False):
    """Quét và dọn dẹp các tin nhắn trùng lặp của bot trong một kênh Discord.
    
    Quy trình xử lý:
    1. Lấy `scan_limit` tin nhắn gần nhất trong kênh (hỗ trợ phân trang).
    2. Lọc ra các tin trùng của bot, chỉ giữ lại 1 tin mới nhất.
    3. Nếu `dry_run=True`: Chỉ báo cáo, không xóa.
    4. Nếu `dry_run=False`:
       - Phân nhóm tin < 14 ngày và >= 14 ngày.
       - Thử dùng Bulk Delete cho tin < 14 ngày (lô 100 tin).
       - Tự động fallback sang Single Delete nếu Bulk Delete trả về 403 (thiếu quyền) hoặc 400.
       - Xóa đơn lẻ cho các tin >= 14 ngày hoặc tin lẻ.
       
    Args:
        token (str): Discord Bot Token.
        channel_id (str): ID kênh Discord.
        bot_user_id (str, optional): ID user của bot.
        scan_limit (int): Số lượng tin nhắn tối đa cần quét trong kênh. Mặc định 100.
        dry_run (bool): Nếu True thì chỉ mô phỏng, không thực hiện xóa thật.
        
    Returns:
        dict: Thống kê kết quả quét và xóa.
    """
    logging.info(f"Đang quét {scan_limit} tin nhắn gần nhất trong kênh {channel_id}...")
    messages = get_channel_messages(token, channel_id, limit=scan_limit)

    duplicates, kept = filter_duplicate_bot_messages(messages, bot_user_id)
    bot_total = len(duplicates) + len(kept)

    stats = {
        "channel_id": channel_id,
        "scanned": len(messages),
        "bot_messages": bot_total,
        "duplicates_found": len(duplicates),
        "deleted": 0,
        "failed": 0,
        "dry_run": dry_run
    }

    if not duplicates:
        logging.info(f"Kênh {channel_id}: Không phát hiện tin nhắn trùng lặp (Tổng tin bot: {bot_total}).")
        return stats

    logging.info(
        f"Kênh {channel_id}: Phát hiện {len(duplicates)}/{bot_total} tin nhắn bot trùng lặp. "
        f"Giữ lại {len(kept)} tin mới nhất."
    )

    if dry_run:
        logging.info(f"[DRY RUN] Bỏ qua xóa thật. {len(duplicates)} tin nhắn trùng lặp được giữ nguyên.")
        return stats

    bulk_candidates = []
    single_delete_candidates = []

    for msg in duplicates:
        if is_message_under_14_days(msg):
            bulk_candidates.append(msg["id"])
        else:
            single_delete_candidates.append(msg["id"])

    deleted_count = 0
    failed_count = 0

    # 1. Bulk Delete cho các tin < 14 ngày (batch 2 -> 100)
    while len(bulk_candidates) >= 2:
        chunk = bulk_candidates[:100]
        bulk_candidates = bulk_candidates[100:]

        success, status_code, reason = bulk_delete_messages(token, channel_id, chunk)
        if success:
            deleted_count += len(chunk)
        else:
            logging.info(f"Bulk delete không khả dụng ({reason}). Fallback sang xóa từng tin đơn lẻ...")
            for msg_id in chunk:
                if delete_message(token, channel_id, msg_id):
                    deleted_count += 1
                else:
                    failed_count += 1

    # Nếu còn sót 1 tin lẻ trong bulk_candidates
    if len(bulk_candidates) == 1:
        single_delete_candidates.append(bulk_candidates[0])
        bulk_candidates = []

    # 2. Xóa đơn lẻ cho các tin >= 14 ngày hoặc tin lẻ
    if single_delete_candidates:
        logging.info(f"Đang xóa đơn lẻ {len(single_delete_candidates)} tin nhắn (>14 ngày hoặc tin lẻ)...")
        for msg_id in single_delete_candidates:
            if delete_message(token, channel_id, msg_id):
                deleted_count += 1
            else:
                failed_count += 1

    stats["deleted"] = deleted_count
    stats["failed"] = failed_count
    logging.info(f"Kênh {channel_id}: Hoàn tất. Đã xóa: {deleted_count}, Lỗi: {failed_count}")
    return stats


# Mục 3: Tự động chia Thread thảo luận + Tự động tổ chức kênh theo Kỳ học

> Tổng hợp toàn bộ hướng triển khai đã bàn cho **Mục 3 — Tự động chia Thread để thảo luận bài tập** trong `ROADMAP.md`, mở rộng thêm phần tự động tổ chức kênh vào đúng category "kì học" phát sinh trong quá trình triển khai thực tế.
>
> ⚠️ Lưu ý số migration: trong lúc trao đổi có 2 file cùng bị đánh số `003`. File này **chuẩn hoá lại thứ tự đúng**: `003` = thread, `004` = category. Nếu Nguyên đã lỡ tạo file trùng số ở máy, đổi tên lại theo đúng thứ tự dưới đây trước khi chạy.

---

## 0. Mục tiêu gốc (trích ROADMAP.md)

> Mỗi khi có bài tập mới, bot tự động tạo một **Thread (luồng tin nhắn)** đính kèm với thông báo đó, giúp thành viên gửi tài liệu, đặt câu hỏi trực tiếp trong Thread mà không làm trôi channel chính.

Trong quá trình triển khai thực tế, phát sinh thêm 2 vấn đề cần giải quyết trước khi tính năng này chạy ổn định lâu dài:

1. Nguyên đã tự tay sắp xếp các kênh môn học vào category `kì 1` … `kì 5` — nhưng `create_channel()` gốc không hề gửi `parent_id`, nên channel mới bot tự tạo sau này sẽ luôn rơi ra ngoài gốc, phá cấu trúc.
2. Việc gán category cho từng môn bằng tay (`scripts/set_category.py`) khả thi nhưng tốn công — có thể tự động hoá bằng cách đọc thẳng năm/học kỳ đã mã hoá sẵn trong `shortname`/`CATEGORIES` do Moodle trả về.

Ba phần A, B, C dưới đây giải quyết lần lượt 3 vấn đề trên, và **thiết kế để cộng dồn vào nhau** — không phần nào ghi đè phần trước.

---

## Tổng quan file bị ảnh hưởng

| File | Thay đổi |
|---|---|
| `migrations/003_add_thread_id.sql` | **Mới** — cột `discord_thread_id` trên `deadlines` |
| `migrations/004_add_discord_category.sql` | **Mới** — cột `discord_category_id` trên `courses` |
| `src/moodle_parser.py` | Thêm `extract_semester_index()`; thêm `category_raw` vào event dict |
| `src/discord_api.py` | `create_channel()` nhận thêm `parent_id`; thêm `create_category()`, `resolve_category()`, `create_thread_from_message()` |
| `src/db_queries.py` | `update_deadline_discord_info()` nhận thêm `thread_id`; thêm `get_course_discord_category()`, `set_course_discord_category()` |
| `src/app.py` | `run_main_bot()` và `sync_channels()`: build thêm `category_map`, resolve category trước khi tạo channel, tạo thread khi gửi tin NEW |
| `src/announcement_tracker.py` | `_ensure_channel()` và 2 hàm gửi thông báo: nhận thêm `category_map`, `conn`, `semester_index` |
| `scripts/set_category.py` | **Mới** — lưới an toàn để gán tay category cho môn regex không nhận diện được |

---

## Phần A — Auto-thread khi có deadline mới

### A.1. Migration

`migrations/003_add_thread_id.sql`
```sql
-- Thêm cột lưu ID của Thread thảo luận được tự động tạo kèm mỗi deadline mới
ALTER TABLE deadlines ADD COLUMN IF NOT EXISTS discord_thread_id varchar(50);
```

### A.2. `src/discord_api.py` — hàm tạo thread

```python
def create_thread_from_message(token, channel_id, message_id, thread_name, auto_archive_duration=1440):
    """Tạo Thread đính kèm vào một tin nhắn có sẵn (dùng cho thảo luận bài tập).

    auto_archive_duration (phút): 60, 1440 (1 ngày), 4320 (3 ngày), 10080 (7 ngày).
    """
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}/threads"
    if len(thread_name) > 100:
        thread_name = thread_name[:97] + "..."
    payload = {"name": thread_name, "auto_archive_duration": auto_archive_duration}
    response = requests.post(url, headers=get_headers(token), json=payload)
    if response.status_code in (200, 201):
        result = response.json()
        logging.info(f"Created thread '{thread_name}' (ID: {result['id']})")
        return result
    else:
        logging.error(f"Failed to create thread: {response.status_code} {response.text}")
        return None
```

### A.3. `src/db_queries.py` — lưu thread_id

```python
def update_deadline_discord_info(conn, deadlines_id, message_id, channel_id, event_id=None, thread_id=None):
    """Cập nhật Discord message/channel/event/thread ID cho deadline."""
    execute(conn,
        """UPDATE deadlines
           SET discord_message_id = %s, discord_channel_id = %s,
               discord_event_id = %s, discord_thread_id = %s
           WHERE deadlines_id = %s""",
        (message_id, channel_id, event_id, thread_id, deadlines_id))
```

### A.4. Lưu ý quan trọng: không được reset ID cũ mỗi lần nhắc

Code gốc khởi tạo lại `sched_event_id = None` ở **mỗi lần** gửi tin (kể cả nhắc 3 ngày/1 ngày), nên nếu áp y hệt pattern đó cho `thread_id`, cái thread vừa tạo ở lần NEW sẽ bị "quên" ngay ở lần nhắc kế tiếp. Bản merge ở Phần D bên dưới đã sửa: lấy giá trị cũ từ `deadline` (dict fetch từ DB) làm mặc định, chỉ ghi đè khi thực sự tạo mới ở nhánh `NEW`.

### A.5. Quyền cần cấp cho bot

Vào Discord Developer Portal → bot role trong server → thêm quyền **"Create Public Threads"** (ngoài các quyền đã có: Tạo Channel, Quản lý Event, Gửi tin nhắn).

---

## Phần B — Tôn trọng cấu trúc category (kì học) đã sắp xếp thủ công

### B.1. Vấn đề

`create_channel()` gốc không gửi `parent_id` → channel mới luôn tạo ở gốc, không tự rơi vào đúng category `kì N` dù Nguyên đã sắp category đó sẵn. Các channel **đã tồn tại** thì không sao (bot nhận diện qua tên, không quan tâm vị trí) — chỉ channel **mới** mới bị ảnh hưởng.

### B.2. Migration

`migrations/004_add_discord_category.sql`
```sql
-- Lưu Category ID (kì học) trên Discord mà môn học này nên được xếp vào khi
-- bot tạo channel mới. NULL = tạo ở gốc như hành vi cũ (không phá gì cả).
ALTER TABLE courses ADD COLUMN IF NOT EXISTS discord_category_id varchar(50);
```

### B.3. `src/discord_api.py` — hỗ trợ `parent_id` + tự tìm/tạo category

```python
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
```

*(Bot đã có quyền "Tạo Channel" từ trước — category về bản chất cũng là 1 loại channel trên Discord API nên không cần xin thêm quyền gì.)*

### B.4. `src/db_queries.py` — getter/setter category

```python
def get_course_discord_category(conn, course_name):
    """Lấy Category ID đã gán cho môn học — dùng khi tạo channel mới.
    Trả về None nếu chưa gán (bot sẽ tạo ở gốc như hành vi cũ)."""
    row = fetch_one(conn,
        "SELECT discord_category_id FROM courses WHERE course_name = %s",
        (course_name,))
    return row['discord_category_id'] if row else None


def set_course_discord_category(conn, course_name, category_id):
    """Gán/ghi nhận Category ID cho môn học."""
    execute(conn,
        "UPDATE courses SET discord_category_id = %s WHERE course_name = %s",
        (category_id, course_name))
```

### B.5. Lưới an toàn thủ công — `scripts/set_category.py`

Dùng cho các môn mà Phần C (auto-detect) không nhận diện được pattern (VD: môn đại cương, mã lạ).

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_env
from src.database import get_db
from src.db_queries import set_course_discord_category, get_all_courses


def main():
    print("="*50)
    print(" GÁN CATEGORY DISCORD (KÌ HỌC) CHO MÔN HỌC")
    print("="*50)
    print("💡 Bật Developer Mode (Cài đặt > Nâng cao), chuột phải vào")
    print("   category (VD: 'kì 2') → Copy Category ID.\n")

    env = load_env()
    if not env:
        print("❌ Không tải được biến môi trường.")
        return

    with get_db(env['database_url']) as conn:
        courses = get_all_courses(conn)
        if not courses:
            print("❌ Chưa có môn nào trong DB. Chạy `python main.py --sync-channels` trước.")
            return

        print("📚 Các môn hiện có:")
        for c in courses:
            print(f"   - {c['course_name']} ({c.get('display_name') or 'chưa rõ tên'})")

        codes = [c.strip().upper() for c in
                 input("\n🔤 Nhập mã môn cần gán (cách nhau bởi dấu phẩy): ").split(',') if c.strip()]
        category_id = input("🔗 Nhập Category ID (kì học): ").strip()

        if not codes or not category_id.isdigit():
            print("❌ Thiếu mã môn hoặc Category ID không hợp lệ.")
            return

        for code in codes:
            set_course_discord_category(conn, code, category_id)
            print(f"   ✅ {code} → category {category_id}")

    print("\n🎉 Hoàn tất!")


if __name__ == "__main__":
    main()
```

---

## Phần C — Tự động phát hiện "kì mấy" từ mã Moodle

### C.1. Insight

Chuỗi mã gốc Moodle trả về (`shortname` của course, và field `CATEGORIES` trong `.ics`) có dạng `CQ2627HK1_CSC10012_CQ2026/1` — đã chứa sẵn năm học, học kỳ trong năm, và năm nhập học (khóa). Từ đó suy ra "kì thứ mấy" theo công thức:

```
kì = (năm_bắt_đầu_học_kỳ − năm_nhập_học) × 2 + số_học_kỳ_trong_năm
```

Ví dụ: `CQ2627HK1_..._CQ2026/1` → học kỳ 1, năm 2026-2027, khóa 2026 → `(2026−2026)×2+1 = kì 1`.

> ⚠️ **Chưa được xác nhận 100%** — pattern này suy từ ví dụ có sẵn trong docstring code cũ, có thể không đúng với môn đại cương (Toán, Ngoại ngữ...) do phòng ban khác quản lý format khác. **Trước khi tin tưởng hoàn toàn, chạy `python scripts/dump_moodle_data.py` để soi vài môn thật, đặc biệt môn đại cương**, rồi điều chỉnh regex nếu cần. Môn không khớp sẽ tự fallback về Phần B (gán tay), không có gì bị hỏng.

### C.2. `src/moodle_parser.py` — hàm tính kì

```python
def extract_semester_index(raw_code):
    """Tính 'kì thứ mấy' (học kỳ riêng của sinh viên, kì 1 = học kỳ đầu tiên nhập học)
    từ chuỗi mã gốc dạng 'CQ2627HK1_CSC10012_CQ2026/1'.

    Chỉ áp dụng cho HK1/HK2 (học kỳ chính). HK3 (hè) hoặc chuỗi không khớp
    pattern → trả None (bot sẽ fallback sang category đã gán tay, nếu có).
    """
    if not raw_code:
        return None
    match = re.search(r'CQ(\d{2})(\d{2})HK([123])_.*?_CQ(\d{4})/\d+', raw_code)
    if not match:
        return None
    start_yy, _end_yy, hk_str, cohort_year_str = match.groups()
    hk = int(hk_str)
    if hk not in (1, 2):
        return None
    academic_start_year = 2000 + int(start_yy)
    cohort_year = int(cohort_year_str)
    ky = (academic_start_year - cohort_year) * 2 + hk
    return ky if ky >= 1 else None
```

Cũng cần giữ lại chuỗi mã gốc trong event dict khi parse ICS (bản gốc chỉ lưu `subject` đã rút gọn, mất thông tin năm/kỳ):

```python
                events.append({
                    "uid": uid,
                    "summary": summary,
                    "deadline": dtend,
                    "subject": subject,
                    "category_raw": category,   # <-- thêm dòng này
                })
```

---

## Phần D — Bản hợp nhất cuối cùng (A + B + C cộng dồn)

Đây là bản **đầy đủ, đã merge** 3 phần trên vào từng file — dùng bản này để áp trực tiếp, khỏi phải tự cộng dồn diff qua nhiều bước.

### D.1. `src/app.py`

Import:
```python
from src.db_queries import (
    get_or_create_course, get_deadline_by_lms_id, insert_deadline,
    update_deadline_notified, update_deadline_discord_info,
    get_all_deadlines_with_course, insert_notification,
    update_course_chat_id, get_all_courses, get_course_display_name,
    get_course_discord_category, set_course_discord_category
)
from src.discord_api import (
    get_bot_user, get_guild_channels, create_channel, rename_channel,
    send_message, add_reaction, create_scheduled_event,
    create_thread_from_message, resolve_category
)
from src.moodle_parser import (
    fetch_and_parse_events, slugify_channel_name,
    extract_display_name, extract_subject, extract_semester_index
)
```

Trong `run_main_bot()` — build thêm `category_map` cùng lúc `channel_map`:
```python
    channels = get_guild_channels(bot_token, guild_id)
    channel_map = {c['name']: c['id'] for c in channels if c.get('type') == 0}
    category_map = {c['name']: c['id'] for c in channels if c.get('type') == 4}
```

Toàn bộ khối xử lý khi có `msg_type`:
```python
            if msg_type:
                display_name = get_course_display_name(conn, event['subject'])
                chan_name = slugify_channel_name(event['subject'], display_name)
                old_chan_name = slugify_channel_name(event['subject'])

                if chan_name in channel_map:
                    target_chan_id = channel_map[chan_name]
                elif old_chan_name in channel_map:
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

                event_url = _build_event_url(eid)
                deadline_local = event['deadline'].astimezone(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')
                completion_hint = "\n\n✅ *React ✅ vào tin nhắn này khi đã hoàn thành!*"

                # Nếu đã có Thread thảo luận từ lần báo NEW trước đó, gắn link vào nhắc nhở
                existing_thread_id = deadline.get('discord_thread_id')
                thread_hint = ""
                if existing_thread_id and msg_type != "NEW":
                    thread_hint = f"\n🧵 **Thảo luận:** https://discord.com/channels/{guild_id}/{existing_thread_id}"

                if msg_type == "NEW":
                    content = f"@everyone 🚨 **DEADLINE MỚI** 🚨\n\n📌 **Môn:** {event['subject']}\n📝 **Nội dung:** {event['summary']}\n⏰ **Hạn chót:** {deadline_local}\n🔗 **Xem:** {event_url}{completion_hint}"
                elif msg_type == "3_DAYS":
                    content = f"@everyone ⚠️ **NHẮC NHỞ: CÒN 3 NGÀY** ⚠️\n\n📌 **Môn:** {event['subject']}\n📝 **Nội dung:** {event['summary']}\n⏰ **Hạn chót:** {deadline_local}\n🔗 **Xem:** {event_url}{thread_hint}{completion_hint}"
                elif msg_type == "1_DAY":
                    content = f"@everyone 🆘 **KHẨN CẤP: CÒN 24 GIỜ** 🆘\n\n📌 **Môn:** {event['subject']}\n📝 **Nội dung:** {event['summary']}\n⏰ **Hạn chót:** {deadline_local}\n🔗 **Xem:** {event_url}{thread_hint}{completion_hint}"

                field_map = {"NEW": "notified_new", "3_DAYS": "reminded_3d", "1_DAY": "reminded_1d"}
                update_deadline_notified(conn, deadline['deadlines_id'], field_map[msg_type])

                msg_result = send_message(bot_token, target_chan_id, content)

                if msg_result:
                    add_reaction(bot_token, target_chan_id, msg_result['id'])

                    # Giữ nguyên event/thread ID cũ, chỉ tạo mới khi là thông báo NEW
                    sched_event_id = deadline.get('discord_event_id')
                    thread_id = existing_thread_id

                    if msg_type == "NEW":
                        sched_event = create_scheduled_event(bot_token, guild_id, event)
                        if sched_event:
                            sched_event_id = sched_event['id']

                        thread_name = f"💬 {event['summary']}"
                        thread = create_thread_from_message(bot_token, target_chan_id, msg_result['id'], thread_name)
                        if thread:
                            thread_id = thread['id']

                    update_deadline_discord_info(
                        conn, deadline['deadlines_id'],
                        msg_result['id'], target_chan_id, sched_event_id, thread_id
                    )

                    insert_notification(conn, 'deadline', content[:500], deadline['deadlines_id'])
```

Trong `sync_channels()` — build thêm `category_map`, nhánh tạo channel mới:
```python
    discord_channels = get_guild_channels(bot_token, guild_id)
    channel_map = {c['name']: c['id'] for c in discord_channels if c.get('type') == 0}
    category_map = {c['name']: c['id'] for c in discord_channels if c.get('type') == 4}
    channel_id_to_name = {c['id']: c['name'] for c in discord_channels if c.get('type') == 0}

    ...

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
```

### D.2. `src/announcement_tracker.py`

Import:
```python
from src.moodle_api import (
    get_site_info, get_enrolled_courses, get_course_contents,
    get_course_forums, get_forum_discussions
)
from src.moodle_parser import extract_subject, extract_display_name, slugify_channel_name, extract_semester_index
from src.discord_api import get_guild_channels, create_channel, send_message, rename_channel, resolve_category
from src.db_queries import (
    get_or_create_course, get_known_modules_for_course,
    upsert_module, has_modules, get_known_discussion_ids,
    insert_discussion, update_course_crawl_time,
    get_course_discord_category, set_course_discord_category
)
```

Trong `check_moodle_updates()` — thêm `semester_index` vào `course_info`:
```python
        db_course_id = get_or_create_course(
            conn, subject_code, lms_courses_id=course_id, display_name=display_name
        )
        update_course_crawl_time(conn, db_course_id)

        course_info = {
            'id': course_id,
            'db_id': db_course_id,
            'shortname': course_shortname,
            'fullname': course_fullname,
            'subject': subject_code,
            'display_name': display_name,
            'semester_index': extract_semester_index(course_shortname),
        }
```

Ở "Bước 6" — build thêm `category_map`, truyền `conn`:
```python
    channels = get_guild_channels(bot_token, guild_id)
    channel_map = {c['name']: c['id'] for c in channels if c.get('type') == 0}
    category_map = {c['name']: c['id'] for c in channels if c.get('type') == 4}

    for course_info, module in new_modules:
        _send_module_notification(bot_token, guild_id, channel_map, category_map, conn, course_info, module, is_update=False)

    for course_info, module in updated_modules:
        _send_module_notification(bot_token, guild_id, channel_map, category_map, conn, course_info, module, is_update=True)

    for course_info, disc in new_discussions:
        _send_discussion_notification(bot_token, guild_id, channel_map, category_map, conn, course_info, disc)
```

`_ensure_channel` — nhận `category_map`, `conn`, `semester_index`:
```python
def _ensure_channel(bot_token, guild_id, channel_map, category_map, conn, subject_code, display_name=None, semester_index=None):
    """Tìm hoặc tạo kênh Discord cho một môn học. Trả về channel_id hoặc None."""
    chan_name = slugify_channel_name(subject_code, display_name)

    if chan_name in channel_map:
        return channel_map[chan_name]

    old_chan_name = slugify_channel_name(subject_code)
    if old_chan_name in channel_map:
        old_id = channel_map[old_chan_name]
        if old_chan_name != chan_name:
            rename_channel(bot_token, old_id, chan_name)
            channel_map[chan_name] = old_id
            del channel_map[old_chan_name]
        return old_id

    if semester_index is not None:
        category_id = resolve_category(bot_token, guild_id, category_map, f"kì {semester_index}")
    else:
        category_id = get_course_discord_category(conn, subject_code)

    new_channel = create_channel(bot_token, guild_id, chan_name, parent_id=category_id)
    if new_channel:
        channel_map[chan_name] = new_channel['id']
        if category_id:
            set_course_discord_category(conn, subject_code, category_id)
        return new_channel['id']

    return None
```

`_send_module_notification` / `_send_discussion_notification` — cập nhật chữ ký + lời gọi:
```python
def _send_module_notification(bot_token, guild_id, channel_map, category_map, conn, course_info, module, is_update):
    channel_id = _ensure_channel(
        bot_token, guild_id, channel_map, category_map, conn,
        course_info['subject'], course_info.get('display_name'), course_info.get('semester_index')
    )
    if not channel_id:
        return
    # ... phần còn lại giữ nguyên như code gốc


def _send_discussion_notification(bot_token, guild_id, channel_map, category_map, conn, course_info, disc):
    channel_id = _ensure_channel(
        bot_token, guild_id, channel_map, category_map, conn,
        course_info['subject'], course_info.get('display_name'), course_info.get('semester_index')
    )
    if not channel_id:
        return
    # ... phần còn lại giữ nguyên như code gốc
```

---

## Checklist triển khai (theo đúng thứ tự)

1. [ ] Chạy `migrations/003_add_thread_id.sql` và `migrations/004_add_discord_category.sql` trên Supabase SQL Editor.
2. [ ] Vào Discord Developer Portal → cấp thêm quyền **"Create Public Threads"** cho bot.
3. [ ] Áp code Phần D vào `src/app.py`, `src/discord_api.py`, `src/db_queries.py`, `src/moodle_parser.py`, `src/announcement_tracker.py`.
4. [ ] Chạy `python scripts/dump_moodle_data.py`, kiểm tra `shortname` của **vài môn đại cương** (Toán, Ngoại ngữ...) xem có khớp pattern `CQ..HK.._MÃMÔN_CQ../..` không — báo lại nếu sai để chỉnh regex `extract_semester_index`.
5. [ ] Chạy thử qua GitHub Actions `workflow_dispatch` (mode `notify`) trên 1 deadline test — kiểm tra: channel mới (nếu có) tạo đúng category `kì N`, tin nhắn NEW có kèm Thread `💬 ...`.
6. [ ] Với môn không khớp regex (đại cương…), chạy `python scripts/set_category.py` để gán tay category — chỉ cần làm 1 lần cho mỗi môn.

---

## Việc còn để ngỏ / hướng mở rộng tiếp theo

- **Thread cho thông báo tài liệu/bài tập mới** phát hiện qua quét nội dung Moodle (`_send_module_notification` trong `announcement_tracker.py`) — hiện Phần A mới chỉ tạo thread cho deadline từ ICS (`app.py`), chưa áp dụng cho module mới phát hiện qua `core_course_get_contents`. Có thể làm tương tự nếu Nguyên cần.
- Roadmap mục 1 (Slash Commands) và mục 2 (Custom Deadlines) đã được bàn riêng ở phiên trao đổi sau, không nằm trong file này.
- Roadmap mục 5 (Role Management) và mục 6 (SaaS Scale) đã được Nguyên quyết định bỏ qua.

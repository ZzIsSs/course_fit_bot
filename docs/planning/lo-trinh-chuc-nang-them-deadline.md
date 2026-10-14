# Lộ trình: Chức năng "Thêm Deadline" qua Discord (`/add_deadline`)

> Mục tiêu (trích ROADMAP.md, mục 2 — Quản lý Deadline nội bộ): *"Cho phép thành viên dùng lệnh để thêm các mốc thời gian nội bộ (VD: 'Chốt chia việc đồ án', 'Họp nhóm tối nay'...). Bot sẽ quản lý, nhắc nhở và đưa các deadline này vào báo cáo tiến độ hằng ngày chung với deadline từ Moodle."*
>
> File này khác với `lo-trinh-them-lenh-deadline.md` (lệnh `/deadline` — **xem** danh sách). File này là lệnh `/add_deadline` — **thêm** deadline mới.

---

## 0. Quyết định kiến trúc cốt lõi

**Không để chính interaction handler tự gửi tin nhắn + tạo thread + tạo event + track reaction.** Lý do:
- Interaction endpoint chạy trên serverless (Vercel), Discord chỉ cho **3 giây** để trả lời — không đủ thời gian làm hết chuỗi việc đó.
- Tách biệt khỏi cron `main.py` trên GitHub Actions dễ sinh race-condition khi cần track `message_id` để theo dõi reaction ✅ sau này.

**Giải pháp:** `/add_deadline` chỉ làm đúng 1 việc — **ghi 1 dòng vào bảng `deadlines`** (giống hệt cấu trúc deadline từ Moodle, chỉ khác `source = 'manual'`). Cron `main.py` (chạy mỗi 30 phút) sẽ tự "nhặt" deadline này lên và chạy qua **y hệt pipeline đã có** (tạo channel đúng category, gửi tin NEW, tạo thread thảo luận, tạo scheduled event, gắn reaction, nhắc 3 ngày/1 ngày, vào báo cáo tổng kết/tiến độ) — không viết lại bất kỳ logic nào.

⚠️ **Phụ thuộc:** code merge ở mục 4 giả định đã áp dụng xong các thay đổi trong `muc3-thread-va-to-chuc-kenh-theo-ky.md` (auto-thread, `category_map`, `resolve_category`, `extract_semester_index`). Nếu chưa làm mục 3, làm mục 3 trước — code dưới đây build thẳng lên nó.

---

## Tổng quan file bị ảnh hưởng

| File | Thay đổi |
|---|---|
| `migrations/005_add_manual_deadline_support.sql` | **Mới** — cột `source`, `added_by` trên `deadlines` |
| `src/db_queries.py` | Thêm `get_pending_manual_deadlines()`, `insert_deadline_manual()`, `get_course_name_by_chat_id()` |
| `src/app.py` | `run_main_bot()`: gộp deadline thủ công vào chung vòng lặp xử lý; sửa nguồn `event_url` |
| `src/interactions.py` | **Mới** — xác thực chữ ký Discord + dispatch lệnh + handler `/add_deadline` |
| `api/interactions.py` | **Mới** — entry point HTTP cho Vercel |
| `scripts/register_commands.py` | **Mới** (hoặc mở rộng nếu đã có từ `/deadline`) — đăng ký lệnh `add_deadline` |
| `requirements.txt` | Thêm `pynacl` |

> Số migration `005` nối tiếp `003` (thread) và `004` (category) đã đánh trong file mục 3, tránh trùng số.

---

## 1. Migration

`migrations/005_add_manual_deadline_support.sql`
```sql
ALTER TABLE deadlines ADD COLUMN IF NOT EXISTS source varchar(20) NOT NULL DEFAULT 'moodle';
ALTER TABLE deadlines ADD COLUMN IF NOT EXISTS added_by varchar(100);
```

---

## 2. `src/db_queries.py` — 3 hàm mới

```python
def get_pending_manual_deadlines(conn):
    """Deadline thêm qua /add_deadline, chưa từng được cron xử lý lần đầu."""
    return fetch_all(conn,
        """SELECT d.*, c.course_name
           FROM deadlines d
           JOIN courses c ON d.courses_id = c.courses_id
           WHERE d.source = 'manual' AND d.notified_new = false""")


def insert_deadline_manual(conn, courses_id, deadline_name, lms_deadlines_id, due_time, source_url, added_by):
    """ON CONFLICT DO NOTHING: an toàn nếu Discord gửi lặp interaction (retry)."""
    row = fetch_one(conn,
        """INSERT INTO deadlines (courses_id, deadline_name, lms_deadlines_id, due_time, source_url, source, added_by)
           VALUES (%s, %s, %s, %s, %s, 'manual', %s)
           ON CONFLICT (lms_deadlines_id) DO NOTHING
           RETURNING deadlines_id""",
        (courses_id, deadline_name, lms_deadlines_id, due_time, source_url, added_by))
    return row['deadlines_id'] if row else None


def get_course_name_by_chat_id(conn, chat_id):
    """Tự nhận diện môn học dựa vào kênh đang gõ lệnh — khỏi cần gõ mã môn."""
    row = fetch_one(conn, "SELECT course_name FROM courses WHERE chat_id = %s", (str(chat_id),))
    return row['course_name'] if row else None
```

---

## 3. `src/interactions.py` — xác thực + xử lý lệnh (mới)

```python
import os
from datetime import datetime, timezone

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from src.database import get_db
from src.db_queries import get_or_create_course, insert_deadline_manual, get_course_name_by_chat_id
from src.config import LOCAL_TZ

DISCORD_PUBLIC_KEY = os.environ.get('DISCORD_PUBLIC_KEY')


def verify_signature(signature, timestamp, body):
    if not DISCORD_PUBLIC_KEY:
        return False
    try:
        VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY)).verify(
            f'{timestamp}{body}'.encode(), bytes.fromhex(signature))
        return True
    except (BadSignatureError, Exception):
        return False


def handle_interaction(interaction, database_url):
    command_name = interaction.get('data', {}).get('name')
    if command_name == 'add_deadline':
        return _handle_add_deadline(interaction, database_url)
    return _ephemeral("❌ Lệnh chưa được hỗ trợ.")


def _get_option(options, name):
    for opt in options or []:
        if opt.get('name') == name:
            return opt.get('value')
    return None


def _parse_due_time(text):
    """'25/12/2026 23:59' hoặc '25/12 23:59' (giờ VN) → datetime UTC."""
    text = text.strip()
    now_local = datetime.now(LOCAL_TZ)
    for fmt, has_year in (("%d/%m/%Y %H:%M", True), ("%d/%m %H:%M", False)):
        try:
            dt = datetime.strptime(text, fmt)
            if not has_year:
                dt = dt.replace(year=now_local.year)
            return dt.replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def _handle_add_deadline(interaction, database_url):
    options = interaction.get('data', {}).get('options', [])
    channel_id = interaction.get('channel_id')
    username = (interaction.get('member') or {}).get('user', {}).get('username', 'Unknown')

    name = _get_option(options, 'ten')
    due_time = _parse_due_time(_get_option(options, 'han_chot') or '')
    course_input = _get_option(options, 'mon')

    if not name or due_time is None:
        return _ephemeral("❌ Hạn chót sai định dạng. Ví dụ: `25/12/2026 23:59`.")

    with get_db(database_url) as conn:
        course_name = course_input.strip().upper() if course_input else get_course_name_by_chat_id(conn, channel_id)
        if not course_name:
            return _ephemeral("❌ Không xác định được môn. Dùng lệnh trong kênh của môn, hoặc điền option `mon`.")

        courses_id = get_or_create_course(conn, course_name)
        insert_deadline_manual(
            conn, courses_id, name, f"manual-{interaction['id']}", due_time,
            source_url=f"Discord (thêm bởi {username})", added_by=username
        )

    due_local = due_time.astimezone(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')
    return _ephemeral(
        f"✅ Đã lưu deadline nội bộ!\n📚 Môn: **{course_name}**\n📝 {name}\n⏰ {due_local}\n\n"
        f"Bot sẽ thông báo vào kênh môn trong tối đa 30 phút và nhắc nhở như deadline thường."
    )


def _ephemeral(text):
    return {"type": 4, "data": {"content": text, "flags": 64}}
```

---

## 4. `src/app.py` — gộp deadline thủ công vào pipeline có sẵn

Import bổ sung (nối tiếp bản đã merge trong mục 3):
```python
from src.db_queries import (
    get_or_create_course, get_deadline_by_lms_id, insert_deadline,
    update_deadline_notified, update_deadline_discord_info,
    get_all_deadlines_with_course, insert_notification,
    update_course_chat_id, get_all_courses, get_course_display_name,
    get_course_discord_category, set_course_discord_category,
    get_pending_manual_deadlines
)
```

Đầu `run_main_bot()` — nếu ICS lỗi thì vẫn tiếp tục xử lý deadline thủ công thay vì thoát sớm:
```python
    events = fetch_and_parse_events(calendar_url)
    if events is None:
        logging.warning("Không tải được ICS, vẫn tiếp tục xử lý deadline thủ công (nếu có).")
        events = []
```

Bên trong `with get_db(...) as conn:` — gộp danh sách deadline thủ công vào cùng vòng lặp events đã có, và sửa nguồn `event_url`:
```python
        now = datetime.now(timezone.utc)

        # Gộp deadline thêm qua /add_deadline vào cùng pipeline xử lý deadline từ Moodle
        manual_rows = get_pending_manual_deadlines(conn)
        manual_events = [{
            "uid": row['lms_deadlines_id'],
            "summary": row['deadline_name'],
            "deadline": _ensure_tz(row['due_time']),
            "subject": row['course_name'],
        } for row in manual_rows]

        for event in events + manual_events:
            eid = event['uid']

            deadline = get_deadline_by_lms_id(conn, eid)

            if not deadline:
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
                        category_id = get_course_discord_category(conn, event['subject'])

                    new_channel = create_channel(bot_token, guild_id, chan_name, parent_id=category_id)
                    if new_channel:
                        channel_map[chan_name] = new_channel['id']
                        target_chan_id = new_channel['id']
                        if category_id:
                            set_course_discord_category(conn, event['subject'], category_id)
                    else:
                        continue

                # Dùng source_url đã lưu sẵn trong DB thay vì tự build lại từ uid —
                # deadline thủ công có uid dạng "manual-..." không khớp pattern Moodle,
                # tự build lại sẽ ra link sai.
                event_url = deadline['source_url']
                deadline_local = event['deadline'].astimezone(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')
                completion_hint = "\n\n✅ *React ✅ vào tin nhắn này khi đã hoàn thành!*"

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

**Không cần sửa gì** ở `send_daily_summary()` / `send_progress_report()` — cả 2 hàm này đã đọc từ `get_all_deadlines_with_course()`, tự động bao gồm deadline thủ công ngay khi có dòng trong bảng `deadlines`.

---

## 5. `api/interactions.py` — entry point cho Vercel (mới)

```python
import os, sys, json
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.interactions import verify_signature, handle_interaction

DATABASE_URL = os.environ.get('DATABASE_URL')


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8')
        sig = self.headers.get('X-Signature-Ed25519', '')
        ts = self.headers.get('X-Signature-Timestamp', '')

        if not verify_signature(sig, ts, body):
            self.send_response(401)
            self.end_headers()
            return

        interaction = json.loads(body)
        result = {"type": 1} if interaction.get('type') == 1 else handle_interaction(interaction, DATABASE_URL)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode('utf-8'))
```

---

## 6. `scripts/register_commands.py` — đăng ký lệnh (mới)

```python
import os, requests

APPLICATION_ID = os.environ.get('DISCORD_APPLICATION_ID')
BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

COMMANDS = [{
    "name": "add_deadline",
    "description": "Thêm deadline nội bộ (không có trên Moodle)",
    "options": [
        {"name": "ten", "description": "Tên công việc", "type": 3, "required": True},
        {"name": "han_chot", "description": "dd/mm/yyyy HH:MM", "type": 3, "required": True},
        {"name": "mon", "description": "Mã môn (bỏ trống nếu đang chat trong kênh môn đó)", "type": 3, "required": False},
    ]
}]

resp = requests.put(
    f"https://discord.com/api/v10/applications/{APPLICATION_ID}/commands",
    headers={"Authorization": f"Bot {BOT_TOKEN}"}, json=COMMANDS
)
print("✅ OK" if resp.status_code == 200 else f"❌ {resp.status_code} {resp.text}")
```

> ⚠️ Nếu sau này cũng làm lệnh `/deadline` (xem danh sách — file `lo-trinh-them-lenh-deadline.md`), **phải khai báo cả 2 lệnh trong cùng `COMMANDS`** khi chạy script này, vì Discord `PUT` ghi đè toàn bộ danh sách lệnh, thiếu cái nào sẽ bị xoá mất cái đó.

---

## Việc cần làm để lên hạ tầng

1. [ ] Thêm `pynacl` vào `requirements.txt`.
2. [ ] Tạo project trên Vercel, **link cùng repo hiện tại** (không cần repo riêng — thư mục `api/` là convention Vercel tự nhận diện, dùng chung được `src/` sẵn có).
3. [ ] Vào Discord Developer Portal → app của bot → copy **Public Key** (khác Bot Token) và **Application ID**.
4. [ ] Set biến môi trường trên Vercel: `DATABASE_URL`, `DISCORD_PUBLIC_KEY`, `DISCORD_APPLICATION_ID`.
5. [ ] Deploy xong, dán URL (`https://<project>.vercel.app/api/interactions`) vào ô **"Interactions Endpoint URL"** trong Developer Portal — Discord gửi PING xác thực, endpoint trả `{"type":1}` là pass.
6. [ ] Kiểm tra OAuth2 scope của bot khi mời vào server đã có `applications.commands` chưa — nếu invite link cũ chỉ có `bot`, cần re-invite thêm scope này thì slash command mới hiện ra trong server.
7. [ ] Chạy `python scripts/register_commands.py` (1 lần) để đăng ký `/add_deadline`.
8. [ ] Chạy migration `005_add_manual_deadline_support.sql` trên Supabase.

---

## Checklist kiểm thử

1. [ ] Gõ `/add_deadline ten:"Test deadline" han_chot:"25/12/2026 23:59"` trong 1 kênh môn cụ thể → nhận phản hồi ephemeral xác nhận đã lưu.
2. [ ] Gõ lệnh tương tự nhưng **ngoài** kênh môn nào và không điền `mon` → kỳ vọng bot báo lỗi "Không xác định được môn".
3. [ ] Gõ lại với option `mon:CSC10014` khi đang ở kênh khác → kỳ vọng lưu đúng vào môn được chỉ định dù không ở đúng kênh.
4. [ ] Chạy `python main.py` (hoặc `workflow_dispatch` mode `notify`) → kiểm tra kênh môn nhận được tin "DEADLINE MỚI" kèm Thread thảo luận (nếu đã áp mục 3).
5. [ ] Chạy `python main.py --progress` → xác nhận deadline thủ công xuất hiện trong báo cáo tiến độ, chung với deadline Moodle.
6. [ ] Gõ nhập sai định dạng ngày (VD: `2026-12-25`) → kỳ vọng bot báo lỗi định dạng thay vì crash.

---

## Đánh đổi & hạn chế hiện tại

- **Độ trễ tối đa 30 phút** trước khi deadline thủ công thực sự được thông báo (theo lịch cron) — không tức thì. Đổi lại code an toàn tuyệt đối, tái dùng 100% pipeline đã kiểm chứng, không có race-condition giữa serverless và cron.
- **Vị trí (location) của Scheduled Event** có thể không chính xác với deadline thủ công: `create_scheduled_event()` trong `discord_api.py` tự build link Moodle từ `uid` bằng regex `^(\d+)@`, còn uid thủ công có dạng `manual-...` nên sẽ rơi về link lịch Moodle chung chung thay vì link cụ thể. Không ảnh hưởng chức năng, chỉ là chi tiết nhỏ — có thể cải thiện sau bằng cách sửa `create_scheduled_event` nhận `location` tùy chỉnh từ `deadline['source_url']` nếu Nguyên muốn chuẩn hơn.

### Hướng mở rộng: bắn thông báo tức thì thay vì chờ 30 phút

Nếu muốn deadline thủ công được thông báo ngay lập tức thay vì chờ cron kế tiếp, có thể thêm bước gọi GitHub API `workflow_dispatch` ngay sau khi insert thành công trong `_handle_add_deadline`:

```python
import requests

def _trigger_workflow_now(github_token, repo):
    requests.post(
        f"https://api.github.com/repos/{repo}/actions/workflows/notify.yml/dispatches",
        headers={"Authorization": f"token {github_token}"},
        json={"ref": "main", "inputs": {"mode": "notify"}}
    )
```
Cần thêm `GITHUB_TOKEN` (Personal Access Token, scope `actions:write`) và `GITHUB_REPO` (`owner/repo`) vào env Vercel. Chưa triển khai trong bản này — chỉ là hướng mở rộng nếu Nguyên thấy độ trễ 30 phút gây khó chịu.

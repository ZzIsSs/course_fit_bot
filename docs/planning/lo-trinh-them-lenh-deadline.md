# Lộ trình thêm lệnh `/deadline`

> Mục tiêu (trích ROADMAP.md, mục 1): *"`/deadline`: Liệt kê ngay lập tức các bài tập và hạn chót sắp tới."*
>
> Lệnh này **dùng chung hạ tầng interaction endpoint** đã dựng khi làm `/add_deadline` (Vercel + xác thực chữ ký Discord + dispatch table trong `src/interactions.py`). Nếu hạ tầng đó chưa deploy, xem mục 0 trước.

---

## 0. Điều kiện tiên quyết

Nếu đã deploy `/add_deadline` thành công thì bỏ qua mục này.

- [ ] Project Vercel đã link với repo, có `api/interactions.py` chạy được.
- [ ] Đã set env `DATABASE_URL`, `DISCORD_PUBLIC_KEY`, `DISCORD_APPLICATION_ID` trên Vercel.
- [ ] URL `https://<project>.vercel.app/api/interactions` đã dán vào **Interactions Endpoint URL** trong Discord Developer Portal và pass được PING xác thực.
- [ ] Bot đã được invite với scope `applications.commands` (không chỉ `bot`).

---

## Tổng quan file bị ảnh hưởng

| File | Thay đổi |
|---|---|
| `src/utils.py` | **Mới** — tách `ensure_tz()` ra dùng chung giữa `app.py` và `interactions.py` |
| `src/app.py` | Xoá hàm `_ensure_tz` cục bộ, import từ `src.utils` thay thế |
| `src/db_queries.py` | Thêm `get_deadlines_for_course_or_all()` |
| `src/interactions.py` | Thêm handler `_handle_deadline`, gắn vào dispatch table |
| `scripts/register_commands.py` | Thêm định nghĩa lệnh `deadline` vào `COMMANDS` |

Không cần migration mới — tái sử dụng bảng `deadlines` sẵn có.

---

## 1. Thiết kế hành vi & option

```
/deadline [mon] [so_luong]
```

| Option | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `mon` | STRING | Không | Mã môn cụ thể. Bỏ trống → tự nhận diện theo kênh đang gõ lệnh (giống `/add_deadline`); nếu kênh không gắn với môn nào (VD: `#tong-ket-deadline`) → hiện tất cả các môn. |
| `so_luong` | INTEGER | Không | Số lượng deadline hiển thị, mặc định `5`, tối đa `15`. |

**Quyết định thiết kế cần Nguyên biết:**
- Trả lời dạng **ephemeral** (flag `64` — chỉ người gõ lệnh thấy), giống `/add_deadline`, để tránh spam channel mỗi lần ai đó tra deadline. Nếu muốn công khai cho cả kênh thấy, chỉ cần bỏ `flags: 64` ở hàm `_ephemeral` khi build response — sẽ ghi chú rõ chỗ này ở bước 4.
- Lọc **theo thời gian ở Python**, không dùng `WHERE due_time >= NOW()` trong SQL — vì cột `due_time` là `TIMESTAMP` không kèm timezone (xem `migrations/NOTES.md`), so sánh trực tiếp với `NOW()` (vốn có timezone) của Postgres dễ lệch giờ tuỳ session timezone. Cách này giữ nhất quán với cách `app.py` và `send_daily_summary` đang xử lý.

---

## 2. `src/utils.py` — tách hàm dùng chung (mới)

Hàm `_ensure_tz` hiện đang nằm cục bộ trong `src/app.py`. `interactions.py` cũng cần hàm này để tính deadline nào đã qua hạn — tách ra module riêng để 2 nơi dùng chung, tránh copy-paste logic timezone (dễ lệch nếu sửa 1 chỗ quên chỗ kia).

```python
from datetime import timezone


def ensure_tz(dt):
    """Đảm bảo datetime có timezone (mặc định UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
```

Trong `src/app.py`, xoá định nghĩa `_ensure_tz` cục bộ, thay bằng:
```python
from src.utils import ensure_tz as _ensure_tz
```
*(giữ alias `_ensure_tz` để không phải sửa các chỗ gọi hiện có trong `send_daily_summary`/`send_progress_report`.)*

---

## 3. `src/db_queries.py` — query lấy deadline theo môn hoặc tất cả

```python
def get_deadlines_for_course_or_all(conn, course_name=None):
    """Lấy deadline kèm course_name, lọc theo môn nếu có.
    Việc lọc theo thời gian/đã hoàn thành thực hiện ở Python (xem src/utils.py)
    để nhất quán với phần còn lại của code, tránh lệch timezone.
    """
    if course_name:
        return fetch_all(conn,
            """SELECT d.*, c.course_name
               FROM deadlines d
               JOIN courses c ON d.courses_id = c.courses_id
               WHERE c.course_name = %s
               ORDER BY d.due_time""",
            (course_name,))
    return get_all_deadlines_with_course(conn)  # đã có sẵn, cùng ORDER BY due_time
```

---

## 4. `src/interactions.py` — handler mới

Import bổ sung ở đầu file:
```python
from src.db_queries import (
    get_or_create_course, insert_deadline_manual, get_course_name_by_chat_id,
    get_deadlines_for_course_or_all
)
from src.utils import ensure_tz
from src.config import LOCAL_TZ
```

Gắn vào dispatch table:
```python
def handle_interaction(interaction, database_url):
    command_name = interaction.get('data', {}).get('name')
    if command_name == 'add_deadline':
        return _handle_add_deadline(interaction, database_url)
    if command_name == 'deadline':
        return _handle_deadline(interaction, database_url)
    return _ephemeral("❌ Lệnh chưa được hỗ trợ.")
```

Handler chính:
```python
def _handle_deadline(interaction, database_url):
    options = interaction.get('data', {}).get('options', [])
    channel_id = interaction.get('channel_id')

    course_input = _get_option(options, 'mon')
    limit = _get_option(options, 'so_luong') or 5
    limit = max(1, min(int(limit), 15))

    with get_db(database_url) as conn:
        course_name = course_input.strip().upper() if course_input else get_course_name_by_chat_id(conn, channel_id)
        rows = get_deadlines_for_course_or_all(conn, course_name)

    now = datetime.now(timezone.utc)
    upcoming = [d for d in rows if not d['completed'] and ensure_tz(d['due_time']) >= now]
    upcoming.sort(key=lambda d: d['due_time'])
    upcoming = upcoming[:limit]

    scope_label = f"— {course_name}" if course_name else "— tất cả các môn"

    if not upcoming:
        return _ephemeral(f"✅ Không có deadline sắp tới nào {scope_label}.")

    lines = [f"📅 **DEADLINE SẮP TỚI {scope_label}**"]
    for d in upcoming:
        due_local = ensure_tz(d['due_time']).astimezone(LOCAL_TZ).strftime('%d/%m %H:%M')
        lines.append(f"▸ [{d['course_name']}] {d['deadline_name']} — ⏰ {due_local}")

    # Đổi flags: 64 -> bỏ dòng này nếu muốn cả kênh thấy thay vì chỉ người gõ lệnh
    return _ephemeral("\n".join(lines))
```

*(`_get_option` và `_ephemeral` đã có sẵn từ lúc làm `/add_deadline`, dùng lại nguyên vẹn.)*

---

## 5. `scripts/register_commands.py` — đăng ký lệnh mới

⚠️ Discord `PUT .../commands` là **ghi đè toàn bộ danh sách**, nên phải khai báo **cả `add_deadline` lẫn `deadline`** trong cùng 1 lần chạy — thiếu cái nào sẽ bị xoá mất cái đó.

```python
COMMANDS = [
    {
        "name": "add_deadline",
        "description": "Thêm deadline nội bộ (không có trên Moodle)",
        "options": [
            {"name": "ten", "description": "Tên công việc", "type": 3, "required": True},
            {"name": "han_chot", "description": "dd/mm/yyyy HH:MM", "type": 3, "required": True},
            {"name": "mon", "description": "Mã môn (bỏ trống nếu đang chat trong kênh môn đó)", "type": 3, "required": False},
        ]
    },
    {
        "name": "deadline",
        "description": "Xem các deadline sắp tới",
        "options": [
            {"name": "mon", "description": "Mã môn (bỏ trống để tự nhận theo kênh, hoặc xem tất cả)", "type": 3, "required": False},
            {"name": "so_luong", "description": "Số lượng hiển thị (mặc định 5, tối đa 15)", "type": 4, "required": False, "min_value": 1, "max_value": 15},
        ]
    },
]
```
*(phần còn lại của file — gọi `requests.put(...)` — giữ nguyên như bản đã có.)*

---

## Checklist triển khai

1. [ ] Tạo `src/utils.py`, sửa `src/app.py` dùng import mới — chạy thử `python main.py --summary` để chắc chắn không lỗi import.
2. [ ] Thêm `get_deadlines_for_course_or_all` vào `src/db_queries.py`.
3. [ ] Cập nhật `src/interactions.py` theo mục 4, deploy lại lên Vercel.
4. [ ] Cập nhật `COMMANDS` trong `scripts/register_commands.py`, chạy `python scripts/register_commands.py` **1 lần** để đăng ký cả 2 lệnh.
5. [ ] Test trong kênh 1 môn cụ thể (VD: `#ctdlvgt-csc10004`) → gõ `/deadline` → kỳ vọng chỉ hiện deadline môn đó.
6. [ ] Test trong kênh không thuộc môn nào (VD: `#tong-ket-deadline`) → gõ `/deadline` → kỳ vọng hiện tối đa 5 deadline gần nhất trên tất cả các môn.
7. [ ] Test `/deadline mon:CSC10014` → ép xem đúng môn dù đang ở kênh khác.
8. [ ] Test `/deadline so_luong:15` → xem tối đa 15 kết quả.
9. [ ] Test khi không còn deadline nào sắp tới → bot trả đúng câu "Không có deadline nào".

---

## Hướng mở rộng sau này (chưa làm)

- Nếu danh sách dài vượt quá không gian hiển thị gọn (nhiều hơn ~15 dòng), có thể chuyển sang **embed + nút bấm phân trang** thay vì text thuần — hiện chưa cần vì đã giới hạn `so_luong` tối đa 15.
- Có thể thêm cờ `cong_khai:true` làm option BOOLEAN để người dùng tự chọn ephemeral hay công khai thay vì cố định trong code.

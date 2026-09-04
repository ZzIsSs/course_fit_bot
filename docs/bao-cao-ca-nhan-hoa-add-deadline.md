# Báo cáo: Tính cá nhân hóa của `/add_deadline` + sửa lỗi tiềm ẩn

**Ngày:** 03/09/2026

---

## 🔍 Kết luận nhanh

**Có, đúng như Nguyên nghi ngờ** — tin nhắn xác nhận sau khi gõ `/add_deadline` hiện tại **chỉ người gõ lệnh mới thấy được** (Discord gọi là "ephemeral", có chữ *"Only you can see this"*). Người khác trong kênh **không hề biết** vừa có deadline mới được thêm, cho tới khi bot tự gửi thông báo chính thức (**chờ tối đa 30 phút** vì chạy theo lịch cron).

Đã sửa để tin xác nhận này **hiện công khai ngay lập tức** cho cả kênh, đồng thời phát hiện và vá luôn 1 lỗi tiềm ẩn liên quan (mục 3). Đã kiểm tra bằng test thực tế, không chỉ đọc code.

---

## 1. Vì sao bị "cá nhân hóa" — giải thích kỹ thuật

Trong `src/interactions.py`, có 2 loại phản hồi:

```python
def _ephemeral(text):
    return {"type": 4, "data": {"content": text, "flags": 64}}
```

`flags: 64` là cờ **EPHEMERAL** của Discord API — bắt buộc tin nhắn chỉ hiện cho người gọi lệnh, dù nó nằm trong kênh chung. Đây **không phải bug ngẫu nhiên** — bản kế hoạch gốc (`docs/lo-trinh-them-lenh-deadline.md`) đã chủ đích chọn ephemeral để "tránh spam channel", và có ghi chú sẵn: *"Nếu muốn công khai cho cả kênh thấy, chỉ cần bỏ `flags: 64`"*. Tức là lựa chọn này được lường trước nhưng chưa được đổi lại theo nhu cầu thực tế của Nguyên.

**Rà toàn bộ các chỗ dùng `_ephemeral` trong file:**

| Dòng | Nội dung | Có nên riêng tư không? |
|---|---|---|
| Lệnh không hỗ trợ | Lỗi hệ thống | ✅ Đúng, nên riêng tư |
| `/add_deadline` — sai định dạng ngày | Lỗi input | ✅ Đúng, nên riêng tư (tránh spam kênh mỗi lần ai gõ sai) |
| `/add_deadline` — không xác định được môn | Lỗi input | ✅ Đúng, nên riêng tư |
| **`/add_deadline` — xác nhận thành công** | **Deadline đã lưu** | ❌ **Đây là chỗ cần công khai** — cả kênh cần biết |
| `/deadline` — xem danh sách | Tra cứu cá nhân | ✅ Hợp lý để riêng tư (không phải ai cũng cần thấy người khác tra deadline lúc nào), **không đổi** vì Nguyên không yêu cầu |

→ Chỉ **1 chỗ duy nhất** cần sửa: tin xác nhận thành công của `/add_deadline`.

---

## 2. Đã sửa gì

### `src/interactions.py`

Thêm hàm `_public()` bên cạnh `_ephemeral()` sẵn có (không xoá, không đổi hành vi các chỗ khác):

```python
def _ephemeral(text):
    """Chỉ người gõ lệnh thấy được (dùng cho lỗi và tra cứu riêng tư)."""
    return {"type": 4, "data": {"content": text, "flags": 64}}


def _public(text):
    """Cả kênh đều thấy được (dùng khi hành động ảnh hưởng đến mọi người,
    ví dụ như xác nhận đã thêm deadline mới)."""
    return {"type": 4, "data": {"content": text}}
```

Đổi phần trả kết quả thành công trong `_handle_add_deadline` — dùng `_public()` thay vì `_ephemeral()`, và thêm tên người thêm vào nội dung (giải thích lý do ở mục 3):

```python
        courses_id = get_or_create_course(conn, course_name)
        deadlines_id = insert_deadline_manual(
            conn, courses_id, name, f"manual-{interaction['id']}", due_time,
            source_url=f"Discord (thêm bởi {username})", added_by=username
        )

    due_local = due_time.astimezone(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')

    # deadlines_id là None khi ON CONFLICT DO NOTHING kích hoạt — tức Discord
    # đã gửi lặp lại đúng interaction này (retry). Không phải deadline mới,
    # chỉ là hiển thị lại xác nhận cho interaction bị gửi 2 lần, tránh làm
    # người trong kênh hiểu lầm có 2 deadline được thêm.
    header = "📌 **Deadline nội bộ mới**"
    if deadlines_id is None:
        header += " _(xác nhận lặp lại — deadline này đã được lưu từ trước, không tạo trùng)_"

    return _public(
        f"{header}\n"
        f"📚 Môn: **{course_name}**\n"
        f"📝 {name}\n"
        f"⏰ Hạn chót: {due_local}\n"
        f"➕ Thêm bởi: {username}\n\n"
        f"_Bot sẽ gửi thông báo chính thức kèm nhắc nhở vào kênh môn trong tối đa 30 phút._"
    )
```

**Toàn bộ phần còn lại của file giữ nguyên** — chỉ thay đoạn code trong khối `_handle_add_deadline` nêu trên.

---

## 3. Lỗi tiềm ẩn phát hiện thêm khi kiểm tra (đã vá)

Trong lúc rà lại đoạn code sắp công khai, phát hiện **kết quả trả về của `insert_deadline_manual()` trước giờ bị bỏ qua hoàn toàn** (không gán vào biến, không kiểm tra):

```python
insert_deadline_manual(   # <-- kết quả bị vứt đi, không biết có thật sự tạo mới hay không
    conn, courses_id, name, f"manual-{interaction['id']}", due_time,
    source_url=f"Discord (thêm bởi {username})", added_by=username
)
```

**Vì sao đây là lỗi tiềm ẩn, và vì sao nó quan trọng hơn sau khi công khai:**

Hàm này dùng `ON CONFLICT (lms_deadlines_id) DO NOTHING` — thiết kế để **an toàn khi Discord gửi lặp cùng 1 interaction** (retry, xảy ra khi bot phản hồi chậm hoặc mạng chập chờn). Khi bị lặp, `deadlines_id` trả về sẽ là `None` (không tạo dòng mới, vì đã tồn tại từ lần gọi trước).

- **Lúc còn ephemeral (riêng tư):** nếu retry xảy ra, chỉ người gõ lệnh thấy 2 lần tin xác nhận giống hệt nhau — hơi khó chịu nhưng vô hại, vì chỉ họ tự biết mình gõ 1 lần.
- **Sau khi công khai (theo yêu cầu của Nguyên):** nếu không xử lý, **cả kênh sẽ thấy 2 tin "📌 Deadline nội bộ mới"** với cùng nội dung — dễ khiến mọi người tưởng nhầm có **2 deadline khác nhau** được thêm, trong khi thực chất chỉ có 1 dòng trong DB.

→ Đã vá bằng cách kiểm tra `deadlines_id is None` và ghi chú rõ *"xác nhận lặp lại — không tạo trùng"* trong tin nhắn, để nếu tình huống hiếm này xảy ra, mọi người vẫn hiểu đúng là chỉ có 1 deadline thật sự.

---

## 4. Những phần liên quan đã kiểm tra, xác nhận KHÔNG có vấn đề

- **Thông báo chính thức (`DEADLINE MỚI` gửi bởi cron `main.py`):** đã công khai từ trước (`send_message()` gửi vào kênh chung, kèm `@everyone`), **không phải nguồn gây cá nhân hóa** — chỉ tin xác nhận tức thời của slash command mới bị vậy.
- **API bên thứ 3 (`api/add_deadline.py`, đã làm ở lần trước):** phản hồi JSON trả về **chỉ hiện với bên gọi API** — đây là hành vi **bình thường và đúng** của một REST API (không phải Discord, không có khái niệm "cả kênh xem"), **không cần và không nên sửa gì**. Deadline được thêm qua API này vẫn được cron nhặt lên và thông báo công khai vào kênh Discord như deadline thường, không bị ảnh hưởng bởi thay đổi hôm nay.
- **`/deadline` (lệnh xem danh sách):** vẫn giữ riêng tư như thiết kế ban đầu, vì Nguyên không yêu cầu đổi, và để riêng tư ở đây hợp lý (tránh mỗi lần ai đó tra deadline lại làm trôi kênh).
- **Các tin nhắn lỗi** (sai định dạng ngày, không xác định được môn): vẫn giữ riêng tư, đúng chủ đích (không nên biến lỗi gõ sai của 1 người thành tin công khai cho cả kênh).

---

## 5. Kết quả kiểm tra thực tế (5/5 test pass)

Đã dựng lại file trong môi trường sandbox, `py_compile` + import thật (`pynacl`), rồi giả lập toàn bộ luồng `_handle_add_deadline` / `_handle_deadline` bằng mock DB để kiểm tra hành vi thật, không chỉ đọc code:

| # | Test case | Kỳ vọng | Kết quả |
|---|---|---|---|
| 1 | Thêm deadline thành công | Tin công khai (không có `flags`), có tên người thêm, tự động `23:59` nếu thiếu giờ | ✅ PASS |
| 2 | Sai định dạng ngày | Vẫn riêng tư (`flags: 64`) | ✅ PASS |
| 3 | Không xác định được môn | Vẫn riêng tư (`flags: 64`) | ✅ PASS |
| 4 | Discord gửi lặp interaction (retry, insert trả `None`) | Vẫn công khai nhưng ghi rõ "xác nhận lặp lại — không tạo trùng" | ✅ PASS |
| 5 | `/deadline` (xem danh sách) | Không đổi hành vi, vẫn riêng tư như cũ | ✅ PASS |

Chạy lại thêm toàn bộ test của 2 lần cập nhật trước (`parse_due_time`, `external_api`) — **không có hồi quy**, mọi thứ vẫn hoạt động đúng như trước.

**Ví dụ tin nhắn công khai thực tế sau khi sửa:**
```
📌 **Deadline nội bộ mới**
📚 Môn: **CSC10014**
📝 Nộp đồ án
⏰ Hạn chót: 25/12/2026 23:59
➕ Thêm bởi: baonguyen

_Bot sẽ gửi thông báo chính thức kèm nhắc nhở vào kênh môn trong tối đa 30 phút._
```

---

## 6. Việc cần làm để áp dụng

1. [ ] Áp đoạn code mục 2 vào `src/interactions.py` (chỉ trong hàm `_handle_add_deadline` và phần thêm hàm `_public`).
2. [ ] Deploy lại lên Vercel (endpoint `/api/interactions` dùng file này).
3. [ ] Test trên Discord thật: gõ `/add_deadline` bằng 1 tài khoản, kiểm tra bằng **tài khoản/thiết bị khác** xem có thấy tin xác nhận ngay không (trước đây sẽ không thấy, giờ phải thấy).
4. [ ] Không cần chạy lại `register_commands.py` — lần này không đổi cấu trúc lệnh (option/description), chỉ đổi cách phản hồi.

---

## 7. Nếu Nguyên muốn thêm

Hiện tại tin công khai **không kèm `@everyone`** (chủ đích, để tránh việc mỗi lần thêm 1 deadline nội bộ nhỏ lại ping cả server 2 lần — 1 lần lúc thêm, 1 lần nữa khi thông báo chính thức ~30 phút sau). Nếu Nguyên muốn tin xác nhận này **cũng ping `@everyone`** ngay lúc thêm (thay vì chờ thông báo chính thức), báo mình để chỉnh thêm 1 dòng.

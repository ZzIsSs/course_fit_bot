"""Nội dung tin nhắn Discord và quy tắc làm sạch text người dùng nhập (thuần, không I/O)."""
import re

from course_bot.core.time_utils import LOCAL_TZ
from course_bot.domain.reminders import NEW, THREE_DAYS, ONE_DAY

_DEADLINE_HEADERS = {
    NEW: "🚨 **DEADLINE MỚI** 🚨",
    THREE_DAYS: "⚠️ **NHẮC NHỞ: CÒN 3 NGÀY** ⚠️",
    ONE_DAY: "🆘 **KHẨN CẤP: CÒN 24 GIỜ** 🆘",
}
_COMPLETION_HINT = "\n\n✅ *React ✅ vào tin nhắn này khi đã hoàn thành!*"


def sanitize_discord_text(text):
    """Khử nguy cơ Mention Injection (@everyone, @here, role ping) và ký tự rác."""
    if not text:
        return ""
    # Lọc bỏ ký tự điều khiển trước
    text = "".join(ch for ch in str(text) if ch.isprintable() or ch in '\n\r\t')
    text = text.replace("@everyone", "@​everyone").replace("@here", "@​here")
    text = re.sub(r'<@&(\d+)>', lambda m: '@​&role', text)
    return " ".join(text.strip().split())


def build_event_url(uid):
    """Tạo URL đến sự kiện trên Moodle từ UID."""
    base_url = "https://courses.fit.hcmus.edu.vn/calendar/view.php?view=upcoming"
    id_match = re.search(r'^(\d+)@', uid)
    if id_match:
        return (
            f"https://courses.fit.hcmus.edu.vn/calendar/view.php"
            f"?view=day&course=1&time=upcoming#event_{id_match.group(1)}"
        )
    return base_url


def build_deadline_message(msg_type, subject, summary, due_time, url):
    """Tin nhắn @everyone cho deadline mới hoặc nhắc nhở (msg_type từ domain.reminders)."""
    deadline_local = due_time.astimezone(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')
    return (
        f"@everyone {_DEADLINE_HEADERS[msg_type]}\n\n"
        f"📌 **Môn:** {subject}\n"
        f"📝 **Nội dung:** {summary}\n"
        f"⏰ **Hạn chót:** {deadline_local}\n"
        f"🔗 **Xem:** {url}{_COMPLETION_HINT}"
    )

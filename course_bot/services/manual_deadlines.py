"""Thêm và đánh dấu hoàn thành deadline thủ công (dùng chung cho Web, Discord, API bên thứ 3).

Chuẩn hoá input giống nhau ở mọi nguồn: tên deadline, mã môn và người thêm
đều được sanitize (bỏ ký tự điều khiển, chặn @everyone/@here/ping role, gộp
khoảng trắng) vì bot sẽ chèn chúng vào tin nhắn @everyone trên Discord.
Mỗi entry point vẫn tự quyết message lỗi trả về cho người dùng.
"""
from course_bot.core.time_utils import LOCAL_TZ, parse_due_time
from course_bot.db.repositories.courses import get_or_create_course
from course_bot.db.repositories.deadlines import insert_deadline_manual, toggle_deadline_completed
from course_bot.domain.messages import sanitize_discord_text

MAX_NAME_LEN = 250
MAX_COURSE_LEN = 100
MAX_ADDED_BY_LEN = 95   # source_url "Discord (thêm bởi ...)" phải vừa cột trong DB


def clean_name(raw):
    """Tên deadline đã sanitize, tối đa MAX_NAME_LEN ký tự ("" nếu trống)."""
    return sanitize_discord_text(raw)[:MAX_NAME_LEN]


def clean_course(raw):
    """Mã môn đã sanitize và viết hoa, tối đa MAX_COURSE_LEN ký tự ("" nếu trống).

    Sanitize trước khi viết hoa, để "@everyone" không thành "@EVERYONE" lọt qua bộ lọc.
    """
    return sanitize_discord_text(raw).upper()[:MAX_COURSE_LEN]


def clean_added_by(raw, default):
    """Người/nguồn thêm deadline đã sanitize, tối đa MAX_ADDED_BY_LEN ký tự, hoặc `default`."""
    return sanitize_discord_text(raw)[:MAX_ADDED_BY_LEN] or default


def parse_due(raw):
    """Parse hạn chót kiểu '25/12/2026 23:59' hoặc '25/12/2026' (giờ VN). None nếu sai định dạng."""
    return parse_due_time((raw or "").strip(), LOCAL_TZ)


def add_manual_deadline(conn, course_name, name, due_time, lms_id, *, source_url, added_by, source="manual"):
    """Tạo (hoặc tìm) môn rồi ghi deadline. Trả về deadlines_id, hoặc None nếu đã tồn tại.

    Các giá trị phải đã qua clean_* và parse_due.
    """
    courses_id = get_or_create_course(conn, course_name)
    return insert_deadline_manual(
        conn, courses_id, name, lms_id, due_time,
        source_url=source_url, added_by=added_by, source=source,
    )


def toggle_completed(conn, deadlines_id, completed, completed_by=None):
    """Đánh dấu hoặc bỏ đánh dấu hoàn thành deadline."""
    toggle_deadline_completed(conn, deadlines_id, completed, completed_by)

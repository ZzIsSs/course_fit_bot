"""Repository cho bảng notifications.

Mỗi hàm nhận conn (connection) làm tham số đầu tiên.
"""
from course_bot.db.connection import execute


def insert_notification(conn, notif_type, message, reference_id):
    """Ghi lại thông báo đã gửi vào lịch sử."""
    execute(conn,
        """INSERT INTO notifications (type, message, sent_at, reference_id)
           VALUES (%s, %s, now(), %s)""",
        (notif_type, message, reference_id))

"""Route cho Web Dashboard: /courses, /stats, /deadlines, /deadlines/toggle, /announcements.

Mỗi hàm trả về (status, payload) để router gửi bằng http_utils.send_json.
"""
import json
import uuid

from course_bot.db.connection import get_db
from course_bot.db.repositories.courses import get_courses_with_deadline_counts
from course_bot.db.repositories.deadlines import get_dashboard_stats, get_all_deadlines_with_course_details
from course_bot.db.repositories.moodle_content import get_recent_announcements_with_course
from course_bot.services.manual_deadlines import (
    add_manual_deadline,
    clean_added_by,
    clean_course,
    clean_name,
    parse_due,
    toggle_completed,
)


def get_courses(database_url):
    """GET /api/courses: danh sách môn học kèm số deadline."""
    try:
        with get_db(database_url) as conn:
            courses = get_courses_with_deadline_counts(conn)
        return 200, {"ok": True, "data": courses}
    except Exception as e:
        return 500, {"ok": False, "error": f"Lỗi truy vấn courses: {str(e)}"}


def get_stats(database_url):
    """GET /api/stats: thống kê tổng quan cho Dashboard."""
    try:
        with get_db(database_url) as conn:
            stats = get_dashboard_stats(conn)
        from course_bot.domain.semester import get_current_semester
        stats["semester"] = get_current_semester()
        return 200, {"ok": True, "data": stats}
    except Exception as e:
        return 500, {"ok": False, "error": f"Lỗi truy vấn stats: {str(e)}"}


def get_deadlines(database_url, query_params):
    """GET /api/deadlines: danh sách bài tập (lọc theo ?course=)."""
    course = query_params.get("course", [None])[0]
    try:
        with get_db(database_url) as conn:
            deadlines = get_all_deadlines_with_course_details(conn, course)
        return 200, {"ok": True, "data": deadlines, "total": len(deadlines)}
    except Exception as e:
        return 500, {"ok": False, "error": f"Lỗi truy vấn deadlines: {str(e)}"}


def get_announcements(database_url):
    """GET /api/announcements: thông báo môn học gần nhất."""
    try:
        with get_db(database_url) as conn:
            announcements = get_recent_announcements_with_course(conn)
        return 200, {"ok": True, "data": announcements}
    except Exception as e:
        return 500, {"ok": False, "error": f"Lỗi truy vấn announcements: {str(e)}"}


def create_deadline(body, database_url):
    """POST /api/deadlines: thêm deadline thủ công từ Web UI."""
    try:
        data = json.loads(body)
    except Exception:
        return 400, {"ok": False, "error": "Body không phải JSON hợp lệ."}

    mon = clean_course(data.get("mon"))
    ten = clean_name(data.get("ten"))
    han_chot = (data.get("han_chot") or "").strip()
    nguoi = clean_added_by(data.get("nguoi_phu_trach"), "Web Dashboard")
    ghi_chu = (data.get("ghi_chu_url") or "").strip()[:500]

    if not mon or not ten or not han_chot:
        return 400, {"ok": False, "error": "Vui lòng điền đủ: mon, ten, han_chot."}

    due_time = parse_due(han_chot)
    if due_time is None:
        return 400, {"ok": False, "error": "Sai định dạng ngày. VD: '25/09/2026 23:59'."}

    lms_id = f"manual-{uuid.uuid4()}"
    try:
        with get_db(database_url) as conn:
            deadlines_id = add_manual_deadline(
                conn, mon, ten, due_time, lms_id,
                source_url=ghi_chu if ghi_chu else "Thêm thủ công qua Web",
                added_by=nguoi,
                source="manual"
            )
        if deadlines_id is None:
            return 200, {"ok": True, "duplicate": True, "message": "Deadline này đã tồn tại, không tạo trùng."}
        else:
            return 201, {"ok": True, "deadlines_id": deadlines_id, "message": "Thêm deadline thành công!"}
    except Exception as e:
        return 500, {"ok": False, "error": f"Lỗi DB khi thêm deadline: {str(e)}"}


def toggle_deadline(body, database_url):
    """POST /api/deadlines/toggle: đánh dấu hoàn thành / bỏ hoàn thành deadline."""
    try:
        data = json.loads(body)
    except Exception:
        return 400, {"ok": False, "error": "Body không phải JSON hợp lệ."}

    deadlines_id = data.get("deadlines_id")
    completed = bool(data.get("completed"))
    completed_by = data.get("completed_by", "Web User")

    if not deadlines_id:
        return 400, {"ok": False, "error": "Thiếu deadlines_id"}

    try:
        with get_db(database_url) as conn:
            toggle_completed(conn, deadlines_id, completed, completed_by)
        return 200, {"ok": True, "deadlines_id": deadlines_id, "completed": completed}
    except Exception as e:
        return 500, {"ok": False, "error": f"Lỗi DB khi toggle deadline: {str(e)}"}

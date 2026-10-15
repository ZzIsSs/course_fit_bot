"""Thu thập deadline trực tiếp từ Moodle REST API (Assignments & Quizzes).

Module này bổ sung cho luồng ICS hiện tại, giải quyết vấn đề:
- Giảng viên tạo bài tập nhưng quên đẩy lên Calendar → ICS không có.
- Quiz có thời gian đóng (timeclose) nhưng không xuất hiện trong ICS.
- Giảng viên đổi hạn chót → module tự cập nhật due_time trong DB.

Sử dụng MOODLE_TOKEN để gọi:
- mod_assign_get_assignments: lấy toàn bộ bài tập + duedate
- mod_quiz_get_quizzes_by_courses: lấy toàn bộ quiz + timeclose
- core_calendar_get_action_events_by_timesort: sự kiện cần hành động
- mod_assign_get_submission_status: kiểm tra trạng thái nộp bài → auto-complete
"""
import logging
from datetime import datetime, timezone, timedelta

from course_bot.integrations.moodle.webservice import (
    get_site_info, get_enrolled_courses,
    get_assignments, get_quizzes,
    get_calendar_action_events, get_submission_status
)
from course_bot.domain.course_naming import extract_subject, extract_display_name
from course_bot.db.repositories.courses import get_or_create_course
from course_bot.db.repositories.deadlines import (
    upsert_deadline_from_api,
    get_api_deadlines_for_auto_complete,
    mark_deadline_completed,
)
from course_bot.core.config import load_env
from course_bot.db.connection import get_db

# ==================== HẰNG SỐ ====================

MOODLE_BASE = "https://courses.fit.hcmus.edu.vn"

# Số ngày tối đa để quét events từ Calendar API
CALENDAR_LOOKAHEAD_DAYS = 90


# ==================== HÀM CHÍNH ====================

def crawl_moodle_deadlines(moodle_token, conn):
    """Quét Moodle API để thu thập deadline từ Assignments và Quizzes.

    Luồng xử lý:
    1. Xác thực token → lấy user ID
    2. Lấy danh sách khóa học
    3. Gọi mod_assign_get_assignments → upsert vào bảng deadlines
    4. Gọi mod_quiz_get_quizzes_by_courses → upsert vào bảng deadlines
    5. Gọi core_calendar_get_action_events_by_timesort → bổ sung thêm
    6. Kiểm tra trạng thái nộp bài → auto-complete

    Args:
        moodle_token: Moodle Web Services token.
        conn: Database connection (psycopg2).

    Returns:
        Dict thống kê: {'assignments': int, 'quizzes': int, 'calendar': int,
                        'inserted': int, 'updated': int, 'auto_completed': int}
    """
    stats = {
        'assignments': 0, 'quizzes': 0, 'calendar': 0,
        'inserted': 0, 'updated': 0, 'skipped': 0,
        'auto_completed': 0, 'errors': 0,
    }

    # === Bước 1: Xác thực token ===
    site_info = get_site_info(moodle_token)
    if not site_info or 'userid' not in site_info:
        logging.error("[Deadline Crawler] Không thể xác thực Moodle token.")
        return stats

    userid = site_info['userid']
    logging.info("[Deadline Crawler] Đã xác thực — User ID: %s", userid)

    # === Bước 2: Lấy danh sách khóa học ===
    courses = get_enrolled_courses(moodle_token, userid)
    if not courses:
        logging.warning("[Deadline Crawler] Không tìm thấy khóa học nào.")
        return stats

    course_ids = [c['id'] for c in courses]
    logging.info("[Deadline Crawler] Tìm thấy %d khóa học.", len(courses))

    # Tạo mapping course_id → course info để tra cứu nhanh
    course_lookup = {}
    for c in courses:
        subject_code = extract_subject(c.get('shortname', ''))
        display_name = extract_display_name(c.get('fullname', ''))
        if subject_code == "General" and display_name:
            subject_code = display_name
        course_lookup[c['id']] = {
            'subject': subject_code,
            'display_name': display_name,
            'fullname': c.get('fullname', ''),
        }

    # === Bước 3: Thu thập Assignments ===
    _crawl_assignments(moodle_token, conn, course_ids, course_lookup, stats)
    conn.commit()

    # === Bước 4: Thu thập Quizzes ===
    _crawl_quizzes(moodle_token, conn, course_ids, course_lookup, stats)
    conn.commit()

    # === Bước 5: Thu thập Calendar Action Events (bổ sung) ===
    _crawl_calendar_events(moodle_token, conn, course_lookup, stats)
    conn.commit()

    # === Bước 6: Auto-complete ===
    _check_auto_complete(moodle_token, conn, userid, stats)
    conn.commit()

    logging.info(
        "[Deadline Crawler] Hoàn tất — "
        "Assignments: %d, Quizzes: %d, Calendar: %d | "
        "Mới: %d, Cập nhật: %d, Bỏ qua: %d, Auto-complete: %d",
        stats['assignments'], stats['quizzes'], stats['calendar'],
        stats['inserted'], stats['updated'], stats['skipped'],
        stats['auto_completed']
    )
    return stats


# ==================== THU THẬP ASSIGNMENTS ====================

def _crawl_assignments(moodle_token, conn, course_ids, course_lookup, stats):
    """Gọi mod_assign_get_assignments và upsert vào bảng deadlines."""
    try:
        data = get_assignments(moodle_token, course_ids)
    except Exception as e:
        logging.error("[Deadline Crawler] Lỗi gọi get_assignments: %s", e)
        stats['errors'] += 1
        return

    if not data or 'courses' not in data:
        logging.warning("[Deadline Crawler] get_assignments trả về dữ liệu rỗng hoặc không hợp lệ.")
        return

    for course_data in data['courses']:
        moodle_course_id = course_data.get('id')
        course_info = course_lookup.get(moodle_course_id, {})
        subject = course_info.get('subject', 'General')

        for assign in course_data.get('assignments', []):
            assign_id = assign.get('id')
            cmid = assign.get('cmid')
            name = assign.get('name', 'Bài tập không tên')
            duedate = assign.get('duedate', 0)
            cutoffdate = assign.get('cutoffdate', 0)

            # Ưu tiên duedate, fallback sang cutoffdate
            effective_due = duedate if duedate and duedate > 0 else cutoffdate
            if not effective_due or effective_due <= 0:
                continue  # Bài tập không có hạn chót → bỏ qua

            due_dt = datetime.fromtimestamp(effective_due, tz=timezone.utc)

            # Bỏ qua deadline đã quá hạn lâu hơn 7 ngày (tránh spam cũ)
            if due_dt < datetime.now(timezone.utc) - timedelta(days=7):
                continue

            lms_id = f"moodle-assign-{assign_id}"
            source_url = f"{MOODLE_BASE}/mod/assign/view.php?id={cmid}" if cmid else ""

            db_course_id = get_or_create_course(conn, subject)
            action, _ = upsert_deadline_from_api(
                conn, db_course_id, name, lms_id, due_dt, source_url, source='moodle_api'
            )

            stats['assignments'] += 1
            if action == 'inserted':
                stats['inserted'] += 1
            elif action == 'updated':
                stats['updated'] += 1
            else:
                stats['skipped'] += 1


# ==================== THU THẬP QUIZZES ====================

def _crawl_quizzes(moodle_token, conn, course_ids, course_lookup, stats):
    """Gọi mod_quiz_get_quizzes_by_courses và upsert vào bảng deadlines."""
    try:
        data = get_quizzes(moodle_token, course_ids)
    except Exception as e:
        logging.error("[Deadline Crawler] Lỗi gọi get_quizzes: %s", e)
        stats['errors'] += 1
        return

    if not data or 'quizzes' not in data:
        logging.warning("[Deadline Crawler] get_quizzes trả về dữ liệu rỗng hoặc không hợp lệ.")
        return

    for quiz in data.get('quizzes', []):
        quiz_id = quiz.get('id')
        coursemodule = quiz.get('coursemodule')
        moodle_course_id = quiz.get('course')
        name = quiz.get('name', 'Bài kiểm tra không tên')
        timeclose = quiz.get('timeclose', 0)

        if not timeclose or timeclose <= 0:
            continue  # Quiz không có thời gian đóng → bỏ qua

        due_dt = datetime.fromtimestamp(timeclose, tz=timezone.utc)

        # Bỏ qua quiz đã đóng lâu hơn 7 ngày
        if due_dt < datetime.now(timezone.utc) - timedelta(days=7):
            continue

        course_info = course_lookup.get(moodle_course_id, {})
        subject = course_info.get('subject', 'General')

        lms_id = f"moodle-quiz-{quiz_id}"
        source_url = f"{MOODLE_BASE}/mod/quiz/view.php?id={coursemodule}" if coursemodule else ""

        db_course_id = get_or_create_course(conn, subject)
        action, _ = upsert_deadline_from_api(
            conn, db_course_id, name, lms_id, due_dt, source_url, source='moodle_api'
        )

        stats['quizzes'] += 1
        if action == 'inserted':
            stats['inserted'] += 1
        elif action == 'updated':
            stats['updated'] += 1
        else:
            stats['skipped'] += 1


# ==================== THU THẬP CALENDAR ACTION EVENTS ====================

def _crawl_calendar_events(moodle_token, conn, course_lookup, stats):
    """Gọi core_calendar_get_action_events_by_timesort — bổ sung các sự kiện
    không phải assign/quiz mà vẫn có hành động cần làm (VD: workshop, feedback)."""
    import time

    now_ts = int(time.time())
    end_ts = now_ts + (CALENDAR_LOOKAHEAD_DAYS * 86400)

    try:
        data = get_calendar_action_events(moodle_token, timesort_from=now_ts, timesort_to=end_ts)
    except Exception as e:
        logging.error("[Deadline Crawler] Lỗi gọi get_calendar_action_events: %s", e)
        stats['errors'] += 1
        return

    if not data or 'events' not in data:
        return

    for event in data.get('events', []):
        event_id = event.get('id')
        name = event.get('name', '')
        timestart = event.get('timestart', 0)
        timeduration = event.get('timeduration', 0)

        # Component cho biết loại module (assign, quiz, ...)
        component = event.get('component', '')
        modulename = event.get('modulename', '')

        # Bỏ qua assign và quiz vì đã thu thập riêng ở trên
        if modulename in ('assign', 'quiz'):
            continue

        # Chỉ lấy event có thời gian hợp lệ
        if not timestart or timestart <= 0:
            continue

        # Thời điểm kết thúc = timestart + timeduration (hoặc chính timestart nếu duration = 0)
        effective_end = timestart + timeduration if timeduration else timestart
        due_dt = datetime.fromtimestamp(effective_end, tz=timezone.utc)

        # Lấy thông tin khóa học
        course_data = event.get('course', {})
        moodle_course_id = course_data.get('id')
        course_info = course_lookup.get(moodle_course_id, {})
        subject = course_info.get('subject', 'General')

        lms_id = f"moodle-event-{event_id}"
        action_url = event.get('url', '')
        source_url = action_url if action_url else f"{MOODLE_BASE}/calendar/view.php?view=upcoming"

        db_course_id = get_or_create_course(conn, subject)
        action, _ = upsert_deadline_from_api(
            conn, db_course_id, name, lms_id, due_dt, source_url, source='moodle_api'
        )

        stats['calendar'] += 1
        if action == 'inserted':
            stats['inserted'] += 1
        elif action == 'updated':
            stats['updated'] += 1
        else:
            stats['skipped'] += 1


# ==================== AUTO-COMPLETE ====================

def _check_auto_complete(moodle_token, conn, userid, stats):
    """Kiểm tra trạng thái nộp bài và tự động đánh dấu hoàn thành.

    Chỉ áp dụng cho deadline loại assign (có thể kiểm tra submission status).
    """
    pending_assigns = get_api_deadlines_for_auto_complete(conn)
    if not pending_assigns:
        return

    logging.info("[Auto-Complete] Kiểm tra %d deadline chưa hoàn thành...", len(pending_assigns))

    for row in pending_assigns:
        lms_id = row['lms_deadlines_id']

        # Parse assignment ID từ lms_deadlines_id format "moodle-assign-{id}"
        try:
            assign_id = int(lms_id.split('-')[-1])
        except (ValueError, IndexError):
            continue

        try:
            status_data = get_submission_status(moodle_token, assign_id, userid)
        except Exception as e:
            logging.warning("[Auto-Complete] Lỗi kiểm tra submission cho assign %s: %s", assign_id, e)
            continue

        if not status_data:
            continue

        # Trích xuất trạng thái nộp bài
        submission_status = _extract_submission_status(status_data)
        if submission_status == 'submitted':
            mark_deadline_completed(conn, row['deadlines_id'], completed_by='auto (đã nộp bài)')
            stats['auto_completed'] += 1
            logging.info(
                "[Auto-Complete] ✅ Đánh dấu hoàn thành: '%s' (%s)",
                row['deadline_name'], row['course_name']
            )


def _extract_submission_status(status_data):
    """Bóc tách trạng thái nộp bài từ response của mod_assign_get_submission_status.

    Cấu trúc response:
    {
        "lastattempt": {
            "submission": {
                "status": "submitted" | "new" | "draft",
                ...
            },
            "teamsubmission": {  // nếu bài tập nhóm
                "status": "submitted" | "new" | "draft",
                ...
            }
        }
    }
    """
    if not isinstance(status_data, dict):
        return None

    last_attempt = status_data.get('lastattempt', {})
    if not last_attempt:
        return None

    # Ưu tiên kiểm tra bài nộp cá nhân, sau đó bài nộp nhóm
    submission = last_attempt.get('submission')
    if submission and isinstance(submission, dict):
        status = submission.get('status', '')
        if status:
            return status

    team_submission = last_attempt.get('teamsubmission')
    if team_submission and isinstance(team_submission, dict):
        return team_submission.get('status', '')

    return None


# ==================== THU THẬP DEADLINE TỪ MOODLE API ====================

def crawl_deadlines_standalone():
    """Chạy riêng module thu thập deadline từ Moodle API.

    Sử dụng: python main.py --crawl-deadlines
    Yêu cầu: MOODLE_TOKEN phải được cấu hình.
    """
    env = load_env()
    if not env:
        return

    moodle_token = env.get('moodle_token')
    if not moodle_token:
        logging.error("MOODLE_TOKEN chưa được cấu hình. Không thể thu thập deadline từ API.")
        return

    database_url = env['database_url']

    with get_db(database_url) as conn:
        stats = crawl_moodle_deadlines(moodle_token, conn)

    logging.info(
        "Kết quả thu thập: Assignments=%d, Quizzes=%d, Calendar=%d | "
        "Mới=%d, Cập nhật=%d, Auto-complete=%d",
        stats['assignments'], stats['quizzes'], stats['calendar'],
        stats['inserted'], stats['updated'], stats['auto_completed']
    )

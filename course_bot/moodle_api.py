"""Moodle Web Services API client.

Gọi các hàm API REST của Moodle thông qua token (lấy từ GitHub Secrets).
Tất cả hàm trả về dữ liệu JSON đã parse, hoặc None nếu có lỗi.
"""
import logging
import requests

MOODLE_API_BASE = "https://courses.fit.hcmus.edu.vn/webservice/rest/server.php"

# Ngụy trang User-Agent để vượt tường lửa (WAF) của trường
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 MoodleMobile'
}


def _call_api(token, function, **params):
    """Gọi một Moodle Web Services API function.

    Args:
        token: Moodle web service token.
        function: Tên hàm API (ví dụ: 'core_webservice_get_site_info').
        **params: Các tham số bổ sung cho API.

    Returns:
        Dữ liệu JSON đã parse, hoặc None nếu có lỗi.
    """
    all_params = {
        'wstoken': token,
        'wsfunction': function,
        'moodlewsrestformat': 'json',
    }
    all_params.update(params)

    try:
        response = requests.get(MOODLE_API_BASE, params=all_params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Moodle trả lỗi dưới dạng JSON dict có key 'exception'
        if isinstance(data, dict) and 'exception' in data:
            logging.error(
                f"Moodle API error ({function}): "
                f"{data.get('message', data.get('errorcode', 'Unknown'))}"
            )
            return None

        return data
    except requests.exceptions.Timeout:
        logging.error(f"Moodle API timeout ({function})")
        return None
    except Exception as e:
        logging.error(f"Moodle API request failed ({function}): {e}")
        return None


# ==================== THÔNG TIN NGƯỜI DÙNG ====================

def get_site_info(token):
    """Lấy thông tin site và user đã xác thực.

    Returns:
        Dict chứa 'userid', 'fullname', 'sitename', ... hoặc None.
    """
    return _call_api(token, 'core_webservice_get_site_info')


# ==================== KHÓA HỌC ====================

def get_enrolled_courses(token, userid):
    """Lấy danh sách tất cả khóa học mà user đang tham gia.

    Returns:
        List các course dict chứa 'id', 'fullname', 'shortname', ...
    """
    return _call_api(token, 'core_enrol_get_users_courses', userid=userid)


def get_course_contents(token, course_id):
    """Lấy toàn bộ nội dung của một khóa học (sections, modules, files).

    Returns:
        List các section dict, mỗi section chứa danh sách 'modules'.
    """
    return _call_api(token, 'core_course_get_contents', courseid=course_id)


# ==================== DIỄN ĐÀN ====================

def get_course_forums(token, course_id):
    """Lấy tất cả diễn đàn (forums) trong một khóa học.

    Returns:
        List các forum dict chứa 'id', 'name', 'type', ...
    """
    return _call_api(
        token, 'mod_forum_get_forums_by_courses',
        **{'courseids[0]': course_id}
    )


def get_forum_discussions(token, forum_id, per_page=10):
    """Lấy các bài đăng (discussions) gần nhất từ một diễn đàn.

    Args:
        token: Moodle token.
        forum_id: ID của forum.
        per_page: Số lượng bài đăng tối đa cần lấy (mặc định 10).

    Returns:
        List các discussion dict, hoặc None nếu lỗi.
    """
    data = _call_api(
        token, 'mod_forum_get_forum_discussions',
        forumid=forum_id, perpage=per_page, sortorder=1
    )
    # API có thể trả về dict chứa key 'discussions' hoặc trả list trực tiếp
    if data and isinstance(data, dict):
        return data.get('discussions', [])
    if isinstance(data, list):
        return data
    return None


# ==================== BÀI TẬP (ASSIGNMENTS) ====================

def get_assignments(token, course_ids):
    """Lấy danh sách bài tập (assignments) cho nhiều khóa học cùng lúc.

    Args:
        token: Moodle token.
        course_ids: List các course ID (int) từ Moodle.

    Returns:
        Dict chứa key 'courses', mỗi course có list 'assignments'
        với các trường quan trọng: id, cmid, name, duedate, cutoffdate, ...
        Hoặc None nếu lỗi.
    """
    params = {f'courseids[{i}]': cid for i, cid in enumerate(course_ids)}
    return _call_api(token, 'mod_assign_get_assignments', **params)


def get_submission_status(token, assign_id, user_id=None):
    """Kiểm tra trạng thái nộp bài tập của sinh viên.

    Args:
        token: Moodle token.
        assign_id: ID của assignment (không phải cmid).
        user_id: ID người dùng (nếu None, Moodle dùng user hiện tại).

    Returns:
        Dict chứa 'lastattempt.submission.status' = 'submitted' | 'new' | 'draft', ...
        Hoặc None nếu lỗi.
    """
    params = {'assignid': assign_id}
    if user_id is not None:
        params['userid'] = user_id
    return _call_api(token, 'mod_assign_get_submission_status', **params)


# ==================== BÀI KIỂM TRA (QUIZZES) ====================

def get_quizzes(token, course_ids):
    """Lấy danh sách bài kiểm tra (quizzes) cho nhiều khóa học.

    Args:
        token: Moodle token.
        course_ids: List các course ID (int) từ Moodle.

    Returns:
        Dict chứa key 'quizzes', mỗi quiz có: id, coursemodule, course,
        name, timeopen, timeclose, ...
        Hoặc None nếu lỗi.
    """
    params = {f'courseids[{i}]': cid for i, cid in enumerate(course_ids)}
    return _call_api(token, 'mod_quiz_get_quizzes_by_courses', **params)


# ==================== SỰ KIỆN LỊCH (CALENDAR ACTION EVENTS) ====================

def get_calendar_action_events(token, timesort_from=None, timesort_to=None, limit=50):
    """Lấy các sự kiện 'cần hành động' từ Moodle Calendar API.

    Trả về các assignment/quiz/event mà sinh viên cần hoàn thành,
    bao gồm cả những event chưa có trong ICS.

    Args:
        token: Moodle token.
        timesort_from: Unix timestamp bắt đầu (mặc định: hiện tại).
        timesort_to: Unix timestamp kết thúc (mặc định: 90 ngày sau).
        limit: Số lượng event tối đa (mặc định 50).

    Returns:
        Dict chứa key 'events', mỗi event có: id, name, timestart,
        timeduration, course, action, url, ...
        Hoặc None nếu lỗi.
    """
    import time
    params = {
        'limitnum': limit,
    }
    if timesort_from is not None:
        params['timesortfrom'] = timesort_from
    else:
        params['timesortfrom'] = int(time.time())
    if timesort_to is not None:
        params['timesortto'] = timesort_to
    return _call_api(token, 'core_calendar_get_action_events_by_timesort', **params)


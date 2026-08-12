"""Moodle Web Services API client.

Gọi các hàm API REST của Moodle thông qua token (lấy từ GitHub Secrets).
Tất cả hàm trả về dữ liệu JSON đã parse, hoặc None nếu có lỗi.
"""
import logging
import requests

MOODLE_API_BASE = "https://courses.fit.hcmus.edu.vn/webservice/rest/server.php"


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
        response = requests.get(MOODLE_API_BASE, params=all_params, timeout=30)
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

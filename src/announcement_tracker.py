"""Theo dõi nội dung mới trên Moodle và gửi thông báo qua Discord.

Module này quét toàn bộ khóa học trên Moodle, phát hiện:
- Tài liệu mới được upload (slide, PDF, ...)
- Bài tập mới được tạo
- Bài đăng mới trên diễn đàn (thông báo từ thầy cô)
- Nội dung đã cập nhật

Và gửi thông báo vào kênh Discord tương ứng cho từng môn học.
"""
import logging
import re

from src.moodle_api import (
    get_site_info, get_enrolled_courses, get_course_contents,
    get_course_forums, get_forum_discussions
)
from src.moodle_parser import extract_subject, extract_display_name, slugify_channel_name
from src.discord_api import get_guild_channels, create_channel, send_message, rename_channel
from src.db_queries import (
    get_or_create_course, get_known_modules_for_course,
    upsert_module, has_modules, get_known_discussion_ids,
    insert_discussion, update_course_crawl_time
)

# ==================== HẰNG SỐ ====================

# Mapping loại module Moodle → (emoji, tên tiếng Việt)
MODULE_TYPES = {
    'resource': ('📄', 'Tài liệu'),
    'assign': ('📝', 'Bài tập'),
    'forum': ('💬', 'Diễn đàn'),
    'url': ('🔗', 'Đường dẫn'),
    'quiz': ('❓', 'Bài kiểm tra'),
    'page': ('📃', 'Trang nội dung'),
    'folder': ('📁', 'Thư mục'),
    'label': ('🏷️', 'Nhãn'),
    'choice': ('🗳️', 'Bình chọn'),
    'feedback': ('📊', 'Khảo sát'),
    'workshop': ('🔧', 'Workshop'),
    'book': ('📖', 'Sách'),
    'glossary': ('📒', 'Thuật ngữ'),
    'wiki': ('📝', 'Wiki'),
    'chat': ('💭', 'Chat'),
    'lesson': ('📚', 'Bài học'),
    'scorm': ('🎓', 'SCORM'),
    'lti': ('🔌', 'LTI'),
}

# Các loại module nên bỏ qua (thường là text trang trí, không quan trọng)
SKIP_MODULE_TYPES = {'label'}


# ==================== LOGIC CHÍNH ====================

def check_moodle_updates(bot_token, guild_id, moodle_token, conn):
    """Quét Moodle để phát hiện nội dung mới và gửi thông báo Discord.

    Args:
        bot_token: Discord Bot token.
        guild_id: Discord Server (Guild) ID.
        moodle_token: Moodle Web Services token.
        conn: Database connection.
    """
    # === Bước 1: Xác thực token ===
    site_info = get_site_info(moodle_token)
    if not site_info or 'userid' not in site_info:
        logging.error("Không thể xác thực Moodle token. Token có thể đã hết hạn.")
        return

    userid = site_info['userid']
    username = site_info.get('fullname', 'Unknown')
    logging.info(f"Moodle: Đã xác thực — {username} (ID: {userid})")

    # === Bước 2: Lấy danh sách khóa học ===
    courses = get_enrolled_courses(moodle_token, userid)
    if not courses:
        logging.warning("Moodle: Không tìm thấy khóa học nào.")
        return

    logging.info(f"Moodle: Tìm thấy {len(courses)} khóa học.")

    # === Bước 3: Kiểm tra lần chạy đầu tiên ===
    is_first_run = not has_modules(conn)

    # Lấy known discussions từ DB
    known_disc_ids = get_known_discussion_ids(conn)

    new_modules = []          # (course_info, module_dict)
    updated_modules = []      # (course_info, module_dict)
    new_discussions = []      # (course_info, discussion_dict)

    # === Bước 4: Quét toàn bộ nội dung ===
    for course in courses:
        course_id = course['id']
        course_fullname = course.get('fullname', '')
        course_shortname = course.get('shortname', '')
        
        # Lấy tên hiển thị (tiếng Việt) từ fullname
        display_name = extract_display_name(course_fullname)

        # Lấy mã môn (VD: CSC10014) từ shortname
        subject_code = extract_subject(course_shortname)
        
        # Nếu shortname bị lỗi không ra được mã môn, thì lấy tạm display_name làm mã môn luôn
        if subject_code == "General" and display_name:
            subject_code = display_name

        # Tạo hoặc tìm khóa học trong DB (cập nhật display_name nếu có)
        db_course_id = get_or_create_course(
            conn, subject_code, lms_courses_id=course_id, display_name=display_name
        )
        update_course_crawl_time(conn, db_course_id)

        course_info = {
            'id': course_id,
            'db_id': db_course_id,
            'shortname': course_shortname,
            'fullname': course_fullname,
            'subject': subject_code,
            'display_name': display_name,
        }

        # Lấy known modules cho course này từ DB
        known_modules = get_known_modules_for_course(conn, db_course_id)

        # 4a: Quét nội dung khóa học (files, assignments, quizzes, ...)
        contents = get_course_contents(moodle_token, course_id)
        if contents:
            for section in contents:
                for module in section.get('modules', []):
                    modname = module.get('modname', '')

                    # Bỏ qua các loại module không quan trọng
                    if modname in SKIP_MODULE_TYPES:
                        continue

                    lms_mod_id = str(module['id'])

                    # Lấy timemodified mới nhất (so sánh cả module và file contents)
                    mod_time = module.get('timemodified', 0) or 0
                    for content_file in module.get('contents', []):
                        file_time = content_file.get('timemodified', 0) or 0
                        if file_time > mod_time:
                            mod_time = file_time

                    # Upsert module vào DB
                    upsert_module(
                        conn, db_course_id, lms_mod_id,
                        modname, module.get('name', 'N/A'), mod_time
                    )

                    # So sánh với dữ liệu cũ (chỉ khi không phải lần chạy đầu)
                    if not is_first_run:
                        old_time = known_modules.get(lms_mod_id, None)
                        if old_time is None:
                            new_modules.append((course_info, module))
                        elif mod_time > old_time:
                            updated_modules.append((course_info, module))

        # 4b: Quét bài đăng trên diễn đàn
        forums = get_course_forums(moodle_token, course_id)
        if forums:
            for forum in forums:
                discussions = get_forum_discussions(moodle_token, forum['id'])
                if discussions:
                    for disc in discussions:
                        disc_id = str(disc.get('discussion', disc.get('id', '')))

                        # Insert discussion vào DB (bỏ qua nếu đã tồn tại)
                        insert_discussion(
                            conn, db_course_id, disc_id,
                            forum.get('name', 'Forum'),
                            disc.get('subject', disc.get('name', 'N/A')),
                            disc.get('userfullname', 'N/A')
                        )

                        if not is_first_run:
                            if disc_id not in known_disc_ids:
                                new_discussions.append((course_info, {
                                    **disc,
                                    'forum_name': forum.get('name', 'Forum'),
                                }))

    # === Bước 5: Xử lý kết quả ===
    if is_first_run:
        logging.info(
            f"Moodle tracker đã khởi tạo từ {len(courses)} khóa học."
        )
        return

    total_changes = len(new_modules) + len(updated_modules) + len(new_discussions)
    if total_changes == 0:
        logging.info("Moodle: Không có cập nhật mới.")
        return

    logging.info(
        f"Moodle: Phát hiện {total_changes} thay đổi — "
        f"{len(new_modules)} mới, {len(updated_modules)} cập nhật, "
        f"{len(new_discussions)} bài đăng mới."
    )

    # === Bước 6: Gửi thông báo Discord ===
    channels = get_guild_channels(bot_token, guild_id)
    channel_map = {c['name']: c['id'] for c in channels if c.get('type') == 0}

    for course_info, module in new_modules:
        _send_module_notification(
            bot_token, guild_id, channel_map, course_info, module, is_update=False
        )

    for course_info, module in updated_modules:
        _send_module_notification(
            bot_token, guild_id, channel_map, course_info, module, is_update=True
        )

    for course_info, disc in new_discussions:
        _send_discussion_notification(
            bot_token, guild_id, channel_map, course_info, disc
        )


# ==================== GỬI THÔNG BÁO ====================

def _ensure_channel(bot_token, guild_id, channel_map, subject_code, display_name=None):
    """Tìm hoặc tạo kênh Discord cho một môn học. Trả về channel_id hoặc None."""
    chan_name = slugify_channel_name(subject_code, display_name)

    # Thử tìm kênh với tên mới (viết-tắt-mã-môn)
    if chan_name in channel_map:
        return channel_map[chan_name]

    # Fallback: thử tìm kênh cũ (chỉ mã môn)
    old_chan_name = slugify_channel_name(subject_code)
    if old_chan_name in channel_map:
        old_id = channel_map[old_chan_name]
        # Phát hiện tên cũ, tiến hành đổi tên sang format mới
        if old_chan_name != chan_name:
            rename_channel(bot_token, old_id, chan_name)
            # Cập nhật lại cache (channel_map)
            channel_map[chan_name] = old_id
            del channel_map[old_chan_name]
        return old_id

    # Tạo kênh mới với tên format mới
    new_channel = create_channel(bot_token, guild_id, chan_name)
    if new_channel:
        channel_map[chan_name] = new_channel['id']
        return new_channel['id']

    return None


def _get_module_display(modname):
    """Lấy emoji và tên hiển thị cho loại module."""
    emoji, label = MODULE_TYPES.get(modname, ('📌', modname.capitalize() if modname else 'Khác'))
    return emoji, label


def _send_module_notification(bot_token, guild_id, channel_map, course_info, module, is_update):
    """Gửi thông báo về module mới hoặc đã cập nhật."""
    channel_id = _ensure_channel(bot_token, guild_id, channel_map, course_info['subject'], course_info.get('display_name'))
    if not channel_id:
        return

    emoji, type_label = _get_module_display(module.get('modname', ''))

    if is_update:
        header = "🔄 **NỘI DUNG CẬP NHẬT** 🔄"
    else:
        header = "🆕 **NỘI DUNG MỚI** 🆕"

    # Danh sách file đính kèm (nếu có)
    files_text = ""
    contents = module.get('contents', [])
    if contents:
        file_names = [c.get('filename', '') for c in contents if c.get('filename')]
        if file_names:
            files_text = "\n📎 **File:** " + ", ".join(file_names[:5])
            if len(file_names) > 5:
                files_text += f" (+{len(file_names) - 5} file khác)"

    url = module.get('url', '')
    url_text = f"\n🔗 **Xem:** {url}" if url else ""

    content = (
        f"{header}\n\n"
        f"📚 **Môn:** {course_info['subject']}\n"
        f"{emoji} **Loại:** {type_label}\n"
        f"📌 **Tên:** {module.get('name', 'N/A')}"
        f"{files_text}"
        f"{url_text}"
    )

    send_message(bot_token, channel_id, content)
    logging.info(f"Đã gửi thông báo module: {module.get('name', '')} ({course_info['subject']})")


def _send_discussion_notification(bot_token, guild_id, channel_map, course_info, disc):
    """Gửi thông báo về bài đăng mới trên diễn đàn."""
    channel_id = _ensure_channel(bot_token, guild_id, channel_map, course_info['subject'], course_info.get('display_name'))
    if not channel_id:
        return

    # Làm sạch HTML khỏi nội dung tin nhắn
    message = disc.get('message', '')
    message = re.sub(r'<[^>]+>', '', message)  # Xóa HTML tags
    message = message.strip()
    if len(message) > 500:
        message = message[:500] + "..."

    author = disc.get('userfullname', 'N/A')
    forum_name = disc.get('forum_name', 'Forum')
    subject = disc.get('subject', disc.get('name', 'N/A'))

    # Tạo link đến bài đăng
    disc_id = disc.get('discussion', disc.get('id', ''))
    url = f"https://courses.fit.hcmus.edu.vn/mod/forum/discuss.php?d={disc_id}"

    content = (
        f"📢 **THÔNG BÁO MỚI** 📢\n\n"
        f"📚 **Môn:** {course_info['subject']}\n"
        f"💬 **Diễn đàn:** {forum_name}\n"
        f"👤 **Từ:** {author}\n"
        f"📝 **Tiêu đề:** {subject}\n"
    )

    if message:
        # Discord quote format
        quoted = "\n".join(f"> {line}" for line in message.split("\n")[:10])
        content += f"\n{quoted}\n"

    content += f"\n🔗 **Xem chi tiết:** {url}"

    send_message(bot_token, channel_id, content)
    logging.info(f"Đã gửi thông báo bài đăng: {subject} ({course_info['subject']})")

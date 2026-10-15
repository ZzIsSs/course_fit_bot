"""Tìm hoặc tạo kênh Discord của một môn học (dùng chung cho notify, announcements, sync-channels)."""
import logging

from course_bot.db.repositories.courses import get_course_discord_category, set_course_discord_category
from course_bot.domain.course_naming import slugify_channel_name
from course_bot.integrations.discord.rest import create_channel, rename_channel, resolve_category

# Kết quả resolve_course_channel
EXISTED = "existed"              # kênh tên mới đã có
RENAMED = "renamed"              # kênh tên cũ (chỉ mã môn) đã được đổi sang tên mới
RENAME_FAILED = "rename_failed"  # có kênh tên cũ nhưng đổi tên lỗi: vẫn trả id kênh cũ
CREATED = "created"              # đã tạo kênh mới
FAILED = "failed"                # tạo kênh lỗi: không có kênh để gửi


def resolve_course_channel(bot_token, guild_id, conn, channel_map, category_map,
                           subject_code, display_name=None, semester_index=None):
    """Trả về (channel_id, outcome) cho kênh của môn `subject_code`.

    Thứ tự: kênh tên mới -> kênh tên cũ (đổi sang tên mới) -> tạo kênh trong
    category "kì N" (hoặc category đã gán tay nếu không biết học kỳ).
    `channel_map` và `category_map` là cache theo tên, được cập nhật tại chỗ.
    """
    chan_name = slugify_channel_name(subject_code, display_name)
    if chan_name in channel_map:
        return channel_map[chan_name], EXISTED

    old_chan_name = slugify_channel_name(subject_code)
    if old_chan_name in channel_map:
        old_id = channel_map[old_chan_name]
        if rename_channel(bot_token, old_id, chan_name):
            channel_map[chan_name] = old_id
            del channel_map[old_chan_name]
            logging.info(f"Đã rename #{old_chan_name} → #{chan_name}")
            return old_id, RENAMED
        return old_id, RENAME_FAILED

    if semester_index is not None:
        category_id = resolve_category(bot_token, guild_id, category_map, f"kì {semester_index}")
    else:
        # Không nhận diện được học kỳ → dùng category đã gán tay qua scripts/ops/set_category.py
        category_id = get_course_discord_category(conn, subject_code)

    new_channel = create_channel(bot_token, guild_id, chan_name, parent_id=category_id)
    if not new_channel:
        return None, FAILED

    channel_map[chan_name] = new_channel['id']
    if category_id:
        set_course_discord_category(conn, subject_code, category_id)
    return new_channel['id'], CREATED

"""Job --dedup: dọn tin nhắn trùng lặp của bot."""
import logging

from course_bot.core.config import load_env
from course_bot.integrations.discord.rest import (
    get_bot_user,
    get_guild_channels,
    deduplicate_channel_messages,
)


# ==================== DỌN DẸP TIN NHẮN TRÙNG LẶP ====================

def run_deduplicate_messages(channel_name=None, scan_limit=100, dry_run=False):
    """Quét và dọn dẹp các tin nhắn bị gửi trùng lặp của Bot trên các kênh Discord.
    
    Chỉ giữ lại duy nhất 1 tin nhắn mới nhất và xóa toàn bộ các bản sao còn lại.
    
    Args:
        channel_name (str, optional): Tên kênh cụ thể cần dọn dẹp (bỏ tiền tố #).
                                      Nếu None, sẽ quét qua tất cả các kênh text trên server.
        scan_limit (int): Số lượng tin nhắn tối đa cần quét trên mỗi kênh (mặc định 100).
        dry_run (bool): Nếu True, chỉ chạy thử nghiệm báo cáo thống kê, không thực hiện xóa thật.
    """
    env = load_env()
    if not env:
        return

    bot_token = env['bot_token']
    guild_id = env['guild_id']

    bot_user = get_bot_user(bot_token)
    bot_user_id = bot_user['id'] if bot_user else None
    if not bot_user_id:
        logging.error("Không thể xác thực thông tin Bot qua Discord API. Vui lòng kiểm tra lại DISCORD_BOT_TOKEN.")
        return

    logging.info(f"Bot Identity: {bot_user.get('username')}#{bot_user.get('discriminator')} (ID: {bot_user_id})")

    channels = get_guild_channels(bot_token, guild_id)
    # Lọc các kênh Text (type == 0) và Announcement (type == 5)
    text_channels = [c for c in channels if c.get('type') in (0, 5)]

    if channel_name:
        # Bỏ dấu # nếu người dùng nhập "#ten-kenh"
        target_name = channel_name.lstrip('#')
        text_channels = [c for c in text_channels if c.get('name') == target_name]
        if not text_channels:
            logging.warning(f"Không tìm thấy kênh text nào có tên: #{target_name}")
            return

    mode_text = "[DRY RUN - KIỂM TRA]" if dry_run else "[XÓA THỰC TẾ]"
    logging.info(
        f"{mode_text} Bắt đầu quét trùng lặp trên {len(text_channels)} kênh "
        f"(Giới hạn quét: {scan_limit} tin/kênh)..."
    )

    total_scanned = 0
    total_bot_messages = 0
    total_duplicates = 0
    total_deleted = 0
    total_failed = 0

    for ch in text_channels:
        ch_id = ch['id']
        ch_name = ch.get('name', ch_id)
        logging.info(f"--------------------------------------------------")
        logging.info(f"Đang kiểm tra kênh #{ch_name} (ID: {ch_id})...")

        stats = deduplicate_channel_messages(
            token=bot_token,
            channel_id=ch_id,
            bot_user_id=bot_user_id,
            scan_limit=scan_limit,
            dry_run=dry_run
        )

        total_scanned += stats['scanned']
        total_bot_messages += stats['bot_messages']
        total_duplicates += stats['duplicates_found']
        total_deleted += stats['deleted']
        total_failed += stats['failed']

    action_label = "Phát hiện (sẽ bị xóa)" if dry_run else "Đã xóa thành công"
    logging.info(
        f"\n==================================================\n"
        f"        TỔNG KẾT DỌN DẸP TIN NHẮN TRÙNG LẶP\n"
        f"==================================================\n"
        f"• Chế độ: {'Mô phỏng (Dry-run)' if dry_run else 'Thực thi thật'}\n"
        f"• Số kênh đã quét: {len(text_channels)}\n"
        f"• Tổng số tin nhắn đã duyệt: {total_scanned}\n"
        f"• Tổng số tin nhắn của Bot: {total_bot_messages}\n"
        f"• Số tin nhắn trùng lặp tìm thấy: {total_duplicates}\n"
        f"• {action_label}: {total_duplicates if dry_run else total_deleted}\n"
        f"• Lỗi / Thất bại: {total_failed}\n"
        f"=================================================="
    )

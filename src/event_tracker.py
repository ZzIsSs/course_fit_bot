import logging

from src.discord_api import get_reaction_users, update_scheduled_event
from src.db_queries import get_tracked_deadlines, mark_deadline_completed


# ==================== KIỂM TRA HOÀN THÀNH ====================

def check_completions(token, guild_id, bot_user_id, conn, notion=None, gcal=None):
    """Kiểm tra reactions ✅ trên tin nhắn deadline, đánh dấu hoàn thành nếu có người react.

    Args:
        token: Discord Bot token.
        guild_id: Discord Server (Guild) ID.
        bot_user_id: ID của bot (để lọc bỏ reaction của chính bot).
        conn: Database connection.
        notion: NotionSync instance (tùy chọn — đồng bộ trạng thái lên Notion).
        gcal: GoogleCalendarSync instance (tùy chọn — đồng bộ trạng thái lên Google Calendar).
    """
    deadlines = get_tracked_deadlines(conn)

    for dl in deadlines:
        users = get_reaction_users(token, dl['discord_channel_id'], dl['discord_message_id'])
        # Filter out bot's own reaction
        non_bot_users = [u for u in users if u.get('id') != bot_user_id]

        if non_bot_users:
            completed_by = non_bot_users[0].get('username', 'Unknown')
            mark_deadline_completed(conn, dl['deadlines_id'], completed_by)
            logging.info(f"Deadline {dl['lms_deadlines_id']} marked as completed by {completed_by}")

            # Update scheduled event status to COMPLETED
            if dl.get('discord_event_id'):
                update_scheduled_event(token, guild_id, dl['discord_event_id'], 3)

            # Đồng bộ trạng thái Done lên Notion
            if notion:
                notion.mark_completed(dl['lms_deadlines_id'], completed_by)

            # Đồng bộ trạng thái Done lên Google Calendar
            if gcal:
                gcal.mark_completed(dl['lms_deadlines_id'], completed_by=completed_by, task_name=dl.get('deadline_name'))


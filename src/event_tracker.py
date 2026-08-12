import logging

from src.discord_api import get_reaction_users, update_scheduled_event

# ==================== KIỂM TRA HOÀN THÀNH ====================

def check_completions(token, guild_id, bot_user_id, state):
    """Kiểm tra reactions ✅ trên tin nhắn deadline, đánh dấu hoàn thành nếu có người react."""
    changed = False
    for eid, evt_state in state.get('events', {}).items():
        # Skip if already completed or no message tracked
        if evt_state.get('completed') or not evt_state.get('message_id'):
            continue

        users = get_reaction_users(token, evt_state['channel_id'], evt_state['message_id'])
        # Filter out bot's own reaction
        non_bot_users = [u for u in users if u.get('id') != bot_user_id]

        if non_bot_users:
            evt_state['completed'] = True
            evt_state['completed_by'] = non_bot_users[0].get('username', 'Unknown')
            changed = True
            logging.info(f"Deadline {eid} marked as completed by {evt_state['completed_by']}")

            # Update scheduled event status to COMPLETED
            if evt_state.get('scheduled_event_id'):
                update_scheduled_event(token, guild_id, evt_state['scheduled_event_id'], 3)

    return changed

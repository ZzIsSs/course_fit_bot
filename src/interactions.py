"""Xử lý Discord Interactions (Slash Commands).

Module này xác thực chữ ký từ Discord và dispatch lệnh tương ứng.
Được gọi từ api/interactions.py (Vercel entry point).
"""
import os
from datetime import datetime, timezone

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from src.database import get_db
from src.db_queries import (
    get_or_create_course, insert_deadline_manual, get_course_name_by_chat_id,
    get_deadlines_for_course_or_all
)
from src.utils import ensure_tz, parse_due_time
from src.config import LOCAL_TZ

import re
import logging

DISCORD_PUBLIC_KEY = os.environ.get('DISCORD_PUBLIC_KEY')


def sanitize_discord_text(text):
    """Khử nguy cơ Mention Injection (@everyone, @here, role ping) và ký tự rác."""
    if not text:
        return ""
    # Lọc bỏ ký tự điều khiển trước
    text = "".join(ch for ch in str(text) if ch.isprintable() or ch in '\n\r\t')
    text = text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
    text = re.sub(r'<@&(\d+)>', lambda m: '@\u200b&role', text)
    return " ".join(text.strip().split())


def verify_signature(signature, timestamp, body):
    if not DISCORD_PUBLIC_KEY:
        return False
    try:
        VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY)).verify(
            f'{timestamp}{body}'.encode(), bytes.fromhex(signature))
        return True
    except (BadSignatureError, Exception):
        return False


def handle_interaction(interaction, database_url):
    try:
        command_name = interaction.get('data', {}).get('name')
        if command_name == 'add_deadline':
            return _handle_add_deadline(interaction, database_url)
        if command_name == 'deadline':
            return _handle_deadline(interaction, database_url)
        return _ephemeral("❌ Lệnh chưa được hỗ trợ.")
    except Exception as e:
        logging.exception(f"Lỗi unhandled khi xử lý Discord interaction: {e}")
        return _ephemeral("⚠️ Hệ thống gặp sự cố tạm thời khi xử lý lệnh. Vui lòng thử lại sau!")


# ==================== TIỆN ÍCH ====================

def _get_option(options, name):
    for opt in options or []:
        if opt.get('name') == name:
            return opt.get('value')
    return None


def _ephemeral(text):
    """Chỉ người gõ lệnh thấy được (dùng cho lỗi và tra cứu riêng tư)."""
    return {"type": 4, "data": {"content": text, "flags": 64}}


def _public(text):
    """Cả kênh đều thấy được (dùng khi hành động ảnh hưởng đến mọi người,
    ví dụ như xác nhận đã thêm deadline mới).
    Khóa allowed_mentions để chống mention injection từ nội dung người dùng nhập.
    """
    return {
        "type": 4,
        "data": {
            "content": text,
            "allowed_mentions": {"parse": []}
        }
    }


# ==================== HANDLER: /add_deadline ====================

def _handle_add_deadline(interaction, database_url):
    options = interaction.get('data', {}).get('options', [])
    channel_id = interaction.get('channel_id')
    user_info = (interaction.get('member') or {}).get('user') or interaction.get('user') or {}
    raw_username = user_info.get('username', 'Unknown')
    username = sanitize_discord_text(raw_username)[:95] or 'Unknown'

    raw_name = _get_option(options, 'ten')
    raw_due = _get_option(options, 'han_chot')
    raw_course = _get_option(options, 'mon')

    name = sanitize_discord_text(raw_name)[:250]
    due_time = parse_due_time(raw_due or '', LOCAL_TZ)

    if not name or due_time is None:
        return _ephemeral(
            "❌ Hạn chót sai định dạng hoặc tên bài trống. Ví dụ: `25/12/2026 23:59` "
            "hoặc chỉ `25/12/2026` (bot tự set 23:59)."
        )

    with get_db(database_url) as conn:
        clean_course_input = sanitize_discord_text(raw_course).upper()[:100] if raw_course else None
        course_name = clean_course_input if clean_course_input else get_course_name_by_chat_id(conn, channel_id)
        if not course_name:
            return _ephemeral("❌ Không xác định được môn. Dùng lệnh trong kênh của môn, hoặc điền option `mon`.")

        courses_id = get_or_create_course(conn, course_name)
        interaction_id = str(interaction.get('id', 'unknown'))[:40]
        deadlines_id = insert_deadline_manual(
            conn, courses_id, name, f"manual-{interaction_id}", due_time,
            source_url=f"Discord (thêm bởi {username})", added_by=username
        )

    due_local = due_time.astimezone(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')

    # deadlines_id là None khi phát hiện bài tập đã tồn tại (chống trùng lặp kép:
    # cùng môn, cùng tên, cùng hạn chót hoặc retry cùng interaction id)
    header = "📌 **Deadline nội bộ mới**"
    if deadlines_id is None:
        header += " _(xác nhận lặp lại — deadline này đã được lưu từ trước, không tạo trùng)_"

    return _public(
        f"{header}\n"
        f"📚 Môn: **{course_name}**\n"
        f"📝 {name}\n"
        f"⏰ Hạn chót: {due_local}\n"
        f"➕ Thêm bởi: {username}\n\n"
        f"_Bot sẽ gửi thông báo chính thức kèm nhắc nhở vào kênh môn trong tối đa 30 phút._"
    )


# ==================== HANDLER: /deadline ====================

def _handle_deadline(interaction, database_url):
    options = interaction.get('data', {}).get('options', [])
    channel_id = interaction.get('channel_id')

    course_input = _get_option(options, 'mon')
    limit = _get_option(options, 'so_luong') or 5
    limit = max(1, min(int(limit), 15))

    with get_db(database_url) as conn:
        course_name = course_input.strip().upper() if course_input else get_course_name_by_chat_id(conn, channel_id)
        rows = get_deadlines_for_course_or_all(conn, course_name)

    now = datetime.now(timezone.utc)
    upcoming = [d for d in rows if not d['completed'] and ensure_tz(d['due_time']) >= now]
    upcoming.sort(key=lambda d: d['due_time'])
    upcoming = upcoming[:limit]

    scope_label = f"— {course_name}" if course_name else "— tất cả các môn"

    if not upcoming:
        return _ephemeral(f"✅ Không có deadline sắp tới nào {scope_label}.")

    lines = [f"📅 **DEADLINE SẮP TỚI {scope_label}**"]
    for d in upcoming:
        due_local = ensure_tz(d['due_time']).astimezone(LOCAL_TZ).strftime('%d/%m %H:%M')
        lines.append(f"▸ [{d['course_name']}] {d['deadline_name']} — ⏰ {due_local}")

    return _ephemeral("\n".join(lines))

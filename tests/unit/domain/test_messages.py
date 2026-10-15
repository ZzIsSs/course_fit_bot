"""Unit test cho domain/messages.py: quy tắc sanitize và mẫu tin nhắn deadline."""
from datetime import datetime, timezone

import pytest

from course_bot.domain.messages import build_deadline_message, build_event_url, sanitize_discord_text
from course_bot.domain.reminders import NEW, ONE_DAY, THREE_DAYS

ZWSP = "​"


# ==================== sanitize_discord_text ====================

@pytest.mark.parametrize("raw, expected", [
    (None, ""),
    ("", ""),
    (0, ""),
    ("  Bài   tập\t1 \n", "Bài tập 1"),                     # gộp mọi khoảng trắng
    ("@everyone nộp bài", f"@{ZWSP}everyone nộp bài"),
    ("@here", f"@{ZWSP}here"),
    ("<@&123456> xem", f"@{ZWSP}&role xem"),                # ping role
    ("<@&1><@&2>", f"@{ZWSP}&role@{ZWSP}&role"),
    ("<@123>", "<@123>"),                                   # ping user giữ nguyên
    ("a\x00b\x07c", "abc"),                                 # ký tự điều khiển bị bỏ
    ("dòng 1\r\ndòng 2", "dòng 1 dòng 2"),
    (12345, "12345"),
])
def test_sanitize_discord_text(raw, expected):
    assert sanitize_discord_text(raw) == expected


def test_sanitize_result_cannot_mention():
    text = sanitize_discord_text("@everyone @here <@&99>")
    assert "@everyone" not in text and "@here" not in text and "<@&" not in text


# ==================== build_event_url ====================

@pytest.mark.parametrize("uid, url", [
    ("123@courses.fit.hcmus.edu.vn",
     "https://courses.fit.hcmus.edu.vn/calendar/view.php?view=day&course=1&time=upcoming#event_123"),
    ("abc@x", "https://courses.fit.hcmus.edu.vn/calendar/view.php?view=upcoming"),
    ("manual-1", "https://courses.fit.hcmus.edu.vn/calendar/view.php?view=upcoming"),
])
def test_build_event_url(uid, url):
    assert build_event_url(uid) == url


# ==================== build_deadline_message ====================

DUE = datetime(2026, 12, 25, 16, 59, tzinfo=timezone.utc)   # 23:59 giờ VN


@pytest.mark.parametrize("msg_type, header", [
    (NEW, "🚨 **DEADLINE MỚI** 🚨"),
    (THREE_DAYS, "⚠️ **NHẮC NHỞ: CÒN 3 NGÀY** ⚠️"),
    (ONE_DAY, "🆘 **KHẨN CẤP: CÒN 24 GIỜ** 🆘"),
])
def test_build_deadline_message(msg_type, header):
    assert build_deadline_message(msg_type, "CSC10014", "Bài tập 1", DUE, "http://x") == (
        f"@everyone {header}\n\n"
        "📌 **Môn:** CSC10014\n"
        "📝 **Nội dung:** Bài tập 1\n"
        "⏰ **Hạn chót:** 25/12/2026 23:59\n"
        "🔗 **Xem:** http://x"
        "\n\n✅ *React ✅ vào tin nhắn này khi đã hoàn thành!*"
    )


def test_build_deadline_message_unknown_type():
    with pytest.raises(KeyError):
        build_deadline_message("2_DAYS", "A", "B", DUE, "u")

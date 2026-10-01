# -*- coding: utf-8 -*-
"""Unit tests cho tính năng Message Deduplication & Cleanup."""
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.discord_api import (
    filter_duplicate_bot_messages,
    is_message_under_14_days,
    get_channel_messages,
    bulk_delete_messages,
    deduplicate_channel_messages,
    _request_with_retry
)


def test_filter_duplicate_bot_messages():
    bot_id = "bot_123"
    
    # Giả lập danh sách tin nhắn từ mới nhất (đầu list) đến cũ nhất (cuối list)
    messages = [
        # Msg 1 (Mới nhất): Bot gửi Deadline 1
        {
            "id": "1003",
            "author": {"id": bot_id, "bot": True},
            "content": "🚨 **DEADLINE MỚI**: Bài tập 1",
            "embeds": []
        },
        # Msg 2: User thường gửi tin nhắn giống nội dung bot (Không được xóa!)
        {
            "id": "1002",
            "author": {"id": "user_456", "bot": False},
            "content": "🚨 **DEADLINE MỚI**: Bài tập 1",
            "embeds": []
        },
        # Msg 3: Bot gửi tin nhắn Deadline 2
        {
            "id": "1001",
            "author": {"id": bot_id, "bot": True},
            "content": "🚨 **DEADLINE MỚI**: Bài tập 2",
            "embeds": []
        },
        # Msg 4 (Cũ hơn): Bot gửi lặp lại Deadline 1 (Phải xóa!)
        {
            "id": "1000",
            "author": {"id": bot_id, "bot": True},
            "content": "🚨 **DEADLINE MỚI**: Bài tập 1",
            "embeds": []
        },
        # Msg 5 (Rất cũ): Bot gửi lặp lại Deadline 1 lần nữa (Phải xóa!)
        {
            "id": "999",
            "author": {"id": bot_id, "bot": True},
            "content": "  🚨 **DEADLINE MỚI**: Bài tập 1  ",
            "embeds": []
        },
        # Msg 6 (Embed mới nhất): Bot gửi Embed title "Thông báo kiểm tra"
        {
            "id": "998",
            "author": {"id": bot_id, "bot": True},
            "content": "",
            "embeds": [{"title": "Thông báo kiểm tra giữa kỳ"}]
        },
        # Msg 7 (Embed cũ hơn): Bot gửi trùng title (Phải xóa!)
        {
            "id": "997",
            "author": {"id": bot_id, "bot": True},
            "content": "Một vài text khác",
            "embeds": [{"title": "Thông báo kiểm tra giữa kỳ"}]
        },
    ]

    duplicates, kept = filter_duplicate_bot_messages(messages, bot_user_id=bot_id)

    dup_ids = [m["id"] for m in duplicates]
    kept_ids = [m["id"] for m in kept]

    print("Duplicates found:", dup_ids)
    print("Kept messages:", kept_ids)

    # 1. Kiểm tra giữ lại đúng 1 bản mới nhất
    assert "1003" in kept_ids, "Bản mới nhất của Bài tập 1 (1003) phải được giữ lại"
    assert "1001" in kept_ids, "Bài tập 2 (1001) duy nhất phải được giữ lại"
    assert "998" in kept_ids, "Embed mới nhất (998) phải được giữ lại"

    # 2. Kiểm tra các bản trùng cũ hơn bị đánh dấu xóa
    assert "1000" in dup_ids, "Bản cũ hơn (1000) của Bài tập 1 phải bị xóa"
    assert "999" in dup_ids, "Bản cũ hơn (999) của Bài tập 1 phải bị xóa"
    assert "997" in dup_ids, "Bản trùng title embed cũ hơn (997) phải bị xóa"

    # 3. Tin nhắn của người dùng thường không bao giờ nằm trong duplicates
    assert "1002" not in dup_ids, "Tin nhắn của user không được đưa vào duplicates"

    print("=> test_filter_duplicate_bot_messages: PASSED!")


def test_is_message_under_14_days():
    now = datetime.now(timezone.utc)

    msg_recent = {
        "id": "1",
        "timestamp": (now - timedelta(days=2)).isoformat()
    }
    msg_old = {
        "id": "2",
        "timestamp": (now - timedelta(days=15)).isoformat()
    }
    msg_z_format = {
        "id": "3",
        "timestamp": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    }

    assert is_message_under_14_days(msg_recent) is True, "Tin 2 ngày tuổi phải < 14 ngày"
    assert is_message_under_14_days(msg_old) is False, "Tin 15 ngày tuổi phải >= 14 ngày"
    assert is_message_under_14_days(msg_z_format) is True, "Tin format Z phải parse được"

    print("=> test_is_message_under_14_days: PASSED!")


def test_get_channel_messages_pagination():
    token = "fake_token"
    channel_id = "chan_123"

    # Giả lập trả về 100 tin đợt 1, 50 tin đợt 2
    batch1 = [{"id": f"msg_{i}"} for i in range(100, 0, -1)]
    batch2 = [{"id": f"msg_{i}"} for i in range(0, -50, -1)]

    def mock_request(method, url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "before=" in url:
            resp.json.return_value = batch2
        else:
            resp.json.return_value = batch1
        return resp

    with patch("src.discord_api._request_with_retry", side_effect=mock_request):
        # Yêu cầu lấy 150 tin
        result = get_channel_messages(token, channel_id, limit=150)
        assert len(result) == 150, f"Expected 150 messages, got {len(result)}"
        assert result[0]["id"] == "msg_100"
        assert result[-1]["id"] == "msg_-49"

    print("=> test_get_channel_messages_pagination: PASSED!")


def test_deduplicate_fallback_on_403():
    """Kiểm tra nếu Bulk Delete trả về 403 (thiếu quyền), tự động fallback sang single delete."""
    token = "fake_token"
    channel_id = "chan_123"
    bot_id = "bot_123"

    now = datetime.now(timezone.utc)
    messages = [
        {"id": "msg_3", "author": {"id": bot_id, "bot": True}, "content": "Dup Text", "timestamp": now.isoformat()},
        {"id": "msg_2", "author": {"id": bot_id, "bot": True}, "content": "Dup Text", "timestamp": now.isoformat()},
        {"id": "msg_1", "author": {"id": bot_id, "bot": True}, "content": "Dup Text", "timestamp": now.isoformat()}
    ]

    # Mock get_channel_messages trả về 3 tin (1 kept, 2 duplicates)
    with patch("src.discord_api.get_channel_messages", return_value=messages):
        # Mock bulk_delete trả về False, 403 (PERMISSION_DENIED)
        with patch("src.discord_api.bulk_delete_messages", return_value=(False, 403, "PERMISSION_DENIED")) as mock_bulk:
            # Mock delete_message trả về True
            with patch("src.discord_api.delete_message", return_value=True) as mock_single:
                stats = deduplicate_channel_messages(token, channel_id, bot_user_id=bot_id, scan_limit=10)

                assert stats["duplicates_found"] == 2
                assert stats["deleted"] == 2
                # Kiểm tra bulk delete đã được thử
                assert mock_bulk.called
                # Kiểm tra fallback single delete đã được gọi cho cả 2 tin trùng
                assert mock_single.call_count == 2

    print("=> test_deduplicate_fallback_on_403: PASSED!")


def test_rate_limit_retry():
    """Kiểm tra _request_with_retry xử lý mã 429 và sleep đúng thời gian retry_after."""
    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.json.return_value = {"retry_after": 0.05}

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {"success": True}

    with patch("requests.request", side_effect=[resp_429, resp_200]):
        with patch("time.sleep") as mock_sleep:
            resp = _request_with_retry("GET", "https://discord.com/test", max_retries=3)
            assert resp.status_code == 200
            assert mock_sleep.called

    print("=> test_rate_limit_retry: PASSED!")


if __name__ == "__main__":
    test_filter_duplicate_bot_messages()
    test_is_message_under_14_days()
    test_get_channel_messages_pagination()
    test_deduplicate_fallback_on_403()
    test_rate_limit_retry()
    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<")

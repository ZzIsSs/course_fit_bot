"""Unit test cho services/channel_resolver.py -> resolve_course_channel."""
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from course_bot.services.channel_resolver import (
    CREATED, EXISTED, FAILED, RENAME_FAILED, RENAMED, resolve_course_channel,
)

SUBJECT = "CSC10014"
DISPLAY = "Nhập Môn Trí Tuệ Nhân Tạo"
NEW_CHAN = "nmttnt-csc10014"
OLD_CHAN = "csc10014"


@pytest.fixture
def api():
    names = ["rename_channel", "resolve_category", "create_channel",
             "get_course_discord_category", "set_course_discord_category"]
    with ExitStack() as stack:
        yield {n: stack.enter_context(patch(f"course_bot.services.channel_resolver.{n}")) for n in names}


def resolve(channel_map, semester_index=4, display_name=DISPLAY, category_map=None):
    return resolve_course_channel(
        "tok", "g", "conn", channel_map,
        category_map if category_map is not None else {"kì 4": "cat-4"},
        SUBJECT, display_name, semester_index)


def test_new_name_exists(api):
    assert resolve({NEW_CHAN: "c1"}) == ("c1", EXISTED)
    api["rename_channel"].assert_not_called()
    api["create_channel"].assert_not_called()


def test_new_name_preferred_over_old(api):
    assert resolve({NEW_CHAN: "c1", OLD_CHAN: "c-old"}) == ("c1", EXISTED)
    api["rename_channel"].assert_not_called()


def test_old_name_is_renamed(api):
    channel_map = {OLD_CHAN: "c-old"}
    assert resolve(channel_map) == ("c-old", RENAMED)
    api["rename_channel"].assert_called_once_with("tok", "c-old", NEW_CHAN)
    assert channel_map == {NEW_CHAN: "c-old"}


def test_rename_failure_keeps_cache_and_returns_old_channel(api):
    api["rename_channel"].return_value = None
    channel_map = {OLD_CHAN: "c-old"}
    assert resolve(channel_map) == ("c-old", RENAME_FAILED)
    assert channel_map == {OLD_CHAN: "c-old"}
    api["create_channel"].assert_not_called()


def test_without_display_name_old_and_new_name_are_the_same(api):
    assert resolve({OLD_CHAN: "c1"}, display_name=None) == ("c1", EXISTED)
    api["rename_channel"].assert_not_called()


def test_creates_in_semester_category(api):
    api["resolve_category"].return_value = "cat-4"
    api["create_channel"].return_value = {"id": "c-new"}
    channel_map = {}
    assert resolve(channel_map) == ("c-new", CREATED)
    api["resolve_category"].assert_called_once_with("tok", "g", {"kì 4": "cat-4"}, "kì 4")
    api["get_course_discord_category"].assert_not_called()
    api["create_channel"].assert_called_once_with("tok", "g", NEW_CHAN, parent_id="cat-4")
    api["set_course_discord_category"].assert_called_once_with("conn", SUBJECT, "cat-4")
    assert channel_map == {NEW_CHAN: "c-new"}


def test_creates_with_manual_category_when_semester_unknown(api):
    api["get_course_discord_category"].return_value = "cat-manual"
    api["create_channel"].return_value = {"id": "c-new"}
    assert resolve({}, semester_index=None) == ("c-new", CREATED)
    api["resolve_category"].assert_not_called()
    api["get_course_discord_category"].assert_called_once_with("conn", SUBJECT)
    api["create_channel"].assert_called_once_with("tok", "g", NEW_CHAN, parent_id="cat-manual")


def test_creates_without_category(api):
    api["get_course_discord_category"].return_value = None
    api["create_channel"].return_value = {"id": "c-new"}
    assert resolve({}, semester_index=None) == ("c-new", CREATED)
    api["create_channel"].assert_called_once_with("tok", "g", NEW_CHAN, parent_id=None)
    api["set_course_discord_category"].assert_not_called()


def test_create_failure(api):
    api["create_channel"].return_value = None
    channel_map = {}
    assert resolve(channel_map) == (None, FAILED)
    assert channel_map == {}
    api["set_course_discord_category"].assert_not_called()


def test_second_call_hits_cache_no_duplicate_channel(api):
    """Gate Phase 8: 2 lần resolve liên tiếp cùng môn không tạo kênh trùng."""
    api["create_channel"].return_value = {"id": "c-new"}
    channel_map = {}
    assert resolve(channel_map) == ("c-new", CREATED)
    assert resolve(channel_map) == ("c-new", EXISTED)
    assert api["create_channel"].call_count == 1

"""
Characterization test cho course_bot/cli.py.

GitHub Actions, Termux cron và widget gọi `python main.py <flag>`. Các test này
chốt flag, message và exit code hiện tại. Mọi job đều bị mock, không gửi gì thật.
"""
import os
import subprocess
import sys
from unittest.mock import patch

import pytest

from course_bot import cli

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

JOBS = [
    "run_main_bot",
    "send_daily_summary",
    "send_progress_report",
    "check_announcements",
    "sync_channels",
    "sync_notion",
    "sync_google_calendar",
    "crawl_deadlines_standalone",
    "run_deduplicate_messages",
]


@pytest.fixture
def jobs():
    patchers = {name: patch(f"course_bot.cli.{name}") for name in JOBS}
    mocks = {name: p.start() for name, p in patchers.items()}
    yield mocks
    for p in patchers.values():
        p.stop()


def _called(mocks):
    return [name for name, m in mocks.items() if m.called]


@pytest.mark.parametrize("argv, job", [
    ([], "run_main_bot"),
    (["--summary"], "send_daily_summary"),
    (["--progress"], "send_progress_report"),
    (["--announcements"], "check_announcements"),
    (["--sync-channels"], "sync_channels"),
    (["--sync-notion"], "sync_notion"),
    (["--sync-gcal"], "sync_google_calendar"),
    (["--sync-google-calendar"], "sync_google_calendar"),
    (["--crawl-deadlines"], "crawl_deadlines_standalone"),
    (["--dedup"], "run_deduplicate_messages"),
    (["--clean-duplicates"], "run_deduplicate_messages"),
    # Tham số thừa sau flag không phải dedup bị bỏ qua
    (["--summary", "extra", "--bogus"], "send_daily_summary"),
])
def test_flag_dispatches_to_job(jobs, argv, job):
    cli.main(argv)
    assert _called(jobs) == [job]
    jobs[job].assert_called_once()


def test_unknown_flag_prints_usage_and_returns(jobs, capsys):
    cli.main(["--bogus"])  # không raise SystemExit, tức exit code 0
    out = capsys.readouterr().out
    assert out == (
        "Unknown argument: --bogus\n"
        "Usage: python main.py [--summary | --progress | --announcements | --sync-channels"
        " | --sync-notion | --sync-gcal | --crawl-deadlines | --dedup]\n"
    )
    assert _called(jobs) == []


def test_dedup_defaults(jobs):
    cli.main(["--dedup"])
    jobs["run_deduplicate_messages"].assert_called_once_with(
        channel_name=None, scan_limit=100, dry_run=False)


def test_dedup_all_options(jobs):
    cli.main(["--dedup", "--channel", "csc10014", "--limit", "5", "--dry-run"])
    jobs["run_deduplicate_messages"].assert_called_once_with(
        channel_name="csc10014", scan_limit=5, dry_run=True)


def test_dedup_options_any_order(jobs):
    cli.main(["--clean-duplicates", "--dry-run", "--limit", "7", "--channel", "x"])
    jobs["run_deduplicate_messages"].assert_called_once_with(
        channel_name="x", scan_limit=7, dry_run=True)


def test_dedup_limit_not_int_exits_1(jobs, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--dedup", "--limit", "abc"])
    assert exc.value.code == 1
    assert capsys.readouterr().out == "Lỗi: --limit phải là số nguyên, nhận được: abc\n"
    assert _called(jobs) == []


@pytest.mark.parametrize("argv, bad", [
    (["--dedup", "--channel"], "--channel"),
    (["--dedup", "--limit"], "--limit"),
    (["--dedup", "--foo"], "--foo"),
    (["--dedup", "--dry-run", "extra"], "extra"),
])
def test_dedup_bad_argument_exits_1(jobs, capsys, argv, bad):
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 1
    assert capsys.readouterr().out == (
        f"Tham số không xác định cho dedup: {bad}\n"
        "Usage: python main.py --dedup [--channel <name>] [--limit <N>] [--dry-run]\n"
    )
    assert _called(jobs) == []


def test_main_py_unknown_flag_exit_code_0():
    """Chạy thật main.py với flag sai: chỉ in usage, không chạy job nào."""
    result = subprocess.run(
        [sys.executable, "main.py", "--bogus"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=60,
    )
    assert result.returncode == 0
    assert result.stdout.startswith("Unknown argument: --bogus\n")

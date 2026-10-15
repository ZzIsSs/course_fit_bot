"""CLI cho các tác vụ định kỳ: map tham số dòng lệnh sang jobs/.

main.py ở root chỉ gọi main() trong file này. GitHub Actions, Termux cron và
các widget trên điện thoại gọi `python main.py <flag>`, nên flag, message và
exit code phải giữ nguyên:
- Không có tham số: chạy run_main_bot.
- Chỉ tham số đầu tiên chọn chế độ; tham số thừa sau đó bị bỏ qua (trừ dedup).
- Flag lạ: in "Unknown argument" + usage, exit 0.
- Tham số dedup sai: in message riêng, exit 1.
"""
import argparse
import sys

from course_bot.core.logging_setup import configure_logging
from course_bot.jobs.notify import run_main_bot
from course_bot.jobs.reports import send_daily_summary, send_progress_report
from course_bot.jobs.announcements import check_announcements
from course_bot.jobs.sync_channels import sync_channels
from course_bot.jobs.sync_external import sync_notion, sync_google_calendar
from course_bot.jobs.dedup import run_deduplicate_messages
from course_bot.jobs.crawl_deadlines import crawl_deadlines_standalone

USAGE = ("Usage: python main.py [--summary | --progress | --announcements | --sync-channels"
         " | --sync-notion | --sync-gcal | --crawl-deadlines | --dedup]")
DEDUP_USAGE = "Usage: python main.py --dedup [--channel <name>] [--limit <N>] [--dry-run]"

# flag -> tên hàm job trong module này (tra lúc chạy để mock.patch có hiệu lực)
MODES = {
    "--summary": "send_daily_summary",
    "--progress": "send_progress_report",
    "--announcements": "check_announcements",
    "--sync-channels": "sync_channels",
    "--sync-notion": "sync_notion",
    "--sync-gcal": "sync_google_calendar",
    "--sync-google-calendar": "sync_google_calendar",
    "--crawl-deadlines": "crawl_deadlines_standalone",
    "--dedup": "dedup",
    "--clean-duplicates": "dedup",
}


class _ArgumentError(Exception):
    """argparse.error() mặc định exit 2; ném lỗi này để tự in message và exit code cũ."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise _ArgumentError(message)


def _build_mode_parser():
    parser = _Parser(prog="python main.py", add_help=False, allow_abbrev=False)
    for flag, job in MODES.items():
        parser.add_argument(flag, dest="mode", action="store_const", const=job)
    return parser


def _build_dedup_parser():
    parser = _Parser(prog="python main.py --dedup", add_help=False, allow_abbrev=False)
    parser.add_argument("--channel", dest="channel_name")
    parser.add_argument("--limit", dest="scan_limit")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    return parser


def _dedup_bad_argument(arg):
    print(f"Tham số không xác định cho dedup: {arg}")
    print(DEDUP_USAGE)
    sys.exit(1)


def _run_dedup(args):
    # Kiểu cũ không nhận "--channel=x": báo lỗi đúng token đó.
    for arg in args:
        if arg.startswith("--") and "=" in arg:
            _dedup_bad_argument(arg)
    try:
        ns, extras = _build_dedup_parser().parse_known_args(args)
    except _ArgumentError:
        # Option thiếu giá trị, ví dụ "--channel" ở cuối.
        missing = next(a for a in reversed(args) if a in ("--channel", "--limit"))
        _dedup_bad_argument(missing)
    if extras:
        _dedup_bad_argument(extras[0])

    scan_limit = 100
    if ns.scan_limit is not None:
        try:
            scan_limit = int(ns.scan_limit)
        except ValueError:
            print(f"Lỗi: --limit phải là số nguyên, nhận được: {ns.scan_limit}")
            sys.exit(1)

    run_deduplicate_messages(channel_name=ns.channel_name, scan_limit=scan_limit, dry_run=ns.dry_run)


def main(argv=None):
    """Chạy job tương ứng với tham số. argv mặc định là sys.argv[1:]."""
    if argv is None:
        argv = sys.argv[1:]
    configure_logging()

    if not argv:
        run_main_bot()
        return

    try:
        ns, extras = _build_mode_parser().parse_known_args(argv[:1])
    except _ArgumentError:
        ns, extras = None, argv[:1]
    if ns is None or ns.mode is None or extras:
        print(f"Unknown argument: {argv[0]}")
        print(USAGE)
        return

    if ns.mode == "dedup":
        _run_dedup(argv[1:])
    else:
        globals()[ns.mode]()

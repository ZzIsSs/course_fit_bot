"""CLI cho các tác vụ định kỳ: map tham số dòng lệnh sang jobs/.

main.py ở root chỉ gọi main() trong file này. GitHub Actions, Termux cron và
các widget trên điện thoại gọi `python main.py <flag>`, nên flag, message và
exit code phải giữ nguyên.
"""
import sys

from course_bot.core.logging_setup import configure_logging
from course_bot.jobs.notify import run_main_bot
from course_bot.jobs.reports import send_daily_summary, send_progress_report
from course_bot.jobs.announcements import check_announcements
from course_bot.jobs.sync_channels import sync_channels
from course_bot.jobs.sync_external import sync_notion, sync_google_calendar
from course_bot.jobs.dedup import run_deduplicate_messages
from course_bot.jobs.crawl_deadlines import crawl_deadlines_standalone


def main(argv=None):
    """Chạy job tương ứng với tham số. argv mặc định là sys.argv[1:]."""
    if argv is None:
        argv = sys.argv[1:]
    configure_logging()

    if len(argv) > 0:
        if argv[0] == "--summary":
            send_daily_summary()
        elif argv[0] == "--progress":
            send_progress_report()
        elif argv[0] == "--announcements":
            check_announcements()
        elif argv[0] == "--sync-channels":
            sync_channels()
        elif argv[0] == "--sync-notion":
            sync_notion()
        elif argv[0] in ("--sync-gcal", "--sync-google-calendar"):
            sync_google_calendar()
        elif argv[0] == "--crawl-deadlines":
            crawl_deadlines_standalone()
        elif argv[0] in ("--dedup", "--clean-duplicates"):
            channel_name = None
            scan_limit = 100
            dry_run = False

            i = 1
            while i < len(argv):
                arg = argv[i]
                if arg == "--dry-run":
                    dry_run = True
                    i += 1
                elif arg == "--channel" and i + 1 < len(argv):
                    channel_name = argv[i + 1]
                    i += 2
                elif arg == "--limit" and i + 1 < len(argv):
                    try:
                        scan_limit = int(argv[i + 1])
                    except ValueError:
                        print(f"Lỗi: --limit phải là số nguyên, nhận được: {argv[i + 1]}")
                        sys.exit(1)
                    i += 2
                else:
                    print(f"Tham số không xác định cho dedup: {arg}")
                    print("Usage: python main.py --dedup [--channel <name>] [--limit <N>] [--dry-run]")
                    sys.exit(1)

            run_deduplicate_messages(channel_name=channel_name, scan_limit=scan_limit, dry_run=dry_run)
        else:
            print(f"Unknown argument: {argv[0]}")
            print("Usage: python main.py [--summary | --progress | --announcements | --sync-channels | --sync-notion | --sync-gcal | --crawl-deadlines | --dedup]")
    else:
        run_main_bot()

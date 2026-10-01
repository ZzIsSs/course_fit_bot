import sys
from src.app import (
    run_main_bot, send_daily_summary, send_progress_report,
    check_announcements, sync_channels, sync_notion, sync_google_calendar,
    run_deduplicate_messages
)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--summary":
            send_daily_summary()
        elif sys.argv[1] == "--progress":
            send_progress_report()
        elif sys.argv[1] == "--announcements":
            check_announcements()
        elif sys.argv[1] == "--sync-channels":
            sync_channels()
        elif sys.argv[1] == "--sync-notion":
            sync_notion()
        elif sys.argv[1] in ("--sync-gcal", "--sync-google-calendar"):
            sync_google_calendar()
        elif sys.argv[1] in ("--dedup", "--clean-duplicates"):
            channel_name = None
            scan_limit = 100
            dry_run = False

            i = 2
            while i < len(sys.argv):
                arg = sys.argv[i]
                if arg == "--dry-run":
                    dry_run = True
                    i += 1
                elif arg == "--channel" and i + 1 < len(sys.argv):
                    channel_name = sys.argv[i + 1]
                    i += 2
                elif arg == "--limit" and i + 1 < len(sys.argv):
                    try:
                        scan_limit = int(sys.argv[i + 1])
                    except ValueError:
                        print(f"Lỗi: --limit phải là số nguyên, nhận được: {sys.argv[i + 1]}")
                        sys.exit(1)
                    i += 2
                else:
                    print(f"Tham số không xác định cho dedup: {arg}")
                    print("Usage: python main.py --dedup [--channel <name>] [--limit <N>] [--dry-run]")
                    sys.exit(1)

            run_deduplicate_messages(channel_name=channel_name, scan_limit=scan_limit, dry_run=dry_run)
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: python main.py [--summary | --progress | --announcements | --sync-channels | --sync-notion | --sync-gcal | --dedup]")
    else:
        run_main_bot()


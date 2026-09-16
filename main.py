import sys
from src.app import run_main_bot, send_daily_summary, send_progress_report, check_announcements, sync_channels, sync_notion

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
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: python main.py [--summary | --progress | --announcements | --sync-channels | --sync-notion]")
    else:
        run_main_bot()

import sys
from src.app import run_main_bot, send_daily_summary, send_progress_report

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--summary":
            send_daily_summary()
        elif sys.argv[1] == "--progress":
            send_progress_report()
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: python main.py [--summary | --progress]")
    else:
        run_main_bot()

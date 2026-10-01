"""Script dọn dẹp các tin nhắn bị gửi trùng lặp của Bot trên server Discord.

Sử dụng:
    # Quét thử nghiệm trên tất cả các kênh (không xóa thật)
    python scripts/clean_bot_messages.py --dry-run

    # Thực hiện dọn dẹp trên tất cả các kênh text (quét 100 tin gần nhất mỗi kênh)
    python scripts/clean_bot_messages.py

    # Quét 200 tin gần nhất trên một kênh cụ thể
    python scripts/clean_bot_messages.py --channel ctdl-gt --limit 200
"""
import sys
import os
import argparse

# Đảm bảo đường dẫn root project có trong sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Đảm bảo encoding utf-8 trên console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.app import run_deduplicate_messages


def main():
    parser = argparse.ArgumentParser(
        description="Dọn dẹp các tin nhắn trùng lặp do Bot gửi trên Discord (chỉ giữ lại 1 tin mới nhất)."
    )
    parser.add_argument(
        "--channel",
        type=str,
        default=None,
        help="Tên kênh Discord cần dọn dẹp (bỏ qua nếu muốn quét tất cả các kênh)."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Số lượng tin nhắn tối đa cần duyệt trên mỗi kênh (mặc định 100, tự động phân trang nếu > 100)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chế độ chạy thử nghiệm (kiểm tra thống kê số tin trùng, không xóa thật)."
    )

    args = parser.parse_args()

    run_deduplicate_messages(
        channel_name=args.channel,
        scan_limit=args.limit,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()

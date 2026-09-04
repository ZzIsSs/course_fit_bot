"""Đăng ký Slash Commands lên Discord.

Chạy 1 lần sau khi deploy: python scripts/register_commands.py

⚠️ Discord PUT ghi đè TOÀN BỘ danh sách lệnh — phải khai báo đầy đủ
tất cả lệnh trong COMMANDS, thiếu cái nào sẽ bị xoá mất cái đó.
"""
import os, sys, requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_env

env = load_env()
BOT_TOKEN = env['bot_token'] if env else os.environ.get('DISCORD_BOT_TOKEN')
APPLICATION_ID = os.environ.get('DISCORD_APPLICATION_ID')

COMMANDS = [
    {
        "name": "add_deadline",
        "description": "Thêm deadline nội bộ (không có trên Moodle)",
        "options": [
            {"name": "ten", "description": "Tên công việc", "type": 3, "required": True},
            {"name": "han_chot", "description": "dd/mm/yyyy HH:MM (bỏ giờ = mặc định 23:59)", "type": 3, "required": True},
            {"name": "mon", "description": "Mã môn (bỏ trống nếu đang chat trong kênh môn đó)", "type": 3, "required": False},
        ]
    },
    {
        "name": "deadline",
        "description": "Xem các deadline sắp tới",
        "options": [
            {"name": "mon", "description": "Mã môn (bỏ trống để tự nhận theo kênh, hoặc xem tất cả)", "type": 3, "required": False},
            {"name": "so_luong", "description": "Số lượng hiển thị (mặc định 5, tối đa 15)", "type": 4, "required": False, "min_value": 1, "max_value": 15},
        ]
    },
]

if not APPLICATION_ID or not BOT_TOKEN:
    print("❌ Thiếu DISCORD_APPLICATION_ID hoặc DISCORD_BOT_TOKEN.")
    print("   Set env hoặc kiểm tra file .env")
    sys.exit(1)

resp = requests.put(
    f"https://discord.com/api/v10/applications/{APPLICATION_ID}/commands",
    headers={"Authorization": f"Bot {BOT_TOKEN}"},
    json=COMMANDS
)

if resp.status_code == 200:
    print(f"[OK] Da dang ky {len(COMMANDS)} lenh thanh cong!")
    for cmd in resp.json():
        print(f"   /{cmd['name']} (ID: {cmd['id']})")
else:
    print(f"[ERROR] Loi {resp.status_code}: {resp.text}")

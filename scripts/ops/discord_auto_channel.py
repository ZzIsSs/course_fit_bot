"""
Script mẫu: Tự động tạo kênh Discord theo danh sách môn học.

Cài đặt trước khi chạy:
    pip install discord.py python-dotenv

Cần 3 biến môi trường (hoặc file .env):
    DISCORD_BOT_TOKEN   - token của bot
    DISCORD_GUILD_ID    - ID của server (guild)
    DISCORD_CATEGORY_ID - ID của category muốn xếp kênh vào (tuỳ chọn, để trống nếu không dùng)
"""

import os
import re
import unicodedata
import discord
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
GUILD_ID = int(os.environ["DISCORD_GUILD_ID"])
CATEGORY_ID = os.environ.get("DISCORD_CATEGORY_ID")
CATEGORY_ID = int(CATEGORY_ID) if CATEGORY_ID else None

# Danh sách môn học đầu vào — sau này sẽ lấy tự động từ file ICS hoặc course.fit.
# Tạm thời khai báo tay để test.
SUBJECTS = [
    "Toán Rời Rạc",
    "Cấu Trúc Dữ Liệu & Giải Thuật",
    "Nhập Môn Trí Tuệ Nhân Tạo",
]


def slugify_channel_name(name: str) -> str:
    """Chuyển tên môn học thành tên kênh hợp lệ cho Discord.

    Discord yêu cầu: chữ thường, không dấu, khoảng trắng -> '-', bỏ ký tự đặc biệt.
    Ví dụ: "Toán Rời Rạc" -> "toan-roi-rac"
    """
    # Bỏ dấu tiếng Việt
    normalized = unicodedata.normalize("NFD", name)
    no_accents = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    no_accents = no_accents.replace("đ", "d").replace("Đ", "D")

    # Chuyển thường, thay khoảng trắng/ký tự đặc biệt bằng '-'
    slug = no_accents.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


async def ensure_channels_exist(guild: discord.Guild, subjects: list[str]) -> None:
    """Kiểm tra và tạo kênh còn thiếu cho danh sách môn học."""
    existing_names = {ch.name for ch in guild.text_channels}
    category = guild.get_channel(CATEGORY_ID) if CATEGORY_ID else None

    for subject in subjects:
        channel_name = slugify_channel_name(subject)

        if channel_name in existing_names:
            print(f"[SKIP] Kênh '{channel_name}' đã tồn tại.")
            continue

        new_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            topic=f"Thông báo & deadline cho môn: {subject}",
        )
        print(f"[CREATED] Đã tạo kênh '{new_channel.name}' cho môn '{subject}'.")


class AutoChannelBot(discord.Client):
    async def on_ready(self):
        print(f"Bot đã đăng nhập với tên: {self.user}")

        guild = self.get_guild(GUILD_ID)
        if guild is None:
            print(f"[ERROR] Không tìm thấy server với ID {GUILD_ID}. "
                  f"Kiểm tra lại bot đã được mời vào server chưa.")
            await self.close()
            return

        await ensure_channels_exist(guild, SUBJECTS)

        # Chạy 1 lần rồi thoát (phù hợp với GitHub Actions chạy theo lịch).
        # Nếu muốn bot chạy liên tục để nhận lệnh, bỏ dòng dưới.
        await self.close()


def main():
    intents = discord.Intents.default()
    intents.guilds = True

    client = AutoChannelBot(intents=intents)
    client.run(BOT_TOKEN)


if __name__ == "__main__":
    main()

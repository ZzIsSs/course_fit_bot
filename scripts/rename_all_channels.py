import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_env
from src.moodle_api import get_site_info, get_enrolled_courses
from src.moodle_parser import extract_subject, extract_display_name, slugify_channel_name
from src.discord_api import get_guild_channels, rename_channel

# Tắt log quá dài, chỉ giữ lại INFO
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def main():
    print("="*50)
    print(" CÔNG CỤ TỰ ĐỘNG ĐỔI TÊN KÊNH DISCORD HÀNG LOẠT")
    print("="*50)
    
    env = load_env()
    if not env:
        print("❌ Lỗi: Không tải được biến môi trường.")
        return
        
    bot_token = env.get('bot_token')
    guild_id = env.get('guild_id')
    moodle_token = env.get('moodle_token')
    
    if not moodle_token or not bot_token or not guild_id:
        print("❌ Lỗi: Thiếu MOODLE_TOKEN, DISCORD_BOT_TOKEN hoặc DISCORD_SERVER_ID.")
        return

    # 1. Xác thực Moodle
    print("⏳ Đang tải danh sách môn học từ Moodle...")
    site_info = get_site_info(moodle_token)
    if not site_info or 'userid' not in site_info:
        print("❌ Token Moodle không hợp lệ.")
        return
        
    userid = site_info['userid']
    courses = get_enrolled_courses(moodle_token, userid)
    if not courses:
        print("❌ Không có khóa học nào trên Moodle.")
        return

    # 2. Lấy kênh Discord
    print("⏳ Đang tải danh sách kênh từ Discord...")
    discord_channels = get_guild_channels(bot_token, guild_id)
    if not discord_channels:
        print("❌ Không lấy được danh sách kênh Discord.")
        return
        
    channel_map = {c['name']: c['id'] for c in discord_channels if c.get('type') == 0}
    
    print("\n🚀 BẮT ĐẦU ĐỔI TÊN...")
    renamed_count = 0
    
    for course in courses:
        course_fullname = course.get('fullname', '')
        course_shortname = course.get('shortname', '')
        
        # Áp dụng logic chuẩn như trong bot
        display_name = extract_display_name(course_fullname)
        subject_code = extract_subject(course_shortname)
        if subject_code == "General" and display_name:
            subject_code = display_name
            
        new_chan_name = slugify_channel_name(subject_code, display_name)
        old_chan_name = slugify_channel_name(subject_code)
        
        # Kiểm tra nếu kênh cũ tồn tại và cần đổi tên
        if old_chan_name in channel_map and old_chan_name != new_chan_name:
            print(f"🔄 Đang đổi: #{old_chan_name} ➔ #{new_chan_name}")
            res = rename_channel(bot_token, channel_map[old_chan_name], new_chan_name)
            if res:
                renamed_count += 1
                channel_map[new_chan_name] = channel_map[old_chan_name]
                del channel_map[old_chan_name]
            else:
                print(f"⚠️ Lỗi khi đổi tên kênh #{old_chan_name}")

    print("\n" + "="*50)
    print(f"🎉 HOÀN TẤT! Đã đổi tên thành công {renamed_count} kênh.")
    print("="*50)

if __name__ == "__main__":
    main()

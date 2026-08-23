import sys
import os
import json

# Đảm bảo có thể import được thư mục src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.moodle_api import get_site_info, get_enrolled_courses, get_course_contents

def main():
    print("="*50)
    print(" CÔNG CỤ XEM DỮ LIỆU GỐC (RAW JSON) TỪ MOODLE")
    print("="*50)
    
    token = os.environ.get('MOODLE_TOKEN')
    if not token:
        token = input("\n🔑 Nhập Moodle Token của Nguyên: ").strip()

    if not token:
        print("❌ Chưa nhập token!")
        return

    print("\n⏳ Đang xác thực và tải dữ liệu...")
    site_info = get_site_info(token)
    
    if not site_info or 'userid' not in site_info:
        print("❌ Token không hợp lệ hoặc đã hết hạn!")
        return

    userid = site_info['userid']
    courses = get_enrolled_courses(token, userid)
    
    if not courses:
        print("❌ Không tìm thấy khóa học nào.")
        return

    print("\n" + "="*50)
    print("1. DỮ LIỆU TẤT CẢ KHÓA HỌC (COURSES)")
    print("="*50)
    print(json.dumps(courses, indent=4, ensure_ascii=False))

    print("\n" + "="*50)
    print("2. DỮ LIỆU TẤT CẢ NỘI DUNG CỦA TỪNG KHÓA HỌC (CONTENTS)")
    print("="*50)
    for course in courses:
        print(f"\n--- NỘI DUNG KHÓA HỌC: {course.get('fullname', course.get('shortname'))} ---")
        contents = get_course_contents(token, course['id'])
        if contents:
            print(json.dumps(contents, indent=4, ensure_ascii=False))
        else:
            print("Khóa học này chưa có nội dung nào.")

    print("\n" + "="*50)
    print("🎉 Hoàn tất hiển thị dữ liệu gốc!")

if __name__ == "__main__":
    main()

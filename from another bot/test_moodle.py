"""Script test nhanh Moodle API — Kiem tra token va xem danh sach khoa hoc/noi dung."""
import sys
import os
import io

# Fix encoding cho Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')

# Thêm project root vào path
sys.path.insert(0, os.path.dirname(__file__))

from src.moodle_api import (
    get_site_info, get_enrolled_courses, get_course_contents,
    get_course_forums, get_forum_discussions
)
from src.moodle_parser import extract_subject


def main():
    # Lấy token từ env hoặc hỏi người dùng
    token = os.environ.get('MOODLE_TOKEN')
    if not token:
        token = input("🔑 Nhập Moodle Token: ").strip()

    if not token:
        print("❌ Chưa nhập token!")
        return

    # === Test 1: Xác thực token ===
    print("\n" + "=" * 50)
    print("🔐 TEST 1: Xác thực token...")
    print("=" * 50)

    site_info = get_site_info(token)
    if not site_info or 'userid' not in site_info:
        print("❌ Token không hợp lệ hoặc đã hết hạn!")
        return

    print(f"✅ Xác thực thành công!")
    print(f"   👤 Tên: {site_info.get('fullname', 'N/A')}")
    print(f"   🆔 User ID: {site_info['userid']}")
    print(f"   🌐 Site: {site_info.get('sitename', 'N/A')}")

    userid = site_info['userid']

    # === Test 2: Danh sách khóa học ===
    print("\n" + "=" * 50)
    print("📚 TEST 2: Danh sách khóa học đang tham gia...")
    print("=" * 50)

    courses = get_enrolled_courses(token, userid)
    if not courses:
        print("❌ Không tìm thấy khóa học nào!")
        return

    print(f"✅ Tìm thấy {len(courses)} khóa học:\n")
    for i, course in enumerate(courses, 1):
        subject = extract_subject(course.get('shortname', ''))
        print(f"   {i}. [{subject}] {course.get('fullname', 'N/A')}")
        print(f"      ID: {course['id']} | Shortname: {course.get('shortname', 'N/A')}")

    # === Test 3: Nội dung khóa học đầu tiên ===
    test_course = courses[0]
    course_name = test_course.get('fullname', 'N/A')

    print("\n" + "=" * 50)
    print(f"📄 TEST 3: Nội dung khóa học '{course_name}'...")
    print("=" * 50)

    contents = get_course_contents(token, test_course['id'])
    if contents:
        module_count = 0
        for section in contents:
            modules = section.get('modules', [])
            if modules:
                print(f"\n   📁 Section: {section.get('name', 'N/A')}")
                for mod in modules:
                    modname = mod.get('modname', '')
                    if modname == 'label':
                        continue
                    module_count += 1
                    files = mod.get('contents', [])
                    file_names = [f.get('filename', '') for f in files if f.get('filename')]
                    file_text = f" — 📎 {', '.join(file_names[:3])}" if file_names else ""
                    print(f"      • [{modname}] {mod.get('name', 'N/A')}{file_text}")

        print(f"\n   📊 Tổng: {module_count} modules (không tính labels)")
    else:
        print("   ⚠️ Không lấy được nội dung.")

    # === Test 4: Diễn đàn ===
    print("\n" + "=" * 50)
    print(f"💬 TEST 4: Diễn đàn khóa học '{course_name}'...")
    print("=" * 50)

    forums = get_course_forums(token, test_course['id'])
    if forums:
        print(f"✅ Tìm thấy {len(forums)} diễn đàn:\n")
        for forum in forums:
            print(f"   💬 {forum.get('name', 'N/A')} (ID: {forum['id']})")

            discussions = get_forum_discussions(token, forum['id'], per_page=3)
            if discussions:
                print(f"      📝 {len(discussions)} bài đăng gần nhất:")
                for disc in discussions[:3]:
                    author = disc.get('userfullname', 'N/A')
                    subject = disc.get('subject', disc.get('name', 'N/A'))
                    print(f"         • {subject}")
                    print(f"           👤 {author}")
            else:
                print("      (Chưa có bài đăng)")
    else:
        print("   ⚠️ Không tìm thấy diễn đàn.")

    # === Tổng kết ===
    print("\n" + "=" * 50)
    print("🎉 TEST HOÀN TẤT!")
    print("=" * 50)
    print(f"✅ Token hoạt động tốt")
    print(f"✅ {len(courses)} khóa học đang được theo dõi")
    print(f"✅ Bot sẵn sàng gửi thông báo qua Discord")
    print(f"\n💡 Tiếp theo: Push code lên GitHub và chạy workflow!")


if __name__ == "__main__":
    main()

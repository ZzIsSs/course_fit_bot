import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_env
from src.database import get_db
from src.db_queries import set_course_discord_category, get_all_courses


def main():
    print("="*50)
    print(" GÁN CATEGORY DISCORD (KÌ HỌC) CHO MÔN HỌC")
    print("="*50)
    print("💡 Bật Developer Mode (Cài đặt > Nâng cao), chuột phải vào")
    print("   category (VD: 'kì 2') → Copy Category ID.\n")

    env = load_env()
    if not env:
        print("❌ Không tải được biến môi trường.")
        return

    with get_db(env['database_url']) as conn:
        courses = get_all_courses(conn)
        if not courses:
            print("❌ Chưa có môn nào trong DB. Chạy `python main.py --sync-channels` trước.")
            return

        print("📚 Các môn hiện có:")
        for c in courses:
            print(f"   - {c['course_name']} ({c.get('display_name') or 'chưa rõ tên'})")

        codes = [c.strip().upper() for c in
                 input("\n🔤 Nhập mã môn cần gán (cách nhau bởi dấu phẩy): ").split(',') if c.strip()]
        category_id = input("🔗 Nhập Category ID (kì học): ").strip()

        if not codes or not category_id.isdigit():
            print("❌ Thiếu mã môn hoặc Category ID không hợp lệ.")
            return

        for code in codes:
            set_course_discord_category(conn, code, category_id)
            print(f"   ✅ {code} → category {category_id}")

    print("\n🎉 Hoàn tất!")


if __name__ == "__main__":
    main()

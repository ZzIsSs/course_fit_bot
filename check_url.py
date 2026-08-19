import sys
import os

# Ensure src module is accessible
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.moodle_parser import fetch_and_parse_events

def main():
    print("="*50)
    print(" CÔNG CỤ KIỂM TRA MÔN HỌC ĐANG ĐƯỢC THEO DÕI BẰNG URL")
    print("="*50)
    url = input("\n🔗 Nhập đường link Moodle Calendar (.ics) của Nguyên: ").strip()
    
    if not url:
        print("❌ Chưa nhập URL!")
        return

    print(f"\n⏳ Đang tải và phân tích dữ liệu từ URL...")
    events = fetch_and_parse_events(url)
    
    if events is None:
        print("❌ Không thể tải hoặc phân tích URL này. Vui lòng kiểm tra lại URL.")
        return
        
    print(f"✅ Đã tải thành công {len(events)} deadline/sự kiện.")
    
    # Extract unique subjects
    subjects = set()
    for ev in events:
        if ev['subject'] and ev['subject'] != 'General':
            subjects.add(ev['subject'])
            
    if not subjects:
        print("\n📚 Không tìm thấy môn học nào riêng biệt trong URL này (hoặc chỉ có sự kiện chung).")
    else:
        print(f"\n📚 PHÁT HIỆN {len(subjects)} MÔN HỌC TRONG URL:")
        for idx, sub in enumerate(sorted(subjects), 1):
            print(f"   {idx}. {sub}")
    print("\n" + "="*50)

if __name__ == "__main__":
    main()

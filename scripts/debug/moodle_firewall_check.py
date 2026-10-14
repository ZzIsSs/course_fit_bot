import requests

def test_firewall():
    token = input("Nhập token Moodle của Nguyên (hoặc dán vào rồi nhấn Enter): ").strip()
    url = "https://courses.fit.hcmus.edu.vn/webservice/rest/server.php"
    params = {
        'wstoken': token,
        'wsfunction': 'core_webservice_get_site_info',
        'moodlewsrestformat': 'json'
    }

    print("\n" + "="*50)
    print("TEST 1: KHÔNG DÙNG NGỤY TRANG (Giống bot hiện tại)")
    print("="*50)
    try:
        res1 = requests.get(url, params=params, timeout=10)
        print(f"HTTP Status: {res1.status_code}")
        if res1.status_code == 200:
            data = res1.json()
            if 'exception' in data:
                print(f"Lỗi từ Moodle: {data['message']}")
            else:
                print("✅ Truy cập thành công! Tên của bạn là:", data.get('fullname'))
        else:
            print("❌ Bị chặn! Tường lửa phản hồi:", res1.text[:100])
    except Exception as e:
        print("❌ Lỗi mạng:", e)

    print("\n" + "="*50)
    print("TEST 2: CÓ DÙNG NGỤY TRANG (Hướng giải quyết đề xuất)")
    print("="*50)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 MoodleMobile'
    }
    try:
        res2 = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"HTTP Status: {res2.status_code}")
        if res2.status_code == 200:
            data = res2.json()
            if 'exception' in data:
                print(f"Lỗi từ Moodle: {data['message']}")
            else:
                print("✅ Truy cập thành công! Tên của bạn là:", data.get('fullname'))
        else:
            print("❌ Vẫn bị chặn! Tường lửa phản hồi:", res2.text[:100])
    except Exception as e:
        print("❌ Lỗi mạng:", e)

if __name__ == "__main__":
    test_firewall()

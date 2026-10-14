"""
Cấu hình chung cho pytest.

Biến môi trường giả được gán ĐÈ ngay khi conftest load, trước khi bất kỳ
module nào trong src/ được import (src/interactions.py đọc
DISCORD_PUBLIC_KEY lúc import). load_dotenv() mặc định không ghi đè biến
đã tồn tại, nên test không bao giờ nạp được DB/token thật từ .env.
Biến của tích hợp tuỳ chọn (Notion, Google) gán chuỗi rỗng để luôn tắt.

Script debug cần token thật nằm ở scripts/debug/, ngoài testpaths.
"""
import os

FAKE_ENV = {
    # Port 1 trên localhost: kết nối bị từ chối ngay, không bao giờ chạm production
    "DATABASE_URL": "postgresql://fake:fake@127.0.0.1:1/fake",
    "DISCORD_BOT_TOKEN": "fake-bot-token",
    "DISCORD_SERVER_ID": "000000000000000000",
    "DISCORD_APPLICATION_ID": "000000000000000000",
    "DISCORD_PUBLIC_KEY": "0" * 64,
    "MOODLE_CALENDAR_URL": "http://127.0.0.1:1/calendar.ics",
    "MOODLE_TOKEN": "fake-moodle-token",
    "EXTERNAL_API_KEY": "fake-external-api-key",
    "NOTION_API_TOKEN": "",
    "NOTION_DATABASE_ID": "",
    "GOOGLE_SERVICE_ACCOUNT_JSON": "",
    "GOOGLE_SERVICE_ACCOUNT_FILE": "",
    "GOOGLE_CALENDAR_ID": "",
}
os.environ.update(FAKE_ENV)

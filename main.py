import os
import json
import logging
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    username = os.environ.get('COURSE_FIT_USERNAME')
    password = os.environ.get('COURSE_FIT_PASSWORD')
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')

    if not all([username, password, webhook_url]):
        logging.error("Missing environment variables. Please check COURSE_FIT_USERNAME, COURSE_FIT_PASSWORD, and DISCORD_WEBHOOK_URL.")
        return

    # 1. Login to Moodle
    session = requests.Session()
    login_url = 'https://courses.fit.hcmus.edu.vn/login/index.php'
    
    try:
        logging.info("Fetching login page to get logintoken...")
        response = session.get(login_url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        logintoken_input = soup.find('input', {'name': 'logintoken'})
        
        if not logintoken_input:
            send_error_to_discord(webhook_url, "Không tìm thấy `logintoken` trên trang đăng nhập. Cấu trúc trang có thể đã thay đổi!")
            return
            
        logintoken = logintoken_input.get('value')
        
        login_data = {
            'username': username,
            'password': password,
            'logintoken': logintoken
        }
        
        logging.info("Attempting login...")
        response = session.post(login_url, data=login_data, timeout=15)
        
        # Check if login is successful
        if 'loginerrormessage' in response.text or 'Invalid login' in response.text:
            send_error_to_discord(webhook_url, "Đăng nhập thất bại. Vui lòng kiểm tra lại Username/Password trong GitHub Secrets.")
            return
            
        logging.info("Login successful.")

        # 2. Fetch upcoming events from calendar
        calendar_url = 'https://courses.fit.hcmus.edu.vn/calendar/view.php?view=upcoming'
        logging.info(f"Fetching calendar: {calendar_url}")
        
        response = session.get(calendar_url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        events = soup.find_all(attrs={"data-region": "event-item"})
        
        if not events:
            # Maybe there are no events, or maybe structure changed. We just log it.
            logging.info("No upcoming events found on the page.")
            
    except Exception as e:
        logging.error(f"Error during scraping: {e}")
        send_error_to_discord(webhook_url, f"Lỗi không xác định khi chạy script: {e}")
        return
        
    # 3. Process events and load state
    state_file = 'state.json'
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
    else:
        state = {"notified_items": []}
        
    new_items_found = False
    
    for event in events:
        a_tag = event.find('a', attrs={"data-action": "view-event"})
        if not a_tag:
            continue
            
        event_id = a_tag.get('data-event-id')
        event_url = a_tag.get('href')
        event_name_span = a_tag.find('span', class_='eventname')
        event_name = event_name_span.text.strip() if event_name_span else a_tag.get('title')
        
        if event_id not in state["notified_items"]:
            # Found a new item!
            logging.info(f"New event found: {event_name}")
            send_notification_to_discord(webhook_url, event_name, event_url)
            state["notified_items"].append(event_id)
            new_items_found = True
            
    if new_items_found:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)
        logging.info("State file updated.")
    else:
        logging.info("No new events to notify.")

def send_notification_to_discord(webhook_url, event_name, event_url):
    message = f"🚨 **THÔNG BÁO MỚI (course.fit)**\n\n📌 **Nội dung:** {event_name}\n🔗 **Link:** {event_url}"
    payload = {"content": message}
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Failed to send discord notification: {e}")

def send_error_to_discord(webhook_url, error_message):
    message = f"⚠️ **Lỗi Script course.fit:**\n{error_message}"
    payload = {"content": message}
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Failed to send discord error notification: {e}")

if __name__ == "__main__":
    main()

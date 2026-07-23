import os
import json
import logging
import requests
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    calendar_url = os.environ.get('MOODLE_CALENDAR_URL')
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')

    if not all([calendar_url, webhook_url]):
        logging.error("Missing environment variables. Please check MOODLE_CALENDAR_URL and DISCORD_WEBHOOK_URL.")
        return

    # 1. Fetch Calendar ICS
    try:
        logging.info("Fetching calendar ICS file...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(calendar_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            send_error_to_discord(webhook_url, f"Không thể tải lịch. HTTP Status: {response.status_code}")
            return
            
        ics_data = response.text
        logging.info("Successfully fetched ICS data.")
        
    except Exception as e:
        logging.error(f"Error fetching calendar: {e}")
        send_error_to_discord(webhook_url, f"Lỗi không tải được lịch: {e}")
        return
        
    # 2. Parse ICS manually with Regex
    events = []
    
    # Extract blocks of BEGIN:VEVENT ... END:VEVENT
    vevent_blocks = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', ics_data, re.DOTALL)
    
    for block in vevent_blocks:
        # Extract UID
        uid_match = re.search(r'\nUID:(.*?)\n', block)
        # Extract SUMMARY
        summary_match = re.search(r'\nSUMMARY:(.*?)\n', block)
        # Extract DESCRIPTION (optional, but good for details if we want)
        
        if uid_match and summary_match:
            uid = uid_match.group(1).strip()
            summary = summary_match.group(1).strip()
            events.append({"uid": uid, "summary": summary})
            
    logging.info(f"Found {len(events)} events in calendar.")

    # 3. Process events and load state
    state_file = 'state.json'
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
    else:
        state = {"notified_items": []}
        
    new_items_found = False
    
    for event in events:
        event_id = event["uid"]
        event_name = event["summary"]
        
        # Moodle includes "is due" at the end of assignments, we can keep it as is.
        
        if event_id not in state["notified_items"]:
            # Found a new item!
            logging.info(f"New event found: {event_name}")
            send_notification_to_discord(webhook_url, event_name, event_id)
            state["notified_items"].append(event_id)
            new_items_found = True
            
    if new_items_found:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)
        logging.info("State file updated.")
    else:
        logging.info("No new events to notify.")

def send_notification_to_discord(webhook_url, event_name, event_id):
    # Try to extract the ID number from UID to build a link if possible
    # e.g., UID:57754@courses.fit.hcmus.edu.vn -> 57754
    event_url = "https://courses.fit.hcmus.edu.vn/calendar/view.php?view=upcoming"
    id_match = re.search(r'^(\d+)@', event_id)
    if id_match:
        event_url = f"https://courses.fit.hcmus.edu.vn/calendar/view.php?view=day&course=1&time=upcoming#event_{id_match.group(1)}"
        
    message = f"@everyone 🚨 **THÔNG BÁO MỚI (course.fit)**\n\n📌 **Nội dung:** {event_name}\n🔗 **Xem trên lịch:** {event_url}"
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

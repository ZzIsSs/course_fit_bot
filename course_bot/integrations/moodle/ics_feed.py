import logging
import re
import requests
from datetime import datetime, timezone

from course_bot.domain.course_naming import extract_subject

# ==================== PARSE ICS ====================

def fetch_and_parse_events(calendar_url):
    """Fetch ICS and parse events. Returns list of event dicts or None on failure."""
    try:
        logging.info("Fetching calendar ICS file...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(calendar_url, headers=headers, timeout=15)

        if response.status_code != 200:
            logging.error(f"Failed to load calendar. HTTP Status: {response.status_code}")
            return None

        ics_data = response.text
    except Exception as e:
        logging.error(f"Error fetching calendar: {e}")
        return None

    events = []
    vevent_blocks = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', ics_data, re.DOTALL)

    for block in vevent_blocks:
        uid_match = re.search(r'\nUID:(.*?)\n', block)
        summary_match = re.search(r'\nSUMMARY:(.*?)\n', block)
        dtend_match = re.search(r'\nDTEND:(.*?)\n', block)
        cat_match = re.search(r'\nCATEGORIES:(.*?)\n', block)

        if uid_match and summary_match and dtend_match:
            uid = uid_match.group(1).strip()
            summary = summary_match.group(1).strip()
            dtend_str = dtend_match.group(1).strip()
            category = cat_match.group(1).strip() if cat_match else "General"

            subject = extract_subject(category)

            try:
                dtend = datetime.strptime(dtend_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                events.append({
                    "uid": uid,
                    "summary": summary,
                    "deadline": dtend,
                    "subject": subject,
                    "category_raw": category,
                })
            except Exception as e:
                logging.error(f"Error parsing date {dtend_str}: {e}")

    logging.info(f"Found {len(events)} events in calendar.")
    return events

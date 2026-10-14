import os
import sys
import re
import csv
import json
import argparse
from datetime import datetime, timezone, timedelta
import urllib.request
import urllib.error

# Tránh lỗi encoding khi in tiếng Việt trên console Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))


def parse_ics_file(ics_path):
    """Đọc file .ics và trích xuất danh sách sự kiện/deadline."""
    with open(ics_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Xử lý line unfolding của chuẩn iCalendar
    content = re.sub(r'\r?\n[ \t]', '', content)

    events = []
    blocks = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', content, re.DOTALL)

    for block in blocks:
        summary_m = re.search(r'SUMMARY:(.*?)(?:\r?\n|$)', block)
        dtend_m = re.search(r'DTEND:(.*?)(?:\r?\n|$)', block)
        dtstart_m = re.search(r'DTSTART:(.*?)(?:\r?\n|$)', block)
        cat_m = re.search(r'CATEGORIES:(.*?)(?:\r?\n|$)', block)

        summary = summary_m.group(1).strip() if summary_m else "Chưa đặt tên"
        # Bỏ 'is due' ở cuối nếu có
        summary = re.sub(r'\s+is due$', '', summary, flags=re.IGNORECASE)
        summary = summary.replace('\\,', ',').replace('\\;', ';')

        raw_date = (dtend_m or dtstart_m)
        deadline_str = ""
        if raw_date:
            raw_val = raw_date.group(1).strip()
            try:
                dt = datetime.strptime(raw_val, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                local_dt = dt.astimezone(VN_TZ)
                deadline_str = local_dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                deadline_str = raw_val

        # Bóc tách môn học theo chuẩn FIT
        subject = "Chung"
        if cat_m:
            raw_cat = cat_m.group(1).strip()
            # Ưu tiên mã môn FIT dạng _CSC10014_ hoặc mã môn đứng riêng
            m = re.search(r'_([A-Z]{2,5}\d{4,6})_', raw_cat)
            if m:
                subject = m.group(1)
            else:
                matches = re.finditer(r'\b([A-Z]{2,5}\d{4,6})\b', raw_cat)
                found = False
                for match in matches:
                    code = match.group(1)
                    if not code.startswith(('CQ', 'CLC', 'VP', 'CTTT')):
                        subject = code
                        found = True
                        break
                if not found:
                    subject = re.sub(r'\s*-\s*(CQ|CLC|VP|CTTT)\d{4}.*$', '', raw_cat).strip()

        events.append({
            "Task": summary,
            "Deadline": deadline_str,
            "Môn học": subject,
            "Status": "Not started"
        })

    return events


def export_to_csv(events, output_csv):
    """Xuất danh sách events ra file CSV tương thích 100% với Notion Import."""
    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Task", "Deadline", "Môn học", "Status"])
        writer.writeheader()
        for ev in events:
            writer.writerow(ev)
    print(f"✅ Đã tạo file CSV thành công: {output_csv} ({len(events)} công việc)")


def _http_request(url, method="GET", headers=None, data=None):
    """Gửi HTTP request dùng thư viện chuẩn urllib (không cần cài thêm requests)."""
    req_headers = headers or {}
    encoded_data = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=encoded_data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        return e.code, json.loads(err_body) if err_body else {"error": str(e)}
    except Exception as e:
        return 500, {"error": str(e)}


def clear_notion_database(token, database_id):
    """Xóa (archive) toàn bộ các dòng hiện có trong Notion database."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    has_more = True
    next_cursor = None
    deleted_count = 0

    print("⏳ Đang tìm các dòng dữ liệu để xóa...")
    while has_more:
        body = {}
        if next_cursor:
            body["start_cursor"] = next_cursor
        status, data = _http_request(url, method="POST", headers=headers, data=body)
        if status != 200:
            print(f"❌ Lỗi truy vấn Database: {data}")
            return
        results = data.get("results", [])
        for page in results:
            page_id = page["id"]
            patch_url = f"https://api.notion.com/v1/pages/{page_id}"
            del_status, _ = _http_request(patch_url, method="PATCH", headers=headers, data={"archived": True})
            if del_status == 200:
                deleted_count += 1

        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")

    print(f"🗑️ Đã xóa thành công {deleted_count} dòng trong Notion database!")


def import_to_notion_database(token, database_id, events):
    """Đẩy danh sách events vào Notion database qua Notion API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    url = "https://api.notion.com/v1/pages"
    success_count = 0

    print(f"⏳ Đang thêm {len(events)} task vào Notion...")
    for ev in events:
        props = {
            "Task": {
                "title": [{"text": {"content": ev["Task"]}}]
            }
        }
        if ev.get("Môn học"):
            props["Môn học"] = {
                "select": {"name": ev["Môn học"]}
            }
        if ev.get("Status"):
            props["Status"] = {
                "status": {"name": ev["Status"]}
            }
        if ev.get("Deadline"):
            try:
                dt = datetime.strptime(ev["Deadline"], "%Y-%m-%d %H:%M")
                iso_str = dt.strftime("%Y-%m-%dT%H:%M:00+07:00")
                props["Deadline"] = {
                    "date": {"start": iso_str}
                }
            except Exception:
                pass

        payload = {
            "parent": {"database_id": database_id},
            "properties": props
        }
        status, res = _http_request(url, method="POST", headers=headers, data=payload)
        if status in (200, 201):
            success_count += 1
        else:
            print(f"⚠️ Lỗi thêm task '{ev['Task']}': {res}")

    print(f"🎉 Hoàn tất! Đã thêm {success_count}/{len(events)} task vào Notion Database.")


def main():
    parser = argparse.ArgumentParser(description="Công cụ Notion: Chuyển đổi file lịch, Import và Xoá dữ liệu")
    subparsers = parser.add_subparsers(dest="command")

    p_csv = subparsers.add_parser("ics-to-csv", help="Chuyển file .ics (Moodle) thành CSV để import vào Notion")
    p_csv.add_argument("--ics", default="data/calendar.ics", help="Đường dẫn file .ics")
    p_csv.add_argument("--out", default="data/notion_import_sample.csv", help="Đường dẫn file CSV xuất ra")

    p_clear = subparsers.add_parser("clear-notion", help="Xoá sạch toàn bộ dữ liệu trong Database Notion")
    p_clear.add_argument("--token", required=True, help="Notion Integration Secret (secret_...)")
    p_clear.add_argument("--db-id", required=True, help="Notion Database ID (lấy từ link database)")

    p_imp = subparsers.add_parser("import-notion", help="Nhập file .ics thẳng vào Database Notion qua API")
    p_imp.add_argument("--ics", default="data/calendar.ics", help="Đường dẫn file .ics")
    p_imp.add_argument("--token", required=True, help="Notion Integration Secret (secret_...)")
    p_imp.add_argument("--db-id", required=True, help="Notion Database ID")

    args = parser.parse_args()

    if args.command == "ics-to-csv":
        events = parse_ics_file(args.ics)
        export_to_csv(events, args.out)
    elif args.command == "clear-notion":
        clear_notion_database(args.token, args.db_id)
    elif args.command == "import-notion":
        events = parse_ics_file(args.ics)
        import_to_notion_database(args.token, args.db_id, events)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

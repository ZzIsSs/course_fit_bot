"""Google Calendar sync module.

Đồng bộ deadline từ Moodle và Discord lên Google Calendar để theo dõi trực quan trên điện thoại.
Sử dụng Google Calendar API v3 qua Google Service Account.

Tính năng nổi bật:
- Hiển thị trực quan trên điện thoại: mốc kết thúc đúng hạn chót (UTC+7).
- Thông báo đẩy (Pop-up/Push Notifications): trước 1 ngày (24h), trước 3 giờ, và trước 30 phút.
- Chống trùng lặp & cập nhật: dùng extendedProperties.private['lms_id'].
- Đồng bộ hoàn thành: khi thả reaction ✅ trên Discord, tự đổi màu xanh lá và đổi tiêu đề '✅ [XONG]'.
- Bọc an toàn 100%: lỗi Google Calendar API không bao giờ làm crash luồng chính của bot.
"""
import base64
import json
import logging
from datetime import datetime, timezone, timedelta

# Timezone Việt Nam (UTC+7)
LOCAL_TZ = timezone(timedelta(hours=7))
TIMEZONE_NAME = "Asia/Ho_Chi_Minh"
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _parse_credentials(sa_json=None, sa_file=None):
    """Phân tích và khởi tạo Google Credentials từ JSON string, Base64 string hoặc File path."""
    from google.oauth2 import service_account

    if sa_file:
        return service_account.Credentials.from_service_account_file(
            sa_file, scopes=SCOPES
        )

    if not sa_json:
        return None

    sa_json_str = sa_json.strip()
    # Nếu là chuỗi base64 (không bắt đầu bằng '{')
    if not sa_json_str.startswith("{"):
        try:
            decoded = base64.b64decode(sa_json_str).decode("utf-8")
            info = json.loads(decoded)
            return service_account.Credentials.from_service_account_info(
                info, scopes=SCOPES
            )
        except Exception as e:
            logging.warning(f"Google Calendar: Không thể giải mã Base64 JSON: {e}")

    # Nếu là chuỗi JSON trực tiếp
    try:
        info = json.loads(sa_json_str)
        return service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES
        )
    except Exception as e:
        logging.warning(f"Google Calendar: Không thể parse JSON Service Account: {e}")
        return None


class GoogleCalendarSync:
    """Quản lý đồng bộ deadline với Google Calendar qua Service Account."""

    def __init__(self, sa_json=None, sa_file=None, calendar_id="primary"):
        self.calendar_id = calendar_id
        self.service = None

        try:
            from googleapiclient.discovery import build

            creds = _parse_credentials(sa_json=sa_json, sa_file=sa_file)
            if creds:
                self.service = build("calendar", "v3", credentials=creds, cache_discovery=False)
                masked_id = self._mask_calendar_id(self.calendar_id)
                logging.info(f"Google Calendar: Khởi tạo thành công cho Calendar ({masked_id}).")
            else:
                logging.warning("Google Calendar: Không thể khởi tạo Credentials.")
        except Exception as e:
            logging.warning(f"Google Calendar: Lỗi khi khởi tạo Google Calendar Service: {e}")

    @staticmethod
    def _mask_calendar_id(cal_id):
        """Che bớt Calendar ID để bảo vệ quyền riêng tư trong log."""
        if not cal_id:
            return "***"
        if "@" in cal_id:
            user_part, domain_part = cal_id.split("@", 1)
            prefix = user_part[:3] + "***" if len(user_part) > 3 else "***"
            return f"{prefix}@{domain_part}"
        if len(cal_id) > 8:
            return f"{cal_id[:3]}***{cal_id[-3:]}"
        return "***"

    def is_available(self):
        """Kiểm tra service đã sẵn sàng hoạt động hay chưa."""
        return self.service is not None


    # ==================== TÌM KIẾM EVENT ====================

    def find_event_by_lms_id(self, lms_id):
        """Tìm sự kiện trên Google Calendar theo lms_id lưu trong extendedProperties."""
        if not self.is_available():
            return None

        try:
            # Tìm kiếm theo private extended property lms_id
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                privateExtendedProperty=f"lms_id={lms_id}",
                maxResults=1,
                singleEvents=True
            ).execute()

            items = events_result.get("items", [])
            if items:
                return items[0]
            return None
        except Exception as e:
            logging.debug(f"Google Calendar: Lỗi khi tìm event theo lms_id '{lms_id}': {e}")
            return None

    # ==================== THÊM / CẬP NHẬT EVENT ====================

    def add_deadline(self, task_name, course_name, deadline_dt, url="", lms_id="", source="Moodle"):
        """Thêm một deadline mới vào Google Calendar.

        Nếu đã tồn tại thì kiểm tra cập nhật (thời hạn/mô tả).
        """
        if not self.is_available():
            return None

        try:
            # Chuẩn hóa thời gian sang múi giờ VN (UTC+7)
            # Dữ liệu hạn chót lưu trong database luôn theo chuẩn UTC.
            # Nếu datetime không có tzinfo (naive từ DB), phải gán tzinfo=UTC trước khi chuyển sang LOCAL_TZ.
            if deadline_dt.tzinfo is None:
                deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)

            end_time = deadline_dt.astimezone(LOCAL_TZ)

            # Đặt thời lượng sự kiện mặc định là 30 phút kết thúc tại hạn chót
            start_time = end_time - timedelta(minutes=30)

            # Format ISO 8601
            start_iso = start_time.isoformat()
            end_iso = end_time.isoformat()
            formatted_dl_str = end_time.strftime("%H:%M ngày %d/%m/%Y")

            existing_event = self.find_event_by_lms_id(lms_id)
            if existing_event:
                event_id = existing_event["id"]
                current_end = existing_event.get("end", {}).get("dateTime")

                # Nếu hạn nộp thay đổi thì cập nhật
                if current_end != end_iso:
                    patch_body = {
                        "start": {"dateTime": start_iso, "timeZone": TIMEZONE_NAME},
                        "end": {"dateTime": end_iso, "timeZone": TIMEZONE_NAME},
                        "description": self._build_description(
                            course_name, formatted_dl_str, url, source, lms_id, completed=False
                        ),
                    }
                    self.service.events().patch(
                        calendarId=self.calendar_id, eventId=event_id, body=patch_body
                    ).execute()
                    logging.info(f"🔄 Google Calendar: Đã cập nhật hạn chót cho '{task_name}' ({formatted_dl_str})")
                else:
                    logging.debug(f"Google Calendar: Sự kiện '{task_name}' ({lms_id}) đã tồn tại — bỏ qua.")
                return event_id

            # Tạo mới sự kiện
            summary = f"[{course_name}] {task_name}"
            description = self._build_description(
                course_name, formatted_dl_str, url, source, lms_id, completed=False
            )

            event_body = {
                "summary": summary[:250],
                "description": description,
                "start": {"dateTime": start_iso, "timeZone": TIMEZONE_NAME},
                "end": {"dateTime": end_iso, "timeZone": TIMEZONE_NAME},
                # Cài đặt thông báo đẩy về điện thoại
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 1440},  # Trước 1 ngày (24 giờ)
                        {"method": "popup", "minutes": 180},   # Trước 3 giờ
                        {"method": "popup", "minutes": 30},    # Trước 30 phút
                    ],
                },
                "extendedProperties": {
                    "private": {
                        "lms_id": str(lms_id),
                        "course_name": str(course_name),
                        "source": str(source),
                        "status": "pending",
                    }
                },
            }

            created_event = self.service.events().insert(
                calendarId=self.calendar_id, body=event_body
            ).execute()

            logging.info(f"✅ Google Calendar: Đã thêm '{summary}' (Hạn: {formatted_dl_str})")
            return created_event.get("id")

        except Exception as e:
            logging.warning(f"Google Calendar: Lỗi ngoại lệ khi thêm deadline '{task_name}': {e}")
            return None

    # ==================== ĐÁNH DẤU HOÀN THÀNH ====================

    def mark_completed(self, lms_id, completed_by=None, task_name=None):
        """Đánh dấu hoàn thành trên Google Calendar:

        - Đổi tiêu đề: '✅ [XONG] ...'
        - Đổi màu sang Xanh lá ('10' - Basil)
        - Cập nhật ghi chú trạng thái hoàn thành
        """
        if not self.is_available():
            return False

        try:
            event = self.find_event_by_lms_id(lms_id)
            if not event:
                logging.debug(f"Google Calendar: Không tìm thấy event để đánh dấu hoàn thành ({lms_id})")
                return False

            event_id = event["id"]
            current_summary = event.get("summary", "")

            # Tránh lặp prefix '✅ [XONG]' nếu đã có
            clean_summary = current_summary
            for pfx in ["✅ [XONG] ", "✅ [DONE] ", "[DONE] "]:
                if clean_summary.startswith(pfx):
                    clean_summary = clean_summary[len(pfx):]

            new_summary = f"✅ [XONG] {clean_summary}"

            # Cập nhật description
            now_vn = datetime.now(LOCAL_TZ).strftime("%H:%M ngày %d/%m/%Y")
            done_text = f"\n\n---\n✅ Trạng thái: ĐÃ HOÀN THÀNH\n👤 Người thực hiện: {completed_by or 'Unknown'}\n⏱ Lúc: {now_vn}"
            old_desc = event.get("description", "")
            # Xóa ghi chú hoàn thành cũ nếu có
            if "---\n✅ Trạng thái: ĐÃ HOÀN THÀNH" in old_desc:
                old_desc = old_desc.split("---\n✅ Trạng thái: ĐÃ HOÀN THÀNH")[0].strip()
            new_desc = old_desc + done_text

            patch_body = {
                "summary": new_summary[:250],
                "colorId": "10",  # Màu Xanh lá cây (Basil) trên Google Calendar
                "description": new_desc,
                "extendedProperties": {
                    "private": {
                        "status": "completed",
                        "completed_by": str(completed_by or "Unknown"),
                        "completed_at": now_vn,
                    }
                },
            }

            self.service.events().patch(
                calendarId=self.calendar_id, eventId=event_id, body=patch_body
            ).execute()

            logging.info(f"✅ Google Calendar: Đã đánh dấu hoàn thành '{new_summary}' (bởi {completed_by})")
            return True

        except Exception as e:
            logging.warning(f"Google Calendar: Lỗi ngoại lệ khi đánh dấu hoàn thành ({lms_id}): {e}")
            return False

    # ==================== ĐỒNG BỘ HÀNG LOẠT ====================

    def sync_all_deadlines(self, all_deadlines):
        """Đồng bộ toàn bộ danh sách deadline từ Database lên Google Calendar.

        Dùng cho lệnh CLI hoặc lần chạy đầu tiên.
        Returns:
            dict: {'added': count, 'updated': count, 'skipped': count, 'failed': count}
        """
        stats = {"added": 0, "updated": 0, "skipped": 0, "failed": 0}
        if not self.is_available():
            logging.warning("Google Calendar: Service chưa được khởi tạo, không thể đồng bộ.")
            return stats

        for dl in all_deadlines:
            task_name = dl.get("deadline_name", "Không có tên")
            course_name = dl.get("course_name", "Chung")
            due_time = dl.get("due_time")
            lms_id = dl.get("lms_deadlines_id")
            source_url = dl.get("source_url", "")
            completed = dl.get("completed", False)
            completed_by = dl.get("completed_by")

            if not due_time or not lms_id:
                stats["skipped"] += 1
                continue

            source = "Discord" if str(lms_id).startswith("manual-") else "Moodle"

            try:
                existing = self.find_event_by_lms_id(lms_id)
                res_id = self.add_deadline(
                    task_name=task_name,
                    course_name=course_name,
                    deadline_dt=due_time,
                    url=source_url,
                    lms_id=lms_id,
                    source=source,
                )

                if not res_id:
                    stats["failed"] += 1
                    continue

                if existing:
                    stats["skipped"] += 1
                else:
                    stats["added"] += 1

                # Nếu trong DB đã hoàn thành nhưng trên lịch chưa cập nhật
                if completed:
                    self.mark_completed(lms_id=lms_id, completed_by=completed_by, task_name=task_name)

            except Exception as e:
                logging.warning(f"Google Calendar: Lỗi khi đồng bộ deadline '{task_name}': {e}")
                stats["failed"] += 1

        return stats

    # ==================== HELPER ====================

    def _build_description(self, course_name, deadline_str, url, source, lms_id, completed=False):
        """Xây dựng nội dung chi tiết cho sự kiện."""
        desc = (
            f"📚 Môn học: {course_name}\n"
            f"⏰ Hạn chót: {deadline_str}\n"
            f"📌 Nguồn: {source}\n"
            f"🔗 Link bài tập: {url if url else 'Không có'}\n"
            f"🆔 LMS ID: {lms_id}\n"
            f"⏳ Trạng thái: {'Đã hoàn thành' if completed else 'Đang chờ hoàn thành'}\n\n"
            f"💡 Mẹo: Bạn có thể react ✅ trên tin nhắn Discord để tự động đổi trạng thái sang Hoàn thành!"
        )
        return desc

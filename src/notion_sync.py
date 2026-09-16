"""Notion Todo List sync module.

Đồng bộ deadline từ Moodle/Discord lên Notion Database dưới dạng Todo List.
Sử dụng trực tiếp Notion REST API qua thư viện requests.

Tính năng tự động & thích ứng:
- Tự động quét cấu trúc bảng Notion: tự nhận diện tên cột Title (dù là "Name" hay "Tên deadline").
- Tự động nhận diện có hay không có cột "LMS ID":
  + Nếu có: Dùng "LMS ID" để chống trùng lặp.
  + Nếu chưa có: Tự động dùng "Tên deadline" để chống trùng lặp, KHÔNG BAO GIỜ báo lỗi thiếu cột.
- Tự động nhận diện kiểu cột Trạng thái (status hay select).
- Bọc an toàn 100%: Lỗi Notion không bao giờ làm crash luồng chính của bot.
"""
import logging
import requests
from datetime import datetime, timezone, timedelta

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# Timezone Việt Nam (UTC+7)
LOCAL_TZ = timezone(timedelta(hours=7))


class NotionSync:
    """Quản lý đồng bộ deadline với Notion Database tự thích ứng schema."""

    def __init__(self, token, database_id):
        self.token = token
        self.database_id = database_id
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }
        self.title_prop = "Tên deadline"
        self.status_prop = "Trạng thái"
        self.status_type = "status"  # hoặc "select"
        self.date_prop = "Hạn chót"
        self.url_prop = "Link Moodle"
        self.course_prop = "Môn học"
        self.source_prop = "Nguồn"
        self.lms_id_prop = None  # Sẽ tự phát hiện nếu có cột 'LMS ID'

        # Tự động đọc schema bảng Notion
        self._inspect_schema()

    def _inspect_schema(self):
        """Tự động kiểm tra các cột thực tế trên Notion Database."""
        url = f"{NOTION_API_BASE}/databases/{self.database_id}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                logging.warning(f"Notion: Không thể đọc schema database ({resp.status_code}): {resp.text[:200]}")
                return

            db_data = resp.json()
            props = db_data.get("properties", {})

            # 1. Tìm cột Title
            for name, meta in props.items():
                if meta.get("type") == "title":
                    self.title_prop = name
                    break

            # 2. Tìm cột LMS ID (nếu có)
            for name, meta in props.items():
                if name.lower().replace(" ", "").replace("_", "") == "lmsid" and meta.get("type") == "rich_text":
                    self.lms_id_prop = name
                    break

            # 3. Tìm cột Trạng thái
            for name, meta in props.items():
                norm = name.lower()
                if norm in ("trạng thái", "status") and meta.get("type") in ("status", "select"):
                    self.status_prop = name
                    self.status_type = meta.get("type")
                    break

            # 4. Tìm cột Hạn chót
            for name, meta in props.items():
                norm = name.lower()
                if (norm in ("hạn chót", "deadline", "date") or meta.get("type") == "date"):
                    self.date_prop = name
                    break

            # 5. Tìm cột Link Moodle
            for name, meta in props.items():
                norm = name.lower()
                if (norm in ("link moodle", "url", "link") or meta.get("type") == "url"):
                    self.url_prop = name
                    break

            # 6. Tìm cột Môn học
            for name, meta in props.items():
                norm = name.lower()
                if norm in ("môn học", "môn", "course") and meta.get("type") == "select":
                    self.course_prop = name
                    break

            # 7. Tìm cột Nguồn
            for name, meta in props.items():
                norm = name.lower()
                if norm in ("nguồn", "source") and meta.get("type") == "select":
                    self.source_prop = name
                    break

            logging.info(
                f"Notion schema: Title='{self.title_prop}', Status='{self.status_prop}'({self.status_type}), "
                f"Date='{self.date_prop}', LMS_ID={'Có ('+self.lms_id_prop+')' if self.lms_id_prop else 'Không (dùng Title)'}"
            )
        except Exception as e:
            logging.warning(f"Notion: Lỗi khi kiểm tra schema, dùng cấu hình mặc định: {e}")

    # ==================== TÌM KIẾM ====================

    def find_page(self, lms_id=None, task_name=None):
        """Tìm page trong Notion Database để tránh tạo trùng.
        Ưu tiên tìm theo LMS ID nếu bảng có cột đó, ngược lại tìm theo Tên deadline.
        """
        url = f"{NOTION_API_BASE}/databases/{self.database_id}/query"
        payload = {"page_size": 1}

        if self.lms_id_prop and lms_id:
            payload["filter"] = {
                "property": self.lms_id_prop,
                "rich_text": {"equals": str(lms_id)}
            }
        elif self.title_prop and task_name:
            payload["filter"] = {
                "property": self.title_prop,
                "title": {"equals": task_name[:2000]}
            }
        else:
            return None

        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=10)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    return results[0]["id"]
            return None
        except Exception as e:
            logging.debug(f"Notion: Lỗi khi tìm kiếm page: {e}")
            return None

    def find_page_by_lms_id(self, lms_id):
        """Alias tương thích ngược."""
        return self.find_page(lms_id=lms_id)

    # ==================== THÊM DEADLINE ====================

    def add_deadline(self, task_name, course_name, deadline_dt, url, lms_id, source="Moodle"):
        """Thêm một deadline mới vào Notion Database với trạng thái To-do.
        Tự động bỏ qua các cột không tồn tại trên bảng.
        """
        try:
            # Kiểm tra trùng lặp trước khi thêm
            existing = self.find_page(lms_id=lms_id, task_name=task_name)
            if existing:
                logging.debug(f"Notion: Deadline đã tồn tại — bỏ qua ('{task_name}')")
                return existing

            api_url = f"{NOTION_API_BASE}/pages"

            # Chuẩn bị deadline theo ISO 8601
            if hasattr(deadline_dt, 'isoformat'):
                deadline_iso = deadline_dt.astimezone(LOCAL_TZ).isoformat()
            else:
                deadline_iso = str(deadline_dt)

            props = {}

            # Cột Title (luôn có)
            if self.title_prop:
                props[self.title_prop] = {
                    "title": [{"text": {"content": task_name[:2000]}}]
                }

            # Cột Trạng thái
            if self.status_prop:
                if self.status_type == "status":
                    props[self.status_prop] = {"status": {"name": "To-do"}}
                else:
                    props[self.status_prop] = {"select": {"name": "To-do"}}

            # Cột Môn học
            if self.course_prop and course_name:
                props[self.course_prop] = {"select": {"name": str(course_name)[:100]}}

            # Cột Hạn chót
            if self.date_prop and deadline_iso:
                props[self.date_prop] = {"date": {"start": deadline_iso}}

            # Cột Link Moodle
            if self.url_prop and url:
                props[self.url_prop] = {"url": url}

            # Cột Nguồn
            if self.source_prop and source:
                props[self.source_prop] = {"select": {"name": source}}

            # Cột LMS ID (chỉ thêm nếu bảng thực tế có cột này)
            if self.lms_id_prop and lms_id:
                props[self.lms_id_prop] = {
                    "rich_text": [{"text": {"content": str(lms_id)}}]
                }

            payload = {
                "parent": {"database_id": self.database_id},
                "properties": props
            }

            resp = requests.post(api_url, headers=self.headers, json=payload, timeout=10)
            if resp.status_code in (200, 201):
                page_id = resp.json()["id"]
                logging.info(f"✅ Notion: Đã thêm '{task_name}' ({course_name})")
                return page_id
            else:
                logging.warning(f"Notion: Thêm deadline thất bại ({resp.status_code}): {resp.text[:300]}")
                return None
        except Exception as e:
            logging.warning(f"Notion: Lỗi ngoại lệ khi thêm deadline '{task_name}': {e}")
            return None

    # ==================== ĐÁNH DẤU HOÀN THÀNH ====================

    def mark_completed(self, lms_id, completed_by=None, task_name=None):
        """Chuyển trạng thái task trên Notion sang Done."""
        try:
            page_id = self.find_page(lms_id=lms_id, task_name=task_name)
            if not page_id:
                logging.debug(f"Notion: Không tìm thấy page để đánh dấu hoàn thành ({lms_id})")
                return False

            if not self.status_prop:
                return False

            url = f"{NOTION_API_BASE}/pages/{page_id}"
            if self.status_type == "status":
                status_val = {"status": {"name": "Done"}}
            else:
                status_val = {"select": {"name": "Done"}}

            payload = {"properties": {self.status_prop: status_val}}
            resp = requests.patch(url, headers=self.headers, json=payload, timeout=10)
            if resp.status_code == 200:
                logging.info(f"✅ Notion: Đã đánh dấu hoàn thành ({lms_id}, bởi {completed_by})")
                return True
            return False
        except Exception as e:
            logging.warning(f"Notion: Lỗi khi đánh dấu hoàn thành: {e}")
            return False

    # ==================== ĐỒNG BỘ HÀNG LOẠT ====================

    def sync_all_deadlines(self, deadlines):
        """Đồng bộ hàng loạt deadline lên Notion (dùng cho lần chạy đầu)."""
        stats = {'added': 0, 'skipped': 0, 'failed': 0}

        for dl in deadlines:
            lms_id = dl['lms_deadlines_id']
            task_name = dl['deadline_name']
            source = "Discord" if str(lms_id).startswith('manual-') else "Moodle"

            due_time = dl['due_time']
            if due_time and not due_time.tzinfo:
                due_time = due_time.replace(tzinfo=timezone.utc)

            # Kiểm tra xem đã có chưa
            existing = self.find_page(lms_id=lms_id, task_name=task_name)
            if existing:
                stats['skipped'] += 1
                if dl.get('completed'):
                    self.mark_completed(lms_id, dl.get('completed_by'), task_name=task_name)
                continue

            result = self.add_deadline(
                task_name=task_name,
                course_name=dl['course_name'],
                deadline_dt=due_time,
                url=dl.get('source_url', ''),
                lms_id=lms_id,
                source=source,
            )

            if result:
                stats['added'] += 1
                if dl.get('completed'):
                    self.mark_completed(lms_id, dl.get('completed_by'), task_name=task_name)
            else:
                stats['failed'] += 1

        logging.info(
            f"Notion sync hoàn tất: "
            f"{stats['added']} thêm mới, {stats['skipped']} đã có, "
            f"{stats['failed']} lỗi."
        )
        return stats

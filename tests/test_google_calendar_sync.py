"""Unit tests cho module google_calendar_sync."""
import json
import base64
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from src.google_calendar_sync import (
    GoogleCalendarSync,
    _parse_credentials,
    LOCAL_TZ,
    TIMEZONE_NAME,
)


class TestGoogleCalendarSync(unittest.TestCase):

    def setUp(self):
        self.sample_sa_info = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQD...\n-----END PRIVATE KEY-----\n",
            "client_email": "test-sa@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        self.sample_sa_json = json.dumps(self.sample_sa_info)
        self.sample_sa_base64 = base64.b64encode(self.sample_sa_json.encode("utf-8")).decode("utf-8")

    @patch("google.oauth2.service_account.Credentials.from_service_account_info")
    def test_parse_credentials_from_raw_json(self, mock_from_info):
        mock_from_info.return_value = MagicMock()
        creds = _parse_credentials(sa_json=self.sample_sa_json)
        self.assertIsNotNone(creds)
        mock_from_info.assert_called_once()

    @patch("google.oauth2.service_account.Credentials.from_service_account_info")
    def test_parse_credentials_from_base64(self, mock_from_info):
        mock_from_info.return_value = MagicMock()
        creds = _parse_credentials(sa_json=self.sample_sa_base64)
        self.assertIsNotNone(creds)
        mock_from_info.assert_called_once()

    @patch("google.oauth2.service_account.Credentials.from_service_account_file")
    def test_parse_credentials_from_file(self, mock_from_file):
        mock_from_file.return_value = MagicMock()
        creds = _parse_credentials(sa_file="some_file.json")
        self.assertIsNotNone(creds)
        mock_from_file.assert_called_once_with("some_file.json", scopes=["https://www.googleapis.com/auth/calendar"])

    def test_parse_credentials_empty(self):
        creds = _parse_credentials()
        self.assertIsNone(creds)

    @patch("googleapiclient.discovery.build")
    @patch("src.google_calendar_sync._parse_credentials")
    def test_init_success(self, mock_parse_creds, mock_build):
        mock_parse_creds.return_value = MagicMock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        gcal = GoogleCalendarSync(sa_json=self.sample_sa_json, calendar_id="test_cal_id")
        self.assertTrue(gcal.is_available())
        self.assertEqual(gcal.calendar_id, "test_cal_id")

    def test_unavailable_service_safety(self):
        # Khi không có credentials, gcal.is_available() trả về False và các method không crash
        gcal = GoogleCalendarSync(sa_json=None, sa_file=None)
        self.assertFalse(gcal.is_available())
        self.assertIsNone(gcal.add_deadline("Task 1", "Course A", datetime.now(timezone.utc), lms_id="123"))
        self.assertFalse(gcal.mark_completed("123"))
        stats = gcal.sync_all_deadlines([])
        self.assertEqual(stats["added"], 0)

    @patch("googleapiclient.discovery.build")
    @patch("src.google_calendar_sync._parse_credentials")
    def test_add_deadline_new_event(self, mock_parse_creds, mock_build):
        mock_parse_creds.return_value = MagicMock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock events().list() trả về rỗng (chưa có event)
        mock_events = mock_service.events.return_value
        mock_list = mock_events.list.return_value
        mock_list.execute.return_value = {"items": []}

        # Mock events().insert() trả về id mới
        mock_insert = mock_events.insert.return_value
        mock_insert.execute.return_value = {"id": "google_event_123"}

        gcal = GoogleCalendarSync(sa_json=self.sample_sa_json, calendar_id="test_cal_id")
        due_time = datetime(2026, 10, 25, 23, 59, tzinfo=timezone.utc)
        event_id = gcal.add_deadline(
            task_name="Đồ án 1",
            course_name="NMTTNT",
            deadline_dt=due_time,
            url="https://courses.fit.hcmus.edu.vn",
            lms_id="assign-999",
            source="Moodle"
        )

        self.assertEqual(event_id, "google_event_123")
        mock_events.insert.assert_called_once()
        call_kwargs = mock_events.insert.call_args[1]
        body = call_kwargs["body"]

        self.assertIn("[NMTTNT] Đồ án 1", body["summary"])
        self.assertEqual(body["extendedProperties"]["private"]["lms_id"], "assign-999")
        self.assertEqual(len(body["reminders"]["overrides"]), 3)

    @patch("googleapiclient.discovery.build")
    @patch("src.google_calendar_sync._parse_credentials")
    def test_add_deadline_naive_utc_datetime(self, mock_parse_creds, mock_build):
        mock_parse_creds.return_value = MagicMock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_events = mock_service.events.return_value
        mock_events.list.return_value.execute.return_value = {"items": []}
        mock_events.insert.return_value.execute.return_value = {"id": "gcal_evt_naive"}

        gcal = GoogleCalendarSync(sa_json=self.sample_sa_json, calendar_id="test_cal_id")
        # Naive datetime from Postgres representing 05:00 UTC (which is 12:00 Vietnam time)
        naive_due = datetime(2026, 9, 18, 5, 0)
        gcal.add_deadline(
            task_name="test dk",
            course_name="CSC10012",
            deadline_dt=naive_due,
            lms_id="manual-123",
        )

        call_kwargs = mock_events.insert.call_args[1]
        body = call_kwargs["body"]
        # Must be 12:00 UTC+7 (+07:00)
        self.assertEqual(body["end"]["dateTime"], "2026-09-18T12:00:00+07:00")
        self.assertEqual(body["start"]["dateTime"], "2026-09-18T11:30:00+07:00")


    @patch("googleapiclient.discovery.build")
    @patch("src.google_calendar_sync._parse_credentials")
    def test_mark_completed(self, mock_parse_creds, mock_build):
        mock_parse_creds.return_value = MagicMock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock find_event_by_lms_id tìm thấy event
        mock_events = mock_service.events.return_value
        mock_list = mock_events.list.return_value
        mock_list.execute.return_value = {
            "items": [{
                "id": "existing_event_id",
                "summary": "[NMTTNT] Đồ án 1",
                "description": "Chi tiết cũ...",
            }]
        }

        # Mock events().patch()
        mock_patch = mock_events.patch.return_value
        mock_patch.execute.return_value = {"id": "existing_event_id"}

        gcal = GoogleCalendarSync(sa_json=self.sample_sa_json, calendar_id="test_cal_id")
        success = gcal.mark_completed("assign-999", completed_by="Nguyen")

        self.assertTrue(success)
        mock_events.patch.assert_called_once()
        patch_kwargs = mock_events.patch.call_args[1]
        patch_body = patch_kwargs["body"]

        self.assertTrue(patch_body["summary"].startswith("✅ [XONG]"))
        self.assertEqual(patch_body["colorId"], "10")
        self.assertEqual(patch_body["extendedProperties"]["private"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()

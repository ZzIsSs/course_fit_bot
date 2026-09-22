# -*- coding: utf-8 -*-
import sys
import os
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db_queries import get_known_modules_for_course


def test_get_known_modules_timezone():
    # Giả lập 1 timestamp UTC cụ thể
    expected_epoch = 1727013141  # 2024-09-22 13:52:21 UTC
    dt_utc = datetime.fromtimestamp(expected_epoch, tz=timezone.utc)
    dt_naive = dt_utc.replace(tzinfo=None)  # Giống như Postgres timestamp without time zone trả về

    mock_rows = [
        {'lms_module_id': '101', 'time_modified': dt_naive},
        {'lms_module_id': '102', 'time_modified': dt_utc},
        {'lms_module_id': '103', 'time_modified': expected_epoch},
    ]

    with patch('src.db_queries.fetch_all', return_value=mock_rows):
        result = get_known_modules_for_course(None, 1)

    print("Result:", result)
    assert result['101'] == expected_epoch, f"Expected {expected_epoch}, got {result['101']}"
    assert result['102'] == expected_epoch, f"Expected {expected_epoch}, got {result['102']}"
    assert result['103'] == expected_epoch, f"Expected {expected_epoch}, got {result['103']}"
    print("ALL TESTS PASSED! Naive datetime correctly normalized to UTC.")


if __name__ == '__main__':
    test_get_known_modules_timezone()

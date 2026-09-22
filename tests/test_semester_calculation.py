# -*- coding: utf-8 -*-
import sys
import os
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.moodle_parser import get_current_semester, parse_moodle_semester_code, extract_semester_index


def test_case_1():
    print("\n--- Test Case 1: 19/09/2026 (September) ---")
    dt = datetime(2026, 9, 19)
    result = get_current_semester(dt)
    print(f"Input: {dt.strftime('%d/%m/%Y')} -> Result: {result}")
    assert result["semester"] == 1, f"Expected semester 1, got {result['semester']}"
    assert result["academicYear"] == "2026 - 2027", f"Expected '2026 - 2027', got {result['academicYear']}"
    assert result["label"] == "Học kỳ 1 (2026 - 2027)", f"Expected 'Học kỳ 1 (2026 - 2027)', got {result['label']}"
    print(" PASSED: Test Case 1")


def test_case_2():
    print("\n--- Test Case 2: 15/03/2026 (March) ---")
    dt = datetime(2026, 3, 15)
    result = get_current_semester(dt)
    print(f"Input: {dt.strftime('%d/%m/%Y')} -> Result: {result}")
    assert result["semester"] == 2, f"Expected semester 2, got {result['semester']}"
    assert result["academicYear"] == "2025 - 2026", f"Expected '2025 - 2026', got {result['academicYear']}"
    assert result["label"] == "Học kỳ 2 (2025 - 2026)", f"Expected 'Học kỳ 2 (2025 - 2026)', got {result['label']}"
    print(" PASSED: Test Case 2")


def test_case_3():
    print("\n--- Test Case 3: 10/07/2026 (July) ---")
    dt = datetime(2026, 7, 10)
    result = get_current_semester(dt)
    print(f"Input: {dt.strftime('%d/%m/%Y')} -> Result: {result}")
    assert result["semester"] == 3, f"Expected semester 3, got {result['semester']}"
    assert result["academicYear"] == "2025 - 2026", f"Expected '2025 - 2026', got {result['academicYear']}"
    assert result["label"] == "Học kỳ Hè (2025 - 2026)", f"Expected 'Học kỳ Hè (2025 - 2026)', got {result['label']}"
    print(" PASSED: Test Case 3")


def test_edge_case_january():
    print("\n--- Test Edge Case: 15/01/2026 (January edge case) ---")
    dt = datetime(2026, 1, 15)
    result = get_current_semester(dt)
    print(f"Input: {dt.strftime('%d/%m/%Y')} -> Result: {result}")
    assert result["semester"] == 1, f"Expected semester 1, got {result['semester']}"
    assert result["academicYear"] == "2025 - 2026", f"Expected '2025 - 2026', got {result['academicYear']}"
    assert result["label"] == "Học kỳ 1 (2025 - 2026)", f"Expected 'Học kỳ 1 (2025 - 2026)', got {result['label']}"
    print(" PASSED: Test Edge Case January")


def test_case_4_moodle_formats():
    print("\n--- Test Case 4: Multiple Moodle Code Formats ---")
    test_samples = [
        {
            "code": "CQ2425HK1_CSC10001_CQ2024/1",
            "expected_year": "2024 - 2025",
            "expected_sem": 1,
            "expected_prefix": "CQ",
            "expected_cohort": 2024,
            "expected_index": 1,
        },
        {
            "code": "CLC2526HK2_CSC10014_CLC2024/2",
            "expected_year": "2025 - 2026",
            "expected_sem": 2,
            "expected_prefix": "CLC",
            "expected_cohort": 2024,
            "expected_index": 4,
        },
        {
            "code": "VP2024_2025_1_MTH00003",
            "expected_year": "2024 - 2025",
            "expected_sem": 1,
            "expected_prefix": "VP",
            "expected_cohort": None,
            "expected_index": None,
        },
        {
            "code": "CTTT2425_2_CSC10004",
            "expected_year": "2024 - 2025",
            "expected_sem": 2,
            "expected_prefix": "CTTT",
            "expected_cohort": None,
            "expected_index": None,
        },
        {
            "code": "2024_2025_HK1_CSC10005",
            "expected_year": "2024 - 2025",
            "expected_sem": 1,
            "expected_prefix": None,
            "expected_cohort": None,
            "expected_index": None,
        },
        {
            "code": "VHVL2425-2_CSC10006",
            "expected_year": "2024 - 2025",
            "expected_sem": 2,
            "expected_prefix": "VHVL",
            "expected_cohort": None,
            "expected_index": None,
        },
    ]

    for sample in test_samples:
        raw = sample["code"]
        parsed = parse_moodle_semester_code(raw)
        print(f"\nParsing '{raw}':")
        print(f" -> Result: {parsed}")
        assert parsed is not None, f"Failed to parse {raw}"
        assert parsed["academicYear"] == sample["expected_year"], f"Year mismatch for {raw}: got {parsed['academicYear']}"
        assert parsed["semester"] == sample["expected_sem"], f"Semester mismatch for {raw}: got {parsed['semester']}"
        if sample["expected_prefix"]:
            assert parsed["prefix"] == sample["expected_prefix"], f"Prefix mismatch for {raw}: got {parsed['prefix']}"
        if sample["expected_cohort"]:
            assert parsed["cohort_year"] == sample["expected_cohort"], f"Cohort mismatch for {raw}: got {parsed['cohort_year']}"
        if sample["expected_index"]:
            assert parsed["semester_index"] == sample["expected_index"], f"Index mismatch for {raw}: got {parsed['semester_index']}"
            assert extract_semester_index(raw) == sample["expected_index"], f"extract_semester_index failed for {raw}"
        print(f"   OK: {raw} parsed correctly.")

    print("\n PASSED: Test Case 4 (All 6 Moodle formats verified)")


if __name__ == "__main__":
    print("==================================================")
    print("STARTING SEMESTER CALCULATION VERIFICATION TESTS")
    print("==================================================")
    test_case_1()
    test_case_2()
    test_case_3()
    test_edge_case_january()
    test_case_4_moodle_formats()
    print("\n==================================================")
    print(" ALL 4 TEST CASES & EDGE CASES PASSED SUCCESSFULLY!")
    print("==================================================")

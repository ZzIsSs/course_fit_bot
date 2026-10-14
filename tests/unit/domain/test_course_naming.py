# -*- coding: utf-8 -*-
"""Characterization tests cho extract_display_name.

Cố định OUTPUT HIỆN TẠI (ghi ngày 2026-10-15, xem mục 5.1 của
docs/architecture/refactoring-blueprint.md), không phải output mong muốn.
Mục đích: bắt mọi thay đổi hành vi ngoài ý muốn trong lúc refactor.

Các dòng đánh dấu PROBABLE BUG được giữ nguyên như hiện tại. Sửa chúng phải là
một commit đổi hành vi riêng, cập nhật test trong cùng commit đó.
"""
import pytest

from course_bot.domain.course_naming import extract_display_name


@pytest.mark.parametrize("fullname, current_output", [
    ("CQ2526HK2_CSC10014_CQ2024/2 - Nhập Môn Trí Tuệ Nhân Tạo", "Nhập Môn Trí Tuệ Nhân Tạo"),
    ("Tư duy tính toán - CQ2024/2", "Tư duy tính toán"),
    # PROBABLE BUG: mong muốn 'Cơ sở dữ liệu'
    ("Cơ sở dữ liệu - CSC10006", "CSC10006"),
    # Cần quyết định: bản nháp mong muốn None, nhưng bên gọi có thể đang dựa vào mã môn
    ("CSC10014", "CSC10014"),
    # Cần quyết định: chưa có output mong muốn
    ("CSC10006_CQ2024/2", "CSC10006_CQ2024/2"),
    # PROBABLE BUG: mong muốn 'Mạng Máy Tính'
    ("[CQ2024/2] Mạng Máy Tính", "[CQ2024/2] Mạng Máy Tính"),
    # PROBABLE BUG: mong muốn 'Hệ điều hành'
    ("CSC13102 - Hệ điều hành (TH)", "Hệ điều hành (TH)"),
])
def test_extract_display_name_current_behaviour(fullname, current_output):
    assert extract_display_name(fullname) == current_output

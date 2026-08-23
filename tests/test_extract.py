# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.moodle_parser import extract_display_name
res1 = extract_display_name('CQ2526HK2_CSC10014_CQ2024/2 - Nhập Môn Trí Tuệ Nhân Tạo')
res2 = extract_display_name('Tư duy tính toán - CQ2024/2')
res3 = extract_display_name('Cơ sở dữ liệu - CSC10006')
res4 = extract_display_name('CSC10014')
res5 = extract_display_name('CSC10006_CQ2024/2')

with open("test_out.txt", "w", encoding="utf-8") as f:
    f.write(f"1: {res1}\n")
    f.write(f"2: {res2}\n")
    f.write(f"3: {res3}\n")
    f.write(f"4: {res4}\n")
    f.write(f"5: {res5}\n")

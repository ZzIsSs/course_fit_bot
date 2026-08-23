# -*- coding: utf-8 -*-
import re

def smart_extract_display_name(fullname):
    if not fullname:
        return None
    
    name = re.sub(r'[-_/\(\)\[\]\|]+', ' ', fullname)
    name = re.sub(r'\b[A-Z]{2,5}\d{4,6}\b', '', name)
    name = re.sub(r'\b(CQ|CLC|VP|CTTT|TH|HK)\w*\b', '', name)
    name = re.sub(r'\b\d+\b', '', name)
    name = ' '.join(name.split())
    
    return name if name else None

fullnames = [
    'CQ2526HK2_CSC10014_CQ2024/2 - Nhập Môn Trí Tuệ Nhân Tạo',
    'Tư duy tính toán - CQ2024/2',
    'Cơ sở dữ liệu - CSC10006',
    'CSC10014',
    '[CQ2024/2] Mạng Máy Tính',
    'CSC13102 - Hệ điều hành (TH)',
]

with open("test_out3.txt", "w", encoding="utf-8") as f:
    for fn in fullnames:
        f.write(f"{fn} -> {smart_extract_display_name(fn)}\n")

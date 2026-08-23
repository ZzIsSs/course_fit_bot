# -*- coding: utf-8 -*-
import re

def smart_extract_display_name(fullname):
    if not fullname:
        return None
    
    # 1. Remove subject codes (e.g., CSC10014)
    name = re.sub(r'\b[A-Z]{2,5}\d{4,6}\b', '', fullname)
    
    # 2. Remove class codes (e.g., CQ2526HK2, CQ2024/2, CLC..., VP...)
    name = re.sub(r'\b(CQ|CLC|VP|CTTT|TH)[A-Z0-9/]+\b', '', name)
    
    # 3. Clean up leftover punctuation (hyphens, underscores, slashes, parens)
    name = re.sub(r'[-_/\(\)\[\]\|]+', ' ', name)
    
    # 4. Strip extra spaces
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

with open("test_out2.txt", "w", encoding="utf-8") as f:
    for fn in fullnames:
        f.write(f"{fn} -> {smart_extract_display_name(fn)}\n")

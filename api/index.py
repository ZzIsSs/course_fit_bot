"""Vercel entrypoint: vercel.json chuyển mọi /api/* về file này.

Vercel cần class `handler` ở đây; logic nằm ở course_bot/web/router.py.
"""
import os
import sys

# Đảm bảo import được package course_bot/ dù runtime không thêm gốc repo vào sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from course_bot.web.router import handler  # noqa: E402,F401

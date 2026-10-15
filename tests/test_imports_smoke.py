"""
Smoke test: mọi module trong package và các entry point đều import được.

Lưới an toàn cho đợt refactor cấu trúc thư mục (docs/architecture/refactoring-blueprint.md):
di chuyển file mà quên sửa import sẽ fail ngay tại đây thay vì lúc cron chạy.
"""
import importlib
import subprocess
import sys
import os
import pkgutil

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PACKAGE = "course_bot"


def _package_modules():
    package = importlib.import_module(PACKAGE)
    names = [PACKAGE]
    for info in pkgutil.walk_packages(package.__path__, prefix=f"{PACKAGE}."):
        names.append(info.name)
    return sorted(names)


def _api_modules():
    api_dir = os.path.join(ROOT, "api")
    return sorted(
        f"api.{name[:-3]}"
        for name in os.listdir(api_dir)
        if name.endswith(".py") and name != "__init__.py"
    )


ENTRY_MODULES = ["main"] + _api_modules()


@pytest.mark.parametrize("module_name", _package_modules() + ENTRY_MODULES)
def test_module_imports(module_name):
    importlib.import_module(module_name)


def test_vercel_handler_exported():
    """vercel.json rewrite /api/(.*) -> /api/index.py cần class `handler`."""
    index = importlib.import_module("api.index")
    assert hasattr(index, "handler")


def test_api_has_only_index():
    """Checklist 4.3: api/index.py là entry duy nhất; mọi route nằm trong course_bot/web/."""
    api_dir = os.path.join(ROOT, "api")
    entries = sorted(n for n in os.listdir(api_dir) if n.endswith(".py"))
    assert entries == ["index.py"]


@pytest.mark.parametrize("module, configured", [
    ("course_bot.core.config", False),   # import thư viện không được đụng root logger
    ("course_bot.jobs.notify", False),
    ("api.index", True),                 # entry Vercel tự cấu hình
])
def test_logging_configured_only_by_entry_points(module, configured):
    """Chạy trong process mới vì pytest đã gắn handler vào root logger."""
    code = (
        "import logging, importlib; "
        f"importlib.import_module({module!r}); "
        "print(len(logging.getLogger().handlers))"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert (int(out.stdout.strip()) > 0) is configured

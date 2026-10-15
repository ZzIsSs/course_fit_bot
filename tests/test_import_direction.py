"""
Kiểm tra hướng import của blueprint mục 3.3 bằng AST (kể cả import lười trong hàm).

core <- domain <- db / integrations <- services <- jobs / web
"""
import ast
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_DIR = os.path.join(ROOT, "course_bot")

# Layer -> các prefix module mà nó KHÔNG được import
FORBIDDEN = {
    "core": ["course_bot.domain", "course_bot.db", "course_bot.integrations", "course_bot.services",
             "course_bot.jobs", "course_bot.web", "course_bot.cli"],
    "domain": ["course_bot.db", "course_bot.integrations", "course_bot.services",
               "course_bot.jobs", "course_bot.web", "course_bot.cli"],
    "db": ["course_bot.integrations", "course_bot.services", "course_bot.jobs", "course_bot.web", "course_bot.cli"],
    "integrations": ["course_bot.db", "course_bot.services", "course_bot.jobs", "course_bot.web", "course_bot.cli"],
    "services": ["course_bot.jobs", "course_bot.web", "course_bot.cli"],
    "jobs": ["course_bot.jobs", "course_bot.web", "course_bot.cli"],
    "web": ["course_bot.jobs", "course_bot.cli", "course_bot.integrations.notion",
            "course_bot.integrations.google_calendar"],
}


def _modules():
    for dirpath, _, files in os.walk(PACKAGE_DIR):
        for name in files:
            if name.endswith(".py"):
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, PACKAGE_DIR).replace(os.sep, "/")
                yield rel.split("/")[0], rel, path


def _imports(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name


CASES = [(layer, rel, path) for layer, rel, path in _modules() if layer in FORBIDDEN]


@pytest.mark.parametrize("layer, rel, path", CASES, ids=[c[1] for c in CASES])
def test_import_direction(layer, rel, path):
    bad = [m for m in _imports(path)
           for prefix in FORBIDDEN[layer]
           if m == prefix or m.startswith(prefix + ".")]
    assert not bad, f"{rel} ({layer}/) không được import: {bad}"

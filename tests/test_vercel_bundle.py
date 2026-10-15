"""
Kiểm tra .vercelignore không loại bỏ module mà Serverless Function cần.

Duyệt AST (kể cả import lười bên trong hàm) bắt đầu từ mọi file trong api/,
đi theo các import `course_bot.*` một cách bắc cầu, rồi đối chiếu với .vercelignore.
Nếu một file bị ignore nhưng vẫn được import, route tương ứng sẽ lỗi
ModuleNotFoundError trên Vercel dù chạy local vẫn bình thường.
"""
import ast
import fnmatch
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = "course_bot"


def _load_ignore_patterns():
    patterns = []
    with open(os.path.join(ROOT, ".vercelignore"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def _is_ignored(rel_path, patterns):
    """So khớp theo kiểu .gitignore (đủ dùng cho các pattern hiện có)."""
    parts = rel_path.split("/")
    for pattern in patterns:
        if pattern.startswith("!"):
            raise NotImplementedError(f"Chưa hỗ trợ pattern phủ định: {pattern}")
        pat = pattern.rstrip("/")
        if "/" in pat:
            # Neo từ gốc repo: khớp chính file hoặc bất kỳ thư mục cha nào
            pat = pat.lstrip("/")
            for i in range(1, len(parts) + 1):
                if fnmatch.fnmatch("/".join(parts[:i]), pat):
                    return pattern
        else:
            # Không có '/': khớp tên ở bất kỳ cấp nào
            if any(fnmatch.fnmatch(part, pat) for part in parts):
                return pattern
    return None


def _module_to_path(module):
    base = module.replace(".", "/")
    for candidate in (f"{base}.py", f"{base}/__init__.py"):
        if os.path.exists(os.path.join(ROOT, candidate)):
            return candidate
    return None


def _local_imports(rel_path):
    with open(os.path.join(ROOT, rel_path), encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=rel_path)
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            if node.module == PACKAGE or node.module.startswith(f"{PACKAGE}."):
                modules.add(node.module)
                # `from course_bot import x` có thể là submodule
                for alias in node.names:
                    modules.add(f"{node.module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == PACKAGE or alias.name.startswith(f"{PACKAGE}."):
                    modules.add(alias.name)
    return {path for path in map(_module_to_path, modules) if path}


def _api_entry_files():
    api_dir = os.path.join(ROOT, "api")
    return sorted(f"api/{n}" for n in os.listdir(api_dir) if n.endswith(".py"))


def _reachable_from(entry):
    """Trả về {file: chuỗi import dẫn tới file đó}."""
    chains = {entry: [entry]}
    queue = [entry]
    while queue:
        current = queue.pop()
        for dep in _local_imports(current):
            if dep not in chains:
                chains[dep] = chains[current] + [dep]
                queue.append(dep)
    return chains


@pytest.mark.parametrize("entry", _api_entry_files())
def test_vercel_bundle_contains_all_imports(entry):
    patterns = _load_ignore_patterns()
    missing = []
    for path, chain in sorted(_reachable_from(entry).items()):
        pattern = _is_ignored(path, patterns)
        if pattern:
            missing.append(f"{path} (ignored by '{pattern}'): {' -> '.join(chain)}")
    assert not missing, "Vercel bundle thiếu module:\n" + "\n".join(missing)


@pytest.mark.parametrize("path, expected", [
    ("main.py", True),
    ("course_bot/jobs/notify.py", True),
    ("course_bot/cli.py", True),
    ("course_bot/integrations/notion/client.py", True),
    ("course_bot/integrations/google_calendar/client.py", True),
    ("scripts/dev/run_server.py", True),
    ("docs/x.md", True),
    ("service_account.json", True),
    ("course_bot/db/connection.py", False),
    ("api/index.py", False),
    ("course_bot/web/router.py", False),
    ("course_bot/web/routes/dashboard.py", False),
    ("course_bot/integrations/discord/signature.py", False),
])
def test_ignore_matcher(path, expected):
    assert bool(_is_ignored(path, _load_ignore_patterns())) is expected

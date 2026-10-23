"""The project's standing rule: no network calls beyond the local model runtime.

Only `ollama.py` may import an HTTP client, and its default target is loopback.
"""

from __future__ import annotations

import ast
from pathlib import Path
from urllib.parse import urlparse

from sloth_shoebox.config import Settings

PACKAGE = Path(__file__).resolve().parents[1] / "sloth_shoebox"
FORBIDDEN = {
    "requests",
    "aiohttp",
    "urllib3",
    "socket",
    "smtplib",
    "ftplib",
    "http.client",
    "urllib.request",
}


def imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_only_ollama_client_imports_http():
    for path in PACKAGE.glob("*.py"):
        mods = imports(path)
        assert not mods & FORBIDDEN, f"{path.name} imports a network library"
        if path.name != "ollama.py":
            assert "httpx" not in mods or path.name in {"parser.py", "query.py"}, path.name


def test_default_model_runtime_is_loopback():
    assert urlparse(Settings().ollama_url).hostname in {"127.0.0.1", "localhost", "::1"}


def test_page_loads_nothing_from_other_origins():
    templates = "\n".join(
        p.read_text(encoding="utf-8") for p in (PACKAGE / "templates").rglob("*.html")
    )
    css = (PACKAGE / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert "http://" not in templates.replace("http://www.w3.org", "")
    assert "https://" not in templates and "https://" not in css

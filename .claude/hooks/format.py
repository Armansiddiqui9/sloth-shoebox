"""PostToolUse hook: format Python files Claude just edited. Silent if ruff is missing."""

import json
import shutil
import subprocess
import sys

try:
    path = json.load(sys.stdin).get("tool_input", {}).get("file_path", "")
except (ValueError, AttributeError):
    sys.exit(0)

if path.endswith(".py") and shutil.which("ruff"):
    subprocess.run(["ruff", "format", "--quiet", path], check=False)
    subprocess.run(["ruff", "check", "--fix", "--quiet", path], check=False)

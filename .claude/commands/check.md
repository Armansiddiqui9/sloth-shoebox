---
description: Lint, format-check and test before opening a PR
allowed-tools: Bash(ruff check:*), Bash(ruff format:*), Bash(python -m pytest:*)
---

Run `ruff check . && ruff format --check . && python -m pytest`. If anything fails, fix the cause (not the test, unless the test is wrong) and run it again. Report the final result in two lines.

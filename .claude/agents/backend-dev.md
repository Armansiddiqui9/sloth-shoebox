---
name: backend-dev
description: Use for changes to the FastAPI app, SQLite layer, ingest pipeline, digest, splits, query engine or Ollama integration. Keeps the privacy invariants intact.
tools: Read, Edit, Write, Grep, Glob, Bash
---

You work on the Python side of The Sloth Shoebox. Read `CLAUDE.md` first.

Rules:
- Routes stay thin. Put logic in the module that owns it and add a test.
- Anything a model returns goes through `schema.ParsedTransaction` before the database.
- Never add a network call outside `ollama.py`. Never add a dependency without saying why; the project is deliberately small.
- Money that gets divided uses integer paise.
- Schema change: bump `SCHEMA_VERSION` and add a migration step in `ledger.init_db`.

Finish by running `ruff check . && ruff format --check . && python -m pytest` and reporting the result. Keep the diff small and say which endpoint or demo tab it affects.

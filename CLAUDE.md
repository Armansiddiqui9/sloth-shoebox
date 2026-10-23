# The Sloth Shoebox: guide for Claude Code

Local-first expense ledger. FastAPI + SQLite + Jinja + vanilla JS. No build step, no Node.
The product idea is fixed: files in, ledger out, nothing leaves the machine. `docs/Sloth_Shoebox_Documentation.md` is the specification; read it before changing behaviour.

## Commands

```bash
pip install -r requirements-dev.txt      # once, inside a venv
python -m sloth_shoebox                  # serve on http://127.0.0.1:8337
python -m sloth_shoebox seed             # reset demo data
ruff check . && ruff format --check .    # lint (use `ruff check --fix . && ruff format .` to fix)
python -m pytest                         # 49 tests, about 1 second
```

Run lint and tests before saying a change is done.

## Map

- `sloth_shoebox/app.py`: routes only. Logic lives in the modules below.
- `ingest.py`: the pipeline. Duplicate -> schema validation -> commit, review (confidence < 0.8) or quarantine.
- `schema.py`: `ParsedTransaction` is the trust boundary for anything a model returns.
- `ledger.py`: DDL, `TxFilter`, CRUD. Schema changes bump `SCHEMA_VERSION` and need a migration step in `init_db`.
- `digest.py`, `splits.py`, `query.py`, `export.py`, `categorize.py`: pure logic, easy to test.
- `parser.py` and `ollama.py`: the only model-facing code. Prompts live in `prompts/`.
- `content.py`: all page copy and tables. Change words here, not in templates.
- `templates/sections/*.html`: one file per page section. `static/js/tabs/*.js`: one module per demo tab.

## Invariants (do not break)

1. No network access except `ollama.py` to a local Ollama server. `tests/test_no_network_in_parse_path.py` guards it.
2. The CSP in `app.py` blocks external origins. Do not add CDN scripts, fonts, analytics or remote images.
3. Model output never reaches the database without passing `ParsedTransaction`.
4. Only `status = 'success'` counts as spend. Failed and reversed rows are kept and shown.
5. Money in `splits.py` is integer paise so shares always sum to the amount.
6. The `upi-failed` sample is quarantined on purpose (category `uncategorized` is invalid). It demonstrates the failure path; do not "fix" it.
7. User-supplied strings are escaped in JS via `html` from `static/js/dom.js`. Never assign raw strings to `innerHTML`.

## Design system

The look is an Indian cash-memo bill book: pink duplicate paper, one blue print ink, red serial stamp, ballpoint for handwriting. Tokens are CSS variables at the top of `static/css/app.css`.

- Fonts: Archivo (variable width and weight; condensed for headings) and Kalam (handwriting, only for things a person "writes": hero memo, notes, query answers). Self-hosted in `static/fonts`.
- Colour roles: ink = structure and text, pen = actions and interactive state, red = errors, quarantine, serial numbers, yellow = needs review or highlight, moss = committed.
- Keep: sentence-case headings, left-aligned layouts, ruled-table and perforation-line devices, one orchestrated motion (the hero memo writing in).
- Avoid: eyebrow labels, numbered section markers, all-caps small labels, mono for UI labels, arrow glyphs in links, gradient text, identical rounded card grids, emoji.
- Respect `prefers-reduced-motion`. Every control needs a visible focus state.
- After UI changes, check the page at 1360 px and 390 px wide.

## Conventions

- Python 3.11+, type hints, `ruff` rules in `pyproject.toml`. Prefer small pure functions.
- JSON API fields are snake_case. Errors are `{"detail": "..."}`.
- SQLite connections are per request (`ledger.session`). They are opened with `check_same_thread=False` because FastAPI may open and close a dependency on different threads.
- Tests use `TestClient` (needs `httpx2` with current Starlette) and fake the model with `httpx.MockTransport`. Never call a real model in tests.
- Work in small PRs: one endpoint, tab or fix each. Say which section or tab the change shows up in.

## Recipes

- **New endpoint**: model in `schema.py`, logic in a module, thin route in `app.py`, test in `tests/test_api.py`, row in the README API table.
- **New demo tab**: `<button role="tab">` and `<div role="tabpanel">` in `templates/sections/demo.html`, module in `static/js/tabs/` exporting `mount(el, ctx)` and optional `show()`, register in `main.js`.
- **New category**: add to the `Category` literal in `categorize.py`, to `CATEGORY_WORDS` in `query.py`, and to merchants if useful.
- **Copy change**: edit `content.py`; docs text lives in `docs/`.

## Not built yet (see roadmap in `content.py`)

Folder watcher, perceptual hashing (dedupe is exact hash plus payment reference), Tesseract assist, PDF parsing, XLSX export, refund tracker, subscription-leak alerts.

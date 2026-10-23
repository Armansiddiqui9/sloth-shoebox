# The Sloth Shoebox

A local-first expense ledger built from the payments you already saved: UPI screenshots, receipt photos and PDF bills. Drop files in, get a categorised, exportable ledger out. No cloud, no accounts, no subscriptions, no SMS permission.

The app is a FastAPI server with a single-page site and a working demo: an ingest pipeline (dedupe, parse, validate, commit), a ledger, a monthly digest, roommate splits, and offline natural-language queries over one local SQLite file.

## Run it

Needs Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m sloth_shoebox
```

Open <http://127.0.0.1:8337>. The first run creates `data/sloth_shoebox.db` and fills it with 28 demo transactions. Delete that file to erase everything.

```bash
python -m sloth_shoebox seed   # reset the demo data
```

Or with Docker:

```bash
docker build -t sloth-shoebox .
docker run --rm -p 8337:8337 -v sloth-data:/data sloth-shoebox
```

## What you will see

| Where | What it does |
| --- | --- |
| Hero | A cash memo filled in from three artifacts. |
| Demo, Inbox | Pick a sample or drop a file. Watch dedupe, parse, validate, commit. Drop the same file twice to see the duplicate quarantine. The "failed payment" sample is quarantined on purpose (its category is not a known one). |
| Demo, Ledger | Search, filter, edit category and notes, flag for review, delete, export CSV. |
| Demo, Digest | Month totals, categories, merchants, change against the trailing three-month average. |
| Demo, Splits | Who owes whom, in the fewest transfers. |
| Demo, Query | Ask the ledger in plain English. |
| Docs | The full specification, rendered from `docs/`. |

## Local models (optional)

Everything works without a model. Install [Ollama](https://ollama.com) to turn two things on:

- **Query tab**: answered by `SLOTH_TEXT_MODEL` instead of the built-in rules engine. The tab tells you which one answered.
- **Parsing your own files**: set `SLOTH_PARSER=ollama` and unknown images go to `SLOTH_VLM_MODEL`, with one re-ask on bad output and quarantine after that. Without it, unknown files get a deterministic stand-in parse so the demo stays repeatable.

```bash
ollama pull phi4-mini
SLOTH_PARSER=ollama python -m sloth_shoebox
```

Model names are whatever you have pulled. Set them in `.env` (see `.env.example`).

## Configuration

All optional, read from the environment.

| Variable | Default | Meaning |
| --- | --- | --- |
| `SLOTH_HOST` / `SLOTH_PORT` | `127.0.0.1` / `8337` | Where to listen. |
| `SLOTH_DB` | `data/sloth_shoebox.db` | The ledger file. |
| `SLOTH_AUTOSEED` | `1` | Seed demo data when the database is empty. |
| `SLOTH_OLLAMA_URL` | `http://127.0.0.1:11434` | Local model runtime. |
| `SLOTH_TEXT_MODEL` | `phi4-mini` | Model for the Query tab. |
| `SLOTH_VLM_MODEL` | `gemma4:12b` | Vision model for parsing. |
| `SLOTH_PARSER` | `demo` | `demo` or `ollama`. |

## API

JSON in and out. The OpenAPI schema is at `/openapi.json`.

| Method and path | Purpose |
| --- | --- |
| `GET /api/ledger` | List. Filters: `category`, `status` (`success` default, `all`, or `failed,reversed`), `from`, `to`, `q`, `limit`. |
| `GET` `PATCH` `DELETE /api/ledger/{id}` | One transaction (patch: category, status, notes, review_flag). |
| `POST /api/ingest` | Run a shipped sample: `{"sample_id": "swiggy"}`. |
| `POST /api/ingest/upload` | Multipart `file`. |
| `GET /api/inbox`, `DELETE /api/inbox/{id}` | Pipeline history. |
| `GET /api/digest?month=YYYY-MM` | Monthly digest. |
| `POST /api/query` | `{"question": "..."}`. |
| `GET /api/export` | CSV, same filters as the ledger. |
| `POST /api/splits`, `GET /api/splits/{tx_id}`, `POST /api/splits/settle` | Splits and settlement. |
| `GET /api/health`, `GET /api/samples` | Status and sample list. |

## Layout

```
sloth_shoebox/
  app.py          routes, security headers
  ingest.py       dedupe -> validate -> commit / review / quarantine
  parser.py       sample parse, stand-in parse, Ollama vision parse
  schema.py       Pydantic contracts (the parse boundary)
  ledger.py       SQLite schema and queries
  digest.py       monthly digest maths
  splits.py       settlement (integer paise)
  query.py        Ollama answer, rules-engine fallback
  categorize.py   categories, merchant normalisation
  seed.py         28 demo transactions
  content.py      site copy as data
  templates/      Jinja pages, one file per section
  static/         css, js (no build step), fonts, sample images
docs/             specification
tests/            pytest
.claude/          agents and commands for Claude Code
CLAUDE.md         project guide for Claude Code
```

## Develop

```bash
pip install -r requirements-dev.txt
ruff check . && ruff format --check .
python -m pytest
```

`make check` runs both. CI does the same on Python 3.11 and 3.13. See `CONTRIBUTING.md`.

## Privacy contract

Images are read from disk by a local process and never transmitted. The only network use in the codebase is the optional call to a local Ollama server, and a test fails the build if any other module imports a network library. The page is served with a Content Security Policy that blocks every external origin.

## Licence

Code is MIT. Model weights keep their own licences.

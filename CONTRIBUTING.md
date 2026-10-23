# Contributing

Small, single-purpose pull requests merge fastest. One endpoint, one tab, or one fix per PR.

1. `pip install -r requirements-dev.txt`
2. Make the change. Add or update a test in `tests/`.
3. `ruff check . && ruff format --check . && python -m pytest`
4. In the PR, say which section or demo tab the change shows up in.

## Ground rules

- **No new network calls.** Only `sloth_shoebox/ollama.py` talks to a model runtime, and only on loopback by default. `tests/test_no_network_in_parse_path.py` enforces it.
- **No build step for the front end.** Plain ES modules in `static/js`, plain CSS in `static/css`. No CDN links, no remote fonts.
- **Validate at the boundary.** Anything a model produces goes through `schema.ParsedTransaction` before it touches the database.
- **Failed and reversed payments are stored but never counted as spend.**
- Copy lives in `content.py`, not in templates.

## Using Claude Code

The repo ships a `CLAUDE.md`, project subagents in `.claude/agents/` and slash commands in `.claude/commands/`. Run `/check` before opening a PR.

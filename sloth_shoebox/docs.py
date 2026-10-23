"""Render the specification (docs/Sloth_Shoebox_Documentation.md) for the Docs section."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import markdown


@dataclass(frozen=True)
class RenderedDocs:
    html: str
    toc: list[dict[str, object]]  # [{"id", "text", "level"}]
    sections: int


_MISSING = RenderedDocs("<p>The documentation file could not be found.</p>", [], 0)
_TITLE = re.compile(r"\A# .*\n+")
_INLINE_TOC = re.compile(r"## Table of Contents\n.*?\n---\n", re.DOTALL)


def _flatten(tokens: list[dict], out: list[dict[str, object]]) -> None:
    for token in tokens:
        out.append({"id": token["id"], "text": token["name"], "level": token["level"]})
        _flatten(token.get("children", []), out)


def load_docs(path: Path) -> RenderedDocs:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return _MISSING
    # The page title and the hand-written contents list are replaced by the sidebar.
    source = _INLINE_TOC.sub("", _TITLE.sub("", source, count=1), count=1)
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "toc", "sane_lists"],
        extension_configs={"toc": {"toc_depth": "2-3"}},
    )
    html = md.convert(source)
    toc: list[dict[str, object]] = []
    _flatten(md.toc_tokens, toc)
    return RenderedDocs(html, toc, sum(1 for t in toc if t["level"] == 2))

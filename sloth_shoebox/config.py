"""Runtime settings, read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parent


def _flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    db_path: Path = Path("data/sloth_shoebox.db")
    host: str = "127.0.0.1"
    port: int = 8337
    autoseed: bool = True
    # Local model runtime (Ollama). Everything works without it.
    ollama_url: str = "http://127.0.0.1:11434"
    text_model: str = "phi4-mini"
    vlm_model: str = "gemma4:12b"
    # "demo" parses unknown uploads with a deterministic stand-in;
    # "ollama" sends images to the local vision model.
    parser: str = "demo"
    docs_path: Path = REPO_DIR / "docs" / "Sloth_Shoebox_Documentation.md"

    @classmethod
    def from_env(cls) -> Settings:
        env = os.environ.get
        return cls(
            db_path=Path(env("SLOTH_DB", str(cls.db_path))),
            host=env("SLOTH_HOST", cls.host),
            port=int(env("SLOTH_PORT", str(cls.port))),
            autoseed=_flag("SLOTH_AUTOSEED", cls.autoseed),
            ollama_url=env("SLOTH_OLLAMA_URL", cls.ollama_url).rstrip("/"),
            text_model=env("SLOTH_TEXT_MODEL", cls.text_model),
            vlm_model=env("SLOTH_VLM_MODEL", cls.vlm_model),
            parser=env("SLOTH_PARSER", cls.parser).lower(),
            docs_path=Path(env("SLOTH_DOCS", str(cls.docs_path))),
        )

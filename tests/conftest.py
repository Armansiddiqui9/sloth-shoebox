from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sloth_shoebox import ledger
from sloth_shoebox.app import create_app
from sloth_shoebox.config import Settings
from sloth_shoebox.seed import seed


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # Port 9 is the discard port: nothing listens, so the Ollama path fails fast.
    return Settings(db_path=tmp_path / "test.db", ollama_url="http://127.0.0.1:9")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture
def conn(settings: Settings):
    ledger.init_db(settings.db_path)
    with ledger.session(settings.db_path) as c:
        seed(c)
        yield c


@pytest.fixture
def rows(conn):
    return ledger.digest_rows(conn)

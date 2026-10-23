"""SQLite layer: connection, schema, and transaction queries."""

from __future__ import annotations

import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

_DDL = """
CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    vendor_normalized TEXT NOT NULL,
    vendor_raw TEXT,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    datetime_local TEXT NOT NULL,
    category TEXT NOT NULL,
    payment_ref TEXT UNIQUE,
    payment_app TEXT,
    doc_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'success',
    gst_amount REAL,
    confidence REAL,
    source_file TEXT,
    content_hash TEXT UNIQUE,
    review_flag INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_tx_datetime ON transactions (datetime_local);

CREATE TABLE splits (
    id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL REFERENCES transactions (id) ON DELETE CASCADE,
    participant TEXT NOT NULL,
    share REAL NOT NULL,
    settled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE quarantined_parses (
    id TEXT PRIMARY KEY,
    source_file TEXT,
    reason TEXT,
    raw_output TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE ingest_artifacts (
    id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    stage TEXT NOT NULL,
    confidence REAL,
    parse_result_json TEXT,
    transaction_id TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

TX_COLUMNS = (
    "id",
    "vendor_normalized",
    "vendor_raw",
    "amount",
    "currency",
    "datetime_local",
    "category",
    "payment_ref",
    "payment_app",
    "doc_type",
    "status",
    "gst_amount",
    "confidence",
    "source_file",
    "content_hash",
    "review_flag",
    "notes",
    "created_at",
    "updated_at",
)


def new_id() -> str:
    return secrets.token_hex(8)


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def connect(path: Path) -> sqlite3.Connection:
    path = Path(path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    # One request owns one connection at a time; FastAPI may open and close it on
    # different worker threads, so the thread check is relaxed.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def session(path: Path) -> Iterator[sqlite3.Connection]:
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(path: Path) -> None:
    """Create tables on first run. Later schema changes bump SCHEMA_VERSION."""
    with session(path) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            conn.executescript(_DDL)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            conn.execute("PRAGMA journal_mode = WAL")


def is_empty(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


@dataclass
class TxFilter:
    category: str | None = None
    status: str | None = None  # "success" (default), "all", or comma list
    date_from: str | None = None
    date_to: str | None = None
    q: str | None = None

    def statuses(self) -> list[str] | None:
        if self.status is None or self.status == "":
            return ["success"]
        if self.status == "all":
            return None
        return [s for s in (part.strip() for part in self.status.split(",")) if s]

    def where(self) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        args: list[Any] = []
        if self.category:
            clauses.append("category = ?")
            args.append(self.category)
        statuses = self.statuses()
        if statuses is not None:
            clauses.append(f"status IN ({','.join('?' * len(statuses))})")
            args.extend(statuses)
        if self.date_from:
            clauses.append("datetime_local >= ?")
            args.append(self.date_from)
        if self.date_to:
            clauses.append("datetime_local <= ?")
            args.append(self.date_to)
        if self.q:
            clauses.append(
                "(vendor_normalized LIKE ? ESCAPE '\\' OR vendor_raw LIKE ? ESCAPE '\\')"
            )
            like = "%" + self.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            args.extend([like, like])
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", args


def list_transactions(
    conn: sqlite3.Connection, flt: TxFilter, limit: int = 200
) -> list[dict[str, Any]]:
    where, args = flt.where()
    rows = conn.execute(
        f"SELECT * FROM transactions{where} ORDER BY datetime_local DESC LIMIT ?",
        [*args, max(1, limit)],
    ).fetchall()
    return [dict(r) for r in rows]


def count_transactions(conn: sqlite3.Connection, flt: TxFilter) -> int:
    where, args = flt.where()
    return conn.execute(f"SELECT COUNT(*) FROM transactions{where}", args).fetchone()[0]


def get_transaction(conn: sqlite3.Connection, tx_id: str) -> dict[str, Any] | None:
    return row_dict(conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone())


def insert_transaction(conn: sqlite3.Connection, values: dict[str, Any]) -> dict[str, Any]:
    now = now_iso()
    row = {col: values.get(col) for col in TX_COLUMNS}
    row.update(id=new_id(), created_at=now, updated_at=now)
    row["currency"] = row["currency"] or "INR"
    row["status"] = row["status"] or "success"
    row["review_flag"] = row["review_flag"] or 0
    cols = ", ".join(row)
    marks = ", ".join(f":{c}" for c in row)
    conn.execute(f"INSERT INTO transactions ({cols}) VALUES ({marks})", row)
    return row


def update_transaction(
    conn: sqlite3.Connection, tx_id: str, changes: dict[str, Any]
) -> dict[str, Any] | None:
    allowed = {"category", "review_flag", "status", "notes"}
    changes = {k: v for k, v in changes.items() if k in allowed}
    if changes:
        sets = ", ".join(f"{k} = :{k}" for k in changes)
        conn.execute(
            f"UPDATE transactions SET {sets}, updated_at = :updated_at WHERE id = :id",
            {**changes, "updated_at": now_iso(), "id": tx_id},
        )
    return get_transaction(conn, tx_id)


def delete_transaction(conn: sqlite3.Connection, tx_id: str) -> bool:
    cur = conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    return cur.rowcount > 0


def digest_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every row the digest needs, whatever its status."""
    rows = conn.execute(
        "SELECT datetime_local, amount, category, vendor_normalized, vendor_raw, "
        "payment_app, status, review_flag FROM transactions"
    ).fetchall()
    return [dict(r) for r in rows]


def splits_for(conn: sqlite3.Connection, tx_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM splits WHERE transaction_id = ? ORDER BY created_at, rowid", (tx_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def replace_splits(
    conn: sqlite3.Connection, tx_id: str, shares: list[tuple[str, float]]
) -> list[dict[str, Any]]:
    conn.execute("DELETE FROM splits WHERE transaction_id = ?", (tx_id,))
    now = now_iso()
    conn.executemany(
        "INSERT INTO splits (id, transaction_id, participant, share, settled, created_at) "
        "VALUES (?, ?, ?, ?, 0, ?)",
        [(new_id(), tx_id, name, share, now) for name, share in shares],
    )
    return splits_for(conn, tx_id)

"""Duplicate detection: content hashes and payment reference numbers."""

from __future__ import annotations

import hashlib
import sqlite3


def content_hash(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()[:24]


def find_duplicate(
    conn: sqlite3.Connection, content_hash_value: str, payment_ref: str | None = None
) -> tuple[str, str] | None:
    """Return (existing transaction id, reason) when this artifact is already in the ledger."""
    row = conn.execute(
        "SELECT id FROM transactions WHERE content_hash = ?", (content_hash_value,)
    ).fetchone()
    if row:
        return row["id"], "Duplicate content hash, already in ledger"
    if payment_ref:
        row = conn.execute(
            "SELECT id FROM transactions WHERE payment_ref = ?", (payment_ref,)
        ).fetchone()
        if row:
            return row["id"], "Duplicate payment reference, already in ledger"
    return None

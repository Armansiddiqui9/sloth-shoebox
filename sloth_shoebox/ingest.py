"""The ingest pipeline: dedupe, validate, then commit, review or quarantine."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from pydantic import ValidationError

from .dedupe import find_duplicate
from .ledger import insert_transaction, new_id, now_iso, row_dict
from .schema import ParsedTransaction

STAGES_BEFORE_RESULT = ["queued", "deduping", "parsing", "validating"]
REVIEW_BELOW = 0.8


def _explain(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors()[:3]:
        field = ".".join(str(p) for p in err["loc"]) or "value"
        if err["type"] == "literal_error":
            parts.append(f"{field} '{err.get('input')}' is not a known value")
        else:
            parts.append(f"{field}: {err['msg']}")
    return "; ".join(parts)


def _quarantine(
    conn: sqlite3.Connection,
    artifact_id: str,
    file_name: str,
    reason: str,
    raw_output: Any,
    confidence: float | None,
    stages: list[str],
) -> dict[str, Any]:
    stages.append("quarantined")
    raw_text = raw_output if isinstance(raw_output, str) else json.dumps(raw_output, default=str)
    q_id, now = new_id(), now_iso()
    conn.execute(
        "INSERT INTO quarantined_parses (id, source_file, reason, raw_output, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (q_id, file_name, reason, raw_text, now),
    )
    conn.execute(
        "UPDATE ingest_artifacts SET stage = 'quarantined', error_message = ?, confidence = ?, "
        "parse_result_json = ?, updated_at = ? WHERE id = ?",
        (reason, confidence, raw_text, now_iso(), artifact_id),
    )
    return {
        "artifact": row_dict(
            conn.execute("SELECT * FROM ingest_artifacts WHERE id = ?", (artifact_id,)).fetchone()
        ),
        "transaction": None,
        "quarantined": row_dict(
            conn.execute("SELECT * FROM quarantined_parses WHERE id = ?", (q_id,)).fetchone()
        ),
        "stages": stages,
    }


def ingest(
    conn: sqlite3.Connection,
    *,
    file_name: str,
    file_type: str,
    content_hash: str,
    parse: dict[str, Any] | None,
    raw_output: str | None = None,
    parse_error: str | None = None,
) -> dict[str, Any]:
    """Run one artifact through the pipeline. Failed payments are committed too:
    they stay visible in the ledger but never count toward spend."""
    stages = list(STAGES_BEFORE_RESULT)
    artifact_id, now = new_id(), now_iso()
    conn.execute(
        "INSERT INTO ingest_artifacts (id, file_name, file_type, content_hash, stage, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, 'deduping', ?, ?)",
        (artifact_id, file_name, file_type, content_hash, now, now),
    )

    ref = parse.get("payment_ref") if isinstance(parse, dict) else None
    duplicate = find_duplicate(conn, content_hash, ref if isinstance(ref, str) else None)
    if duplicate:
        existing_id, reason = duplicate
        return _quarantine(
            conn,
            artifact_id,
            file_name,
            reason,
            {"content_hash": content_hash, "existing_id": existing_id},
            None,
            stages,
        )

    if parse is None:
        return _quarantine(
            conn, artifact_id, file_name, parse_error or "No parse result", raw_output, None, stages
        )

    try:
        parsed = ParsedTransaction.model_validate(parse)
    except ValidationError as exc:
        confidence = parse.get("confidence")
        return _quarantine(
            conn,
            artifact_id,
            file_name,
            f"Schema validation failed after re-ask: {_explain(exc)}",
            parse,
            confidence if isinstance(confidence, (int, float)) else None,
            stages,
        )

    needs_review = parsed.confidence < REVIEW_BELOW or parsed.force_review
    values = parsed.model_dump(exclude={"force_review"})
    values["source_file"] = parsed.source_file or file_name
    values["content_hash"] = content_hash
    values["review_flag"] = 1 if needs_review else 0
    try:
        tx = insert_transaction(conn, values)
    except sqlite3.IntegrityError:
        return _quarantine(
            conn,
            artifact_id,
            file_name,
            "Duplicate payment reference, already in ledger",
            parse,
            parsed.confidence,
            stages,
        )

    final = "review" if needs_review else "committed"
    stages.append(final)
    conn.execute(
        "UPDATE ingest_artifacts SET stage = ?, confidence = ?, parse_result_json = ?, "
        "transaction_id = ?, updated_at = ? WHERE id = ?",
        (
            final,
            parsed.confidence,
            json.dumps(parse, default=str),
            tx["id"],
            now_iso(),
            artifact_id,
        ),
    )
    return {
        "artifact": row_dict(
            conn.execute("SELECT * FROM ingest_artifacts WHERE id = ?", (artifact_id,)).fetchone()
        ),
        "transaction": tx,
        "quarantined": None,
        "stages": stages,
    }


def list_artifacts(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM ingest_artifacts ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def delete_artifact(conn: sqlite3.Connection, artifact_id: str) -> bool:
    """Remove an inbox entry and its quarantine record. The committed ledger row stays."""
    row = conn.execute(
        "SELECT file_name FROM ingest_artifacts WHERE id = ?", (artifact_id,)
    ).fetchone()
    if row is None:
        return False
    conn.execute("DELETE FROM quarantined_parses WHERE source_file = ?", (row["file_name"],))
    conn.execute("DELETE FROM ingest_artifacts WHERE id = ?", (artifact_id,))
    return True

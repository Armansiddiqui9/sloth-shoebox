from __future__ import annotations

from sloth_shoebox import ledger
from sloth_shoebox.ingest import ingest
from sloth_shoebox.seed import seed


def test_seed_is_deterministic_and_idempotent(settings):
    ledger.init_db(settings.db_path)
    with ledger.session(settings.db_path) as c:
        assert seed(c) == 28
        first = [
            r["payment_ref"] for r in ledger.list_transactions(c, ledger.TxFilter(status="all"))
        ]
        seed(c)
        again = [
            r["payment_ref"] for r in ledger.list_transactions(c, ledger.TxFilter(status="all"))
        ]
        assert first == again and len(first) == 28


def test_cascade_delete_removes_splits(conn):
    tx = ledger.list_transactions(conn, ledger.TxFilter(q="bookmyshow"))[0]
    assert len(ledger.splits_for(conn, tx["id"])) == 3
    ledger.delete_transaction(conn, tx["id"])
    assert conn.execute("SELECT COUNT(*) FROM splits").fetchone()[0] == 0


def test_duplicate_payment_ref_is_quarantined_not_a_crash(conn):
    existing = ledger.list_transactions(conn, ledger.TxFilter(), 1)[0]
    parse = {
        "vendor_raw": "X",
        "amount": 10,
        "datetime_local": "2026-10-22T10:00:00",
        "category": "food",
        "payment_ref": existing["payment_ref"],
    }
    out = ingest(conn, file_name="x.png", file_type="image", content_hash="sha256:new", parse=parse)
    assert out["artifact"]["stage"] == "quarantined"
    assert "payment reference" in out["quarantined"]["reason"]


def test_low_confidence_goes_to_review(conn):
    parse = {
        "vendor_raw": "Corner Shop",
        "amount": 10,
        "datetime_local": "2026-10-22T10:00:00",
        "category": "food",
        "confidence": 0.5,
    }
    out = ingest(conn, file_name="y.png", file_type="image", content_hash="sha256:y", parse=parse)
    assert out["artifact"]["stage"] == "review"
    assert out["transaction"]["review_flag"] == 1


def test_failed_payment_is_committed_but_flagged_by_status(conn):
    parse = {
        "vendor_raw": "Corner Shop",
        "amount": 10,
        "datetime_local": "2026-10-22T10:00:00",
        "category": "food",
        "status": "failed",
    }
    out = ingest(conn, file_name="z.png", file_type="image", content_hash="sha256:z", parse=parse)
    assert out["transaction"]["status"] == "failed"

from __future__ import annotations

from sloth_shoebox.digest import add_months, compute_digest, default_month, r2


def test_helpers():
    assert add_months("2026-01", -1) == "2025-12"
    assert add_months("2026-11", 3) == "2027-02"
    assert r2(2.675) == 2.68  # half up, like the original JavaScript
    assert default_month([]) != ""


def test_october_digest(rows):
    d = compute_digest(rows, "2026-10")
    assert d["transaction_count"] == 15
    assert d["total_spend"] == 8969.5  # 15 successful October payments
    assert d["failed_count"] == 1  # the failed Zomato payment
    assert d["review_count"] == 1  # the low-confidence petrol receipt
    assert sum(c["amount"] for c in d["by_category"]) == d["total_spend"]
    assert [m["month"] for m in d["previous_months"]] == ["2026-09", "2026-08", "2026-07"]
    assert d["previous_months"][2]["total_spend"] == 0


def test_failed_rows_never_count_as_spend(rows):
    aug = compute_digest(rows, "2026-08")
    assert aug["failed_count"] == 1  # reversed Hotstar
    assert all(c["category"] != "subscriptions" for c in aug["by_category"])


def test_delta_uses_months_that_had_spend():
    rows = [
        {
            "datetime_local": "2026-10-01T10:00:00",
            "amount": 300,
            "category": "food",
            "vendor_normalized": "a",
            "vendor_raw": "A",
            "payment_app": "gpay",
            "status": "success",
            "review_flag": 0,
        },
        {
            "datetime_local": "2026-09-01T10:00:00",
            "amount": 100,
            "category": "food",
            "vendor_normalized": "a",
            "vendor_raw": "A",
            "payment_app": "gpay",
            "status": "success",
            "review_flag": 0,
        },
    ]
    food = compute_digest(rows, "2026-10")["category_deltas"][0]
    assert food["trailing_avg"] == 100  # one active month, not divided by three
    assert food["delta_pct"] == 200


def test_new_category_has_no_delta():
    rows = [
        {
            "datetime_local": "2026-10-01T10:00:00",
            "amount": 50,
            "category": "books",
            "vendor_normalized": "b",
            "vendor_raw": "B",
            "payment_app": None,
            "status": "success",
            "review_flag": 0,
        }
    ]
    d = compute_digest(rows, "2026-10")
    assert d["category_deltas"][0]["delta_pct"] is None
    assert d["payment_apps"][0]["app"] == "unknown"

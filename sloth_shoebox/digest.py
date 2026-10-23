"""Monthly digest: totals, categories, merchants, and deltas vs the trailing average."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from typing import Any

TRAILING_MONTHS = 3


def r2(n: float) -> float:
    """Round half up to 2 places (not banker's rounding), so money adds up the way people expect."""
    return math.floor(n * 100 + 0.5) / 100


def month_key(dt: str) -> str:
    return dt[:7]


def add_months(ym: str, delta: int) -> str:
    year, month = int(ym[:4]), int(ym[5:7])
    index = year * 12 + (month - 1) + delta
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def default_month(rows: list[dict[str, Any]]) -> str:
    """Latest month in the ledger, or the current month when it is empty."""
    if not rows:
        return date.today().strftime("%Y-%m")
    return month_key(max(r["datetime_local"] for r in rows))


def compute_digest(rows: list[dict[str, Any]], month: str) -> dict[str, Any]:
    """Only successful payments count toward spend. Failed and reversed rows are
    reported separately as failed_count."""
    ok = [r for r in rows if r["status"] == "success"]
    this_month = [r for r in ok if month_key(r["datetime_local"]) == month]
    total = r2(sum(r["amount"] for r in this_month))

    by_cat: dict[str, dict[str, float]] = defaultdict(lambda: {"amount": 0.0, "count": 0})
    by_merchant: dict[str, dict[str, Any]] = {}
    by_app: dict[str, dict[str, float]] = defaultdict(lambda: {"amount": 0.0, "count": 0})
    for r in this_month:
        cat = by_cat[r["category"]]
        cat["amount"] = r2(cat["amount"] + r["amount"])
        cat["count"] += 1
        merchant = by_merchant.setdefault(
            r["vendor_normalized"],
            {
                "vendor_raw": r.get("vendor_raw") or r["vendor_normalized"],
                "amount": 0.0,
                "count": 0,
            },
        )
        merchant["amount"] = r2(merchant["amount"] + r["amount"])
        merchant["count"] += 1
        app = by_app[r.get("payment_app") or "unknown"]
        app["amount"] = r2(app["amount"] + r["amount"])
        app["count"] += 1

    by_category = sorted(
        (
            {
                "category": c,
                "amount": v["amount"],
                "count": int(v["count"]),
                "pct": r2(v["amount"] / total * 100) if total > 0 else 0,
            }
            for c, v in by_cat.items()
        ),
        key=lambda x: -x["amount"],
    )
    top_merchants = sorted(
        (
            {
                "vendor_normalized": k,
                "vendor_raw": v["vendor_raw"],
                "amount": v["amount"],
                "count": v["count"],
            }
            for k, v in by_merchant.items()
        ),
        key=lambda x: -x["amount"],
    )[:5]
    payment_apps = sorted(
        ({"app": a, "amount": v["amount"], "count": int(v["count"])} for a, v in by_app.items()),
        key=lambda x: -x["amount"],
    )

    # spend per (month, category) over the whole ledger, computed once
    spend: dict[tuple[str, str], float] = defaultdict(float)
    for r in ok:
        spend[(month_key(r["datetime_local"]), r["category"])] += r["amount"]

    previous = [add_months(month, -i) for i in range(1, TRAILING_MONTHS + 1)]
    previous_months = [
        {"month": m, "total_spend": r2(sum(v for (mm, _), v in spend.items() if mm == m))}
        for m in previous
    ]

    categories = {r["category"] for r in this_month}
    categories |= {c for (m, c) in spend if m in previous}
    deltas = []
    for category in categories:
        current = next((c["amount"] for c in by_category if c["category"] == category), 0.0)
        monthly = [spend.get((m, category), 0.0) for m in previous]
        active = sum(1 for v in monthly if v > 0)
        # average over the months that had spend; over all of them when none did
        trailing = r2(sum(monthly) / (active or TRAILING_MONTHS))
        delta_pct = r2((current - trailing) / trailing * 100) if trailing > 0 else None
        deltas.append(
            {
                "category": category,
                "this_month": current,
                "trailing_avg": trailing,
                "delta_pct": delta_pct,
            }
        )
    deltas.sort(key=lambda d: -abs(d["delta_pct"] or 0))

    in_month = [r for r in rows if month_key(r["datetime_local"]) == month]
    return {
        "month": month,
        "total_spend": total,
        "transaction_count": len(this_month),
        "by_category": by_category,
        "top_merchants": top_merchants,
        "payment_apps": payment_apps,
        "previous_months": previous_months,
        "category_deltas": deltas,
        "failed_count": sum(1 for r in in_month if r["status"] != "success"),
        "review_count": sum(1 for r in in_month if r["review_flag"] == 1),
    }

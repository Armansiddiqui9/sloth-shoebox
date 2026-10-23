"""Offline questions over the ledger.

If a local Ollama model is running it answers from the 100 most recent rows.
If not, a small rule engine answers the common questions deterministically,
so the Query tab never depends on a model being installed.
"""

from __future__ import annotations

import re
import sqlite3
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from .categorize import CATEGORY_KEYS, category_label
from .config import Settings
from .digest import add_months, compute_digest, month_key, r2
from .ollama import OllamaError, chat

SYSTEM_PROMPT = """You are the Sloth Shoebox offline query engine.
You answer questions about the user's local expense ledger.

Rules:
- Use ONLY the provided ledger data to answer.
- Be concise: 1 to 4 sentences unless the user explicitly asks for a list.
- Format money as Indian rupees, like ₹1,250 or ₹42.
- Failed and reversed payments do not count as spend.
- If the data cannot answer the question, say so directly. Never invent data.
- For a merchant question, check both vendorNormalized and vendorRaw, ignoring case."""

CATEGORY_WORDS: dict[str, tuple[str, ...]] = {
    "food": ("food", "eating", "restaurant", "dining", "meals", "takeaway"),
    "groceries": ("grocery", "groceries"),
    "travel": ("travel", "commute", "cab", "cabs", "transport", "fuel", "petrol"),
    "utilities": ("utilities", "utility", "electricity", "recharge", "phone bill"),
    "subscriptions": ("subscription", "subscriptions", "streaming"),
    "shopping": ("shopping",),
    "books": ("book", "books"),
    "health": ("health", "medicine", "medical", "pharmacy"),
    "entertainment": ("entertainment", "movie", "movies"),
    "rent": ("rent", "hostel", "mess"),
}
_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "ten": 10}
_MONTHS = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]


def inr(amount: float) -> str:
    """₹ with Indian digit grouping: ₹1,25,000. Whole rupees drop the decimals."""
    sign = "-" if amount < 0 else ""
    whole, frac = f"{abs(r2(amount)):.2f}".split(".")
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while head:
        groups.insert(0, head[-2:])
        head = head[:-2]
    grouped = ",".join([*groups, tail])
    return f"₹{sign}{grouped}" + ("" if frac == "00" else f".{frac}")


def _month_name(ym: str) -> str:
    return datetime(int(ym[:4]), int(ym[5:7]), 1).strftime("%B %Y")


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


# ---------------------------------------------------------------------------
# rule engine
# ---------------------------------------------------------------------------

Rows = list[dict[str, Any]]


def _anchor(rows: Rows) -> date:
    """'Today' for relative phrases is the newest payment in the ledger."""
    return date.fromisoformat(max(r["datetime_local"] for r in rows)[:10])


def _period(q: str, anchor: date) -> tuple[date, date, str] | None:
    ym = anchor.strftime("%Y-%m")
    if "last week" in q or "past week" in q or "this week" in q:
        return anchor - timedelta(days=6), anchor, "in the last 7 days"
    for label, month in (("last month", add_months(ym, -1)), ("this month", ym)):
        if label in q:
            return _month_bounds(month, f"in {_month_name(month)}")
    for index, name in enumerate(_MONTHS, start=1):
        if re.search(rf"\b{name}\b", q):
            return _month_bounds(
                f"{anchor.year}-{index:02d}", f"in {name.capitalize()} {anchor.year}"
            )
    return None


def _month_bounds(month: str, label: str) -> tuple[date, date, str]:
    start = date(int(month[:4]), int(month[5:7]), 1)
    end = date.fromisoformat(add_months(month, 1) + "-01") - timedelta(days=1)
    return start, end, label


def _in_period(rows: Rows, period: tuple[date, date, str] | None) -> Rows:
    if period is None:
        return rows
    start, end, _ = period
    return [r for r in rows if start <= date.fromisoformat(r["datetime_local"][:10]) <= end]


def _category_in(q: str) -> str | None:
    for key, words in CATEGORY_WORDS.items():
        if any(re.search(rf"\b{re.escape(w)}\b", q) for w in words):
            return key
    return None


def _merchant_in(q: str, rows: Rows) -> str | None:
    names = {r["vendor_normalized"] for r in rows}
    for name in sorted(names, key=len, reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", q):
            return name
    return None


def _top_n(q: str, default: int) -> int:
    match = re.search(r"\b(\d+)\b", q)
    if match:
        return max(1, min(int(match.group(1)), 10))
    for word, n in _NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", q):
            return n
    return default


def _span(period: tuple[date, date, str] | None, count: int) -> str:
    return period[2] if period else f"across all {_plural(count, 'payment')} in the ledger"


def rules_answer(all_rows: Rows, question: str) -> str:
    ok = [r for r in all_rows if r["status"] == "success"]
    if not ok:
        return (
            "The ledger has no successful payments yet. Send an artifact through the inbox first."
        )

    q = question.lower()
    anchor = _anchor(ok)
    this_month = anchor.strftime("%Y-%m")
    period = _period(q, anchor)
    scoped = _in_period(ok, period)
    span = _span(period, len(scoped))

    if "subscription" in q and not re.search(r"how much|more|less|usual", q):
        subs = [r for r in ok if r["category"] == "subscriptions"]
        if not subs:
            return "No subscription payments in the ledger."
        latest: dict[str, dict[str, Any]] = {}
        for r in sorted(subs, key=lambda r: r["datetime_local"]):
            latest[r["vendor_normalized"]] = r
        listed = ", ".join(
            f"{r['vendor_raw'] or name} ({inr(r['amount'])})"
            for name, r in sorted(latest.items(), key=lambda kv: -kv[1]["amount"])
        )
        monthly = r2(sum(r["amount"] for r in latest.values()))
        return f"You pay for {listed}. That is about {inr(monthly)} per month at the latest rates."

    if re.search(r"compare|\bvs\b|versus", q):
        prev = add_months(this_month, -1)
        cur = r2(sum(r["amount"] for r in ok if month_key(r["datetime_local"]) == this_month))
        old = r2(sum(r["amount"] for r in ok if month_key(r["datetime_local"]) == prev))
        if old == 0:
            return f"{_month_name(this_month)} is {inr(cur)}. There is no spend in {_month_name(prev)} to compare."
        change = r2((cur - old) / old * 100)
        direction = "up" if change > 0 else "down" if change < 0 else "flat"
        return (
            f"{_month_name(this_month)} is {inr(cur)} against {inr(old)} in {_month_name(prev)}: "
            f"{direction} {abs(change):g}% ({inr(abs(r2(cur - old)))}). "
            "The newest month may be incomplete."
        )

    if re.search(r"\btop\b", q) and re.search(r"merchant|vendor|shop|place", q):
        totals: dict[str, list[Any]] = defaultdict(lambda: [0.0, 0, ""])
        for r in scoped:
            entry = totals[r["vendor_normalized"]]
            entry[0] += r["amount"]
            entry[1] += 1
            entry[2] = r["vendor_raw"] or r["vendor_normalized"]
        ranked = sorted(totals.values(), key=lambda e: -e[0])[: _top_n(q, 5)]
        if not ranked:
            return f"No payments {span}."
        lines = ", ".join(f"{e[2]} {inr(e[0])} ({_plural(e[1], 'payment')})" for e in ranked)
        return f"Top merchants {span}: {lines}."

    category = _category_in(q)

    if (
        re.search(r"biggest|largest|highest|most", q)
        and re.search(r"categor|expense|spend", q)
        and not category
    ):
        totals_c: dict[str, float] = defaultdict(float)
        for r in scoped:
            totals_c[r["category"]] += r["amount"]
        if not totals_c:
            return f"No payments {span}."
        name, amount = max(totals_c.items(), key=lambda kv: kv[1])
        share = r2(amount / sum(totals_c.values()) * 100)
        return f"{category_label(name)} is the biggest category {span}: {inr(amount)}, {share:g}% of spend."

    if category and re.search(r"more|less|usual|average|normal|trend", q):
        digest = compute_digest(all_rows, this_month)
        entry = next((d for d in digest["category_deltas"] if d["category"] == category), None)
        label = category_label(category).lower()
        if entry is None or (entry["this_month"] == 0 and entry["trailing_avg"] == 0):
            return f"No {label} spend in {_month_name(this_month)} or the three months before."
        if entry["delta_pct"] is None:
            return (
                f"{_month_name(this_month)} {label} spend is {inr(entry['this_month'])}. "
                "There was none in the previous three months, so there is no usual to compare with."
            )
        direction = "above" if entry["delta_pct"] > 0 else "below"
        return (
            f"{category_label(category)} is {inr(entry['this_month'])} in {_month_name(this_month)}, "
            f"{abs(entry['delta_pct']):g}% {direction} your usual {inr(entry['trailing_avg'])} "
            "(average of the three months before)."
        )

    merchant = _merchant_in(q, ok)
    if merchant:
        hits = [r for r in scoped if r["vendor_normalized"] == merchant]
        total = r2(sum(r["amount"] for r in hits))
        return f"You spent {inr(total)} at {merchant.title()} {span} ({_plural(len(hits), 'payment')})."

    if category:
        hits = [r for r in scoped if r["category"] == category]
        total = r2(sum(r["amount"] for r in hits))
        return f"You spent {inr(total)} on {category_label(category).lower()} {span} ({_plural(len(hits), 'payment')})."

    if re.search(r"total|how much|spend|spent", q):
        total = r2(sum(r["amount"] for r in scoped))
        return f"Total spend {span} is {inr(total)} across {_plural(len(scoped), 'payment')}."

    by_cat: dict[str, float] = defaultdict(float)
    for r in ok:
        by_cat[r["category"]] += r["amount"]
    top = ", ".join(
        f"{category_label(c)} {inr(a)}"
        for c, a in sorted(by_cat.items(), key=lambda kv: -kv[1])[:3]
    )
    return (
        "I can answer questions about spend by category, merchant or month, top merchants, "
        f"subscriptions, and how a month compares with your usual. Overall: {inr(r2(sum(by_cat.values())))} "
        f"across {_plural(len(ok), 'payment')}. Top categories: {top}."
    )


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def _context(rows: Rows) -> str:
    lines = [
        f"{r['datetime_local']} | {r['vendor_raw'] or r['vendor_normalized']} "
        f"({r['vendor_normalized']}) | ₹{r['amount']:.2f} | {r['category']} | "
        f"via {r['payment_app'] or 'unknown'} | status: {r['status']}"
        for r in rows
    ]
    return f"LEDGER (most recent {len(rows)} transactions, oldest first):\n" + "\n".join(lines)


def answer(
    conn: sqlite3.Connection,
    settings: Settings,
    question: str,
    *,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    cols = "datetime_local, vendor_raw, vendor_normalized, amount, category, payment_app, status, review_flag"
    rows = [
        dict(r) for r in conn.execute(f"SELECT {cols} FROM transactions ORDER BY datetime_local")
    ]

    engine, text = "rules", ""
    try:
        text = chat(
            settings.ollama_url,
            settings.text_model,
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Today's date: {date.today().isoformat()}\n\n"
                    f"{_context(rows[-100:])}\n\nQuestion: {question}",
                },
            ],
            timeout=60.0,
            transport=transport,
        )
        engine = f"ollama:{settings.text_model}"
    except OllamaError:
        text = rules_answer(rows, question)

    return {
        "answer": text,
        "engine": engine,
        "query_ms": round((time.perf_counter() - started) * 1000),
    }


__all__ = ["CATEGORY_KEYS", "answer", "inr", "rules_answer"]

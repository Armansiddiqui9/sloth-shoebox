"""CSV export of the ledger."""

from __future__ import annotations

import csv
import io
from typing import Any

HEADER = (
    "date",
    "vendor",
    "category",
    "amount",
    "currency",
    "gst",
    "payment_app",
    "payment_ref",
    "status",
    "source_file",
)


def to_csv(rows: list[dict[str, Any]]) -> str:
    """UTF-8 with a BOM so Excel shows ₹ and em dashes correctly."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(HEADER)
    for r in rows:
        writer.writerow(
            [
                r["datetime_local"],
                r["vendor_raw"] or r["vendor_normalized"],
                r["category"],
                f"{r['amount']:.2f}",
                r["currency"],
                "" if r["gst_amount"] is None else f"{r['gst_amount']:.2f}",
                r["payment_app"] or "",
                r["payment_ref"] or "",
                r["status"],
                r["source_file"] or "",
            ]
        )
    return "\ufeff" + out.getvalue()

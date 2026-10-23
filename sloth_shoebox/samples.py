"""The five sample artifacts shipped with the demo, and their expected parses.

A vision model would normally derive these from pixels. The demo ships the
expected output beside each image so the pipeline is deterministic.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import PACKAGE_DIR

SAMPLES_DIR = PACKAGE_DIR / "static" / "samples"


@dataclass(frozen=True)
class Sample:
    id: str
    file: str  # file name inside static/samples
    source_file: str  # the name the ledger records
    label: str
    kind: str  # upi_screenshot | receipt_photo | pdf_bill
    content_hash: str
    parse: dict[str, Any]

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "url": f"/static/samples/{self.file}",
        }


SAMPLES: tuple[Sample, ...] = (
    Sample(
        id="swiggy",
        file="upi-swiggy.webp",
        source_file="upi-swiggy.png",
        label="GPay, Swiggy",
        kind="upi_screenshot",
        content_hash="phash:9f2a4c7e1b08",
        parse={
            "vendor_raw": "Swiggy",
            "vendor_normalized": "swiggy",
            "amount": 285.5,
            "datetime_local": "2026-10-19T21:14:00",
            "category": "food",
            "payment_ref": "UPI/519812345678/Payment/000421",
            "payment_app": "gpay",
            "doc_type": "upi_screenshot",
            "status": "success",
            "confidence": 0.96,
            "source_file": "upi-swiggy.png",
        },
    ),
    Sample(
        id="zomato",
        file="upi-zomato.webp",
        source_file="upi-zomato.png",
        label="PhonePe, Zomato",
        kind="upi_screenshot",
        content_hash="phash:7a3c5d9e2f14",
        parse={
            "vendor_raw": "Zomato",
            "vendor_normalized": "zomato",
            "amount": 412.0,
            "datetime_local": "2026-10-15T13:32:00",
            "category": "food",
            "payment_ref": "UPI/428765432109/Payment/000422",
            "payment_app": "phonepe",
            "doc_type": "upi_screenshot",
            "status": "success",
            "confidence": 0.95,
            "source_file": "upi-zomato.png",
        },
    ),
    Sample(
        id="blinkit",
        file="upi-blinkit.webp",
        source_file="upi-blinkit.png",
        label="Paytm, Blinkit",
        kind="upi_screenshot",
        content_hash="phash:5e8b1d4f6a22",
        parse={
            "vendor_raw": "Blinkit",
            "vendor_normalized": "blinkit",
            "amount": 648.75,
            "datetime_local": "2026-10-18T19:45:00",
            "category": "groceries",
            "payment_ref": "UPI/365478921045/Payment/000423",
            "payment_app": "paytm",
            "doc_type": "upi_screenshot",
            "status": "success",
            "confidence": 0.95,
            "source_file": "upi-blinkit.png",
        },
    ),
    Sample(
        id="cafe",
        file="receipt-cafe.webp",
        source_file="receipt-cafe.jpg",
        label="Paper receipt, cafe",
        kind="receipt_photo",
        content_hash="phash:3d7a9c2e5b18",
        parse={
            "vendor_raw": "Brew & Bytes Cafe",
            "vendor_normalized": "brew & bytes cafe",
            "amount": 420.0,
            "datetime_local": "2026-10-12T16:20:00",
            "category": "food",
            "doc_type": "receipt_photo",
            "status": "success",
            "gst_amount": 20.0,
            "confidence": 0.88,
            "source_file": "receipt-cafe.jpg",
        },
    ),
    Sample(
        id="failed",
        file="upi-failed.webp",
        source_file="upi-failed.png",
        label="GPay, failed payment",
        kind="upi_screenshot",
        content_hash="phash:1f4b8a6d3c27",
        # "uncategorized" is not a known category, so this one is quarantined
        # on purpose: it demonstrates the schema-validation failure path.
        parse={
            "vendor_raw": "Unknown Merchant",
            "vendor_normalized": "unknown merchant",
            "amount": 1200.0,
            "datetime_local": "2026-10-10T11:05:00",
            "category": "uncategorized",
            "payment_app": "gpay",
            "doc_type": "upi_screenshot",
            "status": "failed",
            "confidence": 0.92,
            "source_file": "upi-failed.png",
        },
    ),
)

SAMPLES_BY_ID = {s.id: s for s in SAMPLES}


@lru_cache(maxsize=1)
def _file_hashes() -> dict[str, Sample]:
    found: dict[str, Sample] = {}
    for sample in SAMPLES:
        path: Path = SAMPLES_DIR / sample.file
        if path.exists():
            found[hashlib.sha256(path.read_bytes()).hexdigest()] = sample
    return found


def sample_for_bytes(data: bytes) -> Sample | None:
    """Recognise a dropped file that is byte-identical to a shipped sample."""
    return _file_hashes().get(hashlib.sha256(data).hexdigest())

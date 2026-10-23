"""Stage 2 of the pipeline: turn an artifact into a candidate transaction.

Three sources, in order of preference:
  1. a shipped sample (byte-identical file): its expected parse;
  2. SLOTH_PARSER=ollama: the local vision model, with one re-ask on bad JSON;
  3. otherwise a deterministic stand-in so the demo works with no model at all.
"""

from __future__ import annotations

import base64
import json
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from pydantic import ValidationError

from .config import PACKAGE_DIR, Settings
from .ollama import OllamaError, chat
from .schema import ParsedTransaction

PROMPT_PATH = PACKAGE_DIR / "prompts" / "parse_transaction.txt"

_STAND_IN_MERCHANTS = (
    ("Swiggy", "swiggy", "food"),
    ("Zomato", "zomato", "food"),
    ("Blinkit", "blinkit", "groceries"),
    ("Zepto", "zepto", "groceries"),
    ("BigBasket", "bigbasket", "groceries"),
    ("Airtel", "airtel", "utilities"),
    ("Ola Cabs", "ola", "travel"),
    ("Amazon India", "amazon", "shopping"),
    ("Netflix", "netflix", "subscriptions"),
    ("Apollo Pharmacy", "apollo pharmacy", "health"),
)
_APPS = ("gpay", "phonepe", "paytm", "upi")


@dataclass
class ParseAttempt:
    parse: dict[str, Any] | None
    raw: str | None = None
    error: str | None = None


def stand_in_parse(
    file_name: str, content_hash: str, now: datetime | None = None
) -> dict[str, Any]:
    """Plausible, repeatable output for a file the demo has never seen."""
    rng = random.Random(content_hash)
    raw, norm, category = rng.choice(_STAND_IN_MERCHANTS)
    amount = round(rng.uniform(20, 1520), 2)
    when = (now or datetime.now()).replace(second=0, microsecond=0)
    return {
        "vendor_raw": raw,
        "vendor_normalized": norm,
        "amount": amount,
        "currency": "INR",
        "datetime_local": when.isoformat(timespec="seconds"),
        "category": category,
        "payment_ref": f"UPI/{rng.randrange(10**11, 10**12)}/Payment/{rng.randrange(10**6):06d}",
        "payment_app": rng.choice(_APPS),
        "doc_type": "pdf_bill" if file_name.lower().endswith(".pdf") else "upi_screenshot",
        "status": "failed" if rng.random() < 0.1 else "success",
        "gst_amount": round(amount * 0.05, 2) if category in {"groceries", "shopping"} else None,
        "confidence": round(rng.uniform(0.55, 0.99), 2),
        "source_file": file_name,
    }


def _extract_json(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in model output")
    value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("model output is not a JSON object")
    return value


def vlm_parse(
    settings: Settings,
    file_name: str,
    data: bytes,
    *,
    transport: httpx.BaseTransport | None = None,
) -> ParseAttempt:
    """Ask the local vision model; one re-ask on malformed or invalid output."""
    if file_name.lower().endswith(".pdf"):
        return ParseAttempt(None, error="PDF bills need the OCR assist path (not built yet)")
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    image = base64.b64encode(data).decode()
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    raw = ""
    problem = ""
    for attempt in range(2):
        try:
            raw = chat(
                settings.ollama_url,
                settings.vlm_model,
                messages,
                images=[image],
                json_mode=True,
                timeout=180.0,
                transport=transport,
            )
            candidate = _extract_json(raw)
            candidate.setdefault("source_file", file_name)
            ParsedTransaction.model_validate(candidate)
            return ParseAttempt(candidate, raw)
        except OllamaError as exc:
            return ParseAttempt(None, raw or None, f"Local model unavailable: {exc}")
        except (ValueError, ValidationError) as exc:
            problem = str(exc).splitlines()[0]
            messages = [
                *messages,
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": f"That failed validation ({problem}). Return only the corrected JSON.",
                },
            ]
            if attempt == 1:
                break
    return ParseAttempt(None, raw, f"Model output failed validation after re-ask: {problem}")

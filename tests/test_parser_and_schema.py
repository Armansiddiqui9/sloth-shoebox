from __future__ import annotations

import json

import httpx
import pytest
from pydantic import ValidationError

from sloth_shoebox.categorize import guess_category, normalize_vendor
from sloth_shoebox.config import Settings
from sloth_shoebox.parser import stand_in_parse, vlm_parse
from sloth_shoebox.schema import ParsedTransaction

GOOD = {
    "vendor_raw": "Swiggy Instamart",
    "amount": 248,
    "datetime_local": "2026-10-21T21:14:05",
    "category": "food",
    "confidence": 0.9,
}


def test_vendor_normalisation():
    assert normalize_vendor("Swiggy Instamart") == "swiggy"
    assert normalize_vendor("Ola Cabs") == "ola"
    assert normalize_vendor("Cola Corner") != "ola"  # whole words only
    assert normalize_vendor("Corner Shop — Block C") == "corner shop"
    assert guess_category("zomato") == "food"


def test_parse_contract_fills_vendor_and_rejects_nonsense():
    parsed = ParsedTransaction.model_validate(GOOD)
    assert parsed.vendor_normalized == "swiggy"
    for patch in (
        {"amount": 0},
        {"amount": -5},
        {"amount": 1e12},
        {"category": "misc"},
        {"datetime_local": "yesterday"},
        {"datetime_local": "1850-01-01T00:00:00"},
        {"confidence": 1.5},
        {"vendor_raw": None},
    ):
        with pytest.raises(ValidationError):
            ParsedTransaction.model_validate({**GOOD, **patch})


def test_stand_in_parse_is_repeatable_and_valid():
    a = stand_in_parse("x.png", "sha256:abc")
    assert a == stand_in_parse("x.png", "sha256:abc")
    ParsedTransaction.model_validate(a)
    assert stand_in_parse("bill.pdf", "sha256:abc")["doc_type"] == "pdf_bill"


def _fake(replies):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        return httpx.Response(
            200, json={"message": {"content": replies[min(len(calls), len(replies)) - 1]}}
        )

    return httpx.MockTransport(handler), calls


def test_vlm_parse_happy_path():
    transport, calls = _fake(["```json\n" + json.dumps(GOOD) + "\n```"])
    out = vlm_parse(Settings(), "a.png", b"img", transport=transport)
    assert out.parse["amount"] == 248
    assert calls[0]["messages"][0]["images"] and calls[0]["format"] == "json"


def test_vlm_parse_reasks_once_then_succeeds():
    transport, calls = _fake(["not json", json.dumps(GOOD)])
    out = vlm_parse(Settings(), "a.png", b"img", transport=transport)
    assert out.parse is not None and len(calls) == 2


def test_vlm_parse_gives_up_after_one_reask():
    transport, calls = _fake(["nope", "still nope"])
    out = vlm_parse(Settings(), "a.png", b"img", transport=transport)
    assert out.parse is None and len(calls) == 2 and "re-ask" in out.error


def test_vlm_parse_reports_missing_runtime():
    out = vlm_parse(Settings(ollama_url="http://127.0.0.1:9"), "a.png", b"img")
    assert out.parse is None and "unavailable" in out.error


def test_pdf_is_not_sent_to_the_vision_model():
    out = vlm_parse(Settings(), "bill.pdf", b"%PDF")
    assert out.parse is None and "PDF" in out.error

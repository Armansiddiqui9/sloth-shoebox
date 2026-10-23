"""Categories and merchant normalisation (rule based, no model needed)."""

from __future__ import annotations

import re
from typing import Literal, get_args

Category = Literal[
    "food",
    "groceries",
    "travel",
    "utilities",
    "subscriptions",
    "shopping",
    "books",
    "health",
    "entertainment",
    "rent",
]

CATEGORY_KEYS: tuple[str, ...] = get_args(Category)

CATEGORY_LABELS: dict[str, str] = {key: key.capitalize() for key in CATEGORY_KEYS}


def category_label(key: str) -> str:
    return CATEGORY_LABELS.get(key, key.capitalize())


# (aliases found in raw vendor text, canonical name, category)
_MERCHANTS: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("swiggy",), "swiggy", "food"),
    (("zomato",), "zomato", "food"),
    (("chai point",), "chai point", "food"),
    (("canteen",), "college canteen", "food"),
    (("blinkit",), "blinkit", "groceries"),
    (("zepto",), "zepto", "groceries"),
    (("bigbasket",), "bigbasket", "groceries"),
    (("dmart",), "dmart", "groceries"),
    (("ola",), "ola", "travel"),
    (("rapido",), "rapido", "travel"),
    (("irctc",), "irctc", "travel"),
    (("indian oil",), "indian oil", "travel"),
    (("airtel",), "airtel", "utilities"),
    (("jio",), "jio", "utilities"),
    (("bses",), "bses rajdhani", "utilities"),
    (("netflix",), "netflix", "subscriptions"),
    (("spotify",), "spotify", "subscriptions"),
    (("hotstar",), "hotstar", "subscriptions"),
    (("amazon",), "amazon", "shopping"),
    (("flipkart",), "flipkart", "shopping"),
    (("apollo",), "apollo pharmacy", "health"),
    (("1mg",), "tata 1mg", "health"),
    (("bookmyshow",), "bookmyshow", "entertainment"),
    (("hostel mess",), "hostel mess", "rent"),
)

_DASHES = re.compile(r"\s+[—–-]\s+")
_SPACES = re.compile(r"\s+")


def _has_alias(text: str, alias: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", text) is not None


def normalize_vendor(raw: str) -> str:
    """Collapse 'Swiggy Instamart' / 'Ola Cabs' style names to one merchant key."""
    text = _SPACES.sub(" ", raw.strip().lower())
    for aliases, canonical, _ in _MERCHANTS:
        if any(_has_alias(text, alias) for alias in aliases):
            return canonical
    return _DASHES.split(text)[0].strip()


def guess_category(normalized_vendor: str) -> str | None:
    for _, canonical, category in _MERCHANTS:
        if canonical == normalized_vendor:
            return category
    return None

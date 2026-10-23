"""Pydantic contracts: the parse boundary and the HTTP request bodies."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .categorize import Category, normalize_vendor

Status = Literal["success", "failed", "reversed"]
DocType = Literal["upi_screenshot", "receipt_photo", "pdf_bill"]
MAX_AMOUNT = 10_000_000.0  # one crore rupees: anything above is a misread


class ParsedTransaction(BaseModel):
    """What the vision model must return. Anything else is quarantined."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    vendor_raw: str | None = None
    vendor_normalized: str = ""
    amount: float = Field(gt=0, le=MAX_AMOUNT)
    currency: str = "INR"
    datetime_local: str
    category: Category
    payment_ref: str | None = None
    payment_app: str | None = None
    doc_type: DocType = "upi_screenshot"
    status: Status = "success"
    gst_amount: float | None = Field(default=None, ge=0)
    confidence: float = Field(default=0.9, ge=0, le=1)
    source_file: str | None = None
    notes: str | None = None
    force_review: bool = False

    @field_validator("amount", "gst_amount")
    @classmethod
    def _finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("must be a finite number")
        return value

    @field_validator("datetime_local")
    @classmethod
    def _plausible_date(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("must be an ISO local datetime, e.g. 2026-10-19T21:14:00") from exc
        if not 2000 <= parsed.year <= 2100:
            raise ValueError("year is outside 2000-2100")
        return value

    @model_validator(mode="after")
    def _fill_vendor(self) -> ParsedTransaction:
        if not self.vendor_normalized and self.vendor_raw:
            self.vendor_normalized = normalize_vendor(self.vendor_raw)
        if not self.vendor_normalized:
            raise ValueError("vendor_normalized or vendor_raw is required")
        self.vendor_normalized = self.vendor_normalized.lower()
        if not self.vendor_raw:
            self.vendor_raw = self.vendor_normalized
        return self


class TransactionPatch(BaseModel):
    category: Category | None = None
    review_flag: Literal[0, 1] | None = None
    status: Status | None = None
    notes: str | None = None


class SplitShare(BaseModel):
    participant: str = Field(min_length=1)
    share: float = Field(ge=0)


class SplitsIn(BaseModel):
    transaction_id: str
    participants: list[SplitShare] = Field(min_length=1)


class SettleExpense(BaseModel):
    paid_by: str
    amount: float = Field(ge=0)
    split_among: list[str] = Field(min_length=1)


class SettleRequest(BaseModel):
    participants: list[str] = Field(min_length=1)
    expenses: list[SettleExpense] = []

    @model_validator(mode="after")
    def _known_people(self) -> SettleRequest:
        people = set(self.participants)
        if len(people) != len(self.participants):
            raise ValueError("participants must be unique")
        for expense in self.expenses:
            if expense.paid_by not in people or not set(expense.split_among) <= people:
                raise ValueError("expenses reference unknown participants")
        return self


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question is empty")
        return value


class SampleIngest(BaseModel):
    sample_id: str

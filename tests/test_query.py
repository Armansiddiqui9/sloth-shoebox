from __future__ import annotations

import httpx

from sloth_shoebox.config import Settings
from sloth_shoebox.query import answer, inr, rules_answer


def ask(rows, q):
    return rules_answer(rows, q)


def test_inr_formatting():
    assert inr(1250) == "₹1,250"
    assert inr(125000) == "₹1,25,000"
    assert inr(42.5) == "₹42.50"
    assert inr(-99) == "₹-99"


def test_category_this_month(rows):
    assert "₹726 on food in October 2026 (4 payments)" in ask(
        rows, "How much did I spend on food this month?"
    )


def test_merchant_last_week(rows):
    out = ask(rows, "How much did I spend on Swiggy last week?")
    assert "Swiggy" in out and "last 7 days" in out and "₹637" in out


def test_top_merchants_respects_n(rows):
    out = ask(rows, "What are my top 2 merchants?")
    assert out.count("payment") >= 2 and "Hostel Mess" in out
    assert "(1 payment)" in out


def test_subscriptions_list(rows):
    out = ask(rows, "Which subscriptions am I paying for?")
    assert "Netflix" in out and "Spotify" in out and "Hotstar" not in out  # reversed, so not paid


def test_month_compare(rows):
    out = ask(rows, "How does this month compare to last month?")
    assert "October 2026" in out and "September 2026" in out and "up" in out


def test_biggest_category_and_usual(rows):
    assert "biggest category" in ask(rows, "What's my biggest expense category?")
    out = ask(rows, "Am I spending more on travel than usual?")
    assert "above your usual" in out


def test_unknown_question_gets_a_helpful_summary(rows):
    assert "I can answer questions about" in ask(rows, "tell me a joke")


def test_empty_ledger():
    assert "no successful payments" in rules_answer([], "anything")


def test_ollama_answer_is_used_when_available(conn, settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        return httpx.Response(200, json={"message": {"content": "  ₹1 from the model.  "}})

    out = answer(conn, settings, "hi", transport=httpx.MockTransport(handler))
    assert out["answer"] == "₹1 from the model."
    assert out["engine"] == f"ollama:{settings.text_model}"


def test_ollama_failure_falls_back_to_rules(conn):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    out = answer(conn, Settings(), "total spend", transport=httpx.MockTransport(handler))
    assert out["engine"] == "rules"

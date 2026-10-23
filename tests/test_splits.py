from __future__ import annotations

from sloth_shoebox.schema import SettleRequest
from sloth_shoebox.splits import settle


def req(people, expenses):
    return SettleRequest.model_validate({"participants": people, "expenses": expenses})


def test_three_roommates():
    out = settle(
        req(
            ["Aman", "Priya", "Riya"],
            [
                {"paid_by": "Aman", "amount": 1200, "split_among": ["Aman", "Priya", "Riya"]},
                {"paid_by": "Priya", "amount": 640, "split_among": ["Aman", "Priya", "Riya"]},
                {"paid_by": "Riya", "amount": 480, "split_among": ["Priya", "Riya"]},
            ],
        )
    )
    assert out["total_spend"] == 2320
    nets = {p["participant"]: p["net"] for p in out["per_person"]}
    assert round(sum(nets.values()), 2) == 0
    assert {(s["from"], s["to"]) for s in out["settlements"]} == {
        ("Riya", "Aman"),
        ("Priya", "Aman"),
    }


def test_uneven_amounts_lose_no_paise():
    out = settle(
        req(["A", "B", "C"], [{"paid_by": "A", "amount": 100, "split_among": ["A", "B", "C"]}])
    )
    assert round(sum(p["share"] for p in out["per_person"]), 2) == 100
    assert round(sum(s["amount"] for s in out["settlements"]), 2) == round(
        -sum(p["net"] for p in out["per_person"] if p["net"] < 0), 2
    )


def test_settled_group_needs_no_transfers():
    out = settle(
        req(
            ["A", "B"],
            [
                {"paid_by": "A", "amount": 50, "split_among": ["A", "B"]},
                {"paid_by": "B", "amount": 50, "split_among": ["A", "B"]},
            ],
        )
    )
    assert out["settlements"] == []


def test_transfer_count_is_minimal_for_a_chain():
    out = settle(
        req(
            ["A", "B", "C"],
            [
                {"paid_by": "A", "amount": 100, "split_among": ["B"]},
                {"paid_by": "B", "amount": 100, "split_among": ["C"]},
            ],
        )
    )
    assert out["settlements"] == [{"from": "C", "to": "A", "amount": 100.0}]

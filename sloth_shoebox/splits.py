"""Roommate settlement: net balances, then the fewest transfers (greedy)."""

from __future__ import annotations

from .schema import SettleRequest


def settle(request: SettleRequest) -> dict[str, object]:
    """Work in paise so shares always add up to what was paid.

    When an amount does not divide evenly, the extra paise go to the first
    people in `split_among`, one each, instead of vanishing in rounding.
    """
    paid = dict.fromkeys(request.participants, 0)
    owed = dict.fromkeys(request.participants, 0)
    total = 0
    for expense in request.expenses:
        cents = round(expense.amount * 100)
        total += cents
        paid[expense.paid_by] += cents
        people = list(dict.fromkeys(expense.split_among))
        base, extra = divmod(cents, len(people))
        for index, person in enumerate(people):
            owed[person] += base + (1 if index < extra else 0)

    net = {p: paid[p] - owed[p] for p in request.participants}
    creditors = sorted(((n, p) for p, n in net.items() if n > 0), key=lambda x: (-x[0], x[1]))
    debtors = sorted(((-n, p) for p, n in net.items() if n < 0), key=lambda x: (-x[0], x[1]))

    transfers = []
    i = j = 0
    credit, debt = [list(c) for c in creditors], [list(d) for d in debtors]
    while i < len(credit) and j < len(debt):
        amount = min(credit[i][0], debt[j][0])
        if amount > 0:
            transfers.append({"from": debt[j][1], "to": credit[i][1], "amount": amount / 100})
        credit[i][0] -= amount
        debt[j][0] -= amount
        if credit[i][0] == 0:
            i += 1
        if debt[j][0] == 0:
            j += 1

    return {
        "settlements": transfers,
        "total_spend": total / 100,
        "per_person": [
            {
                "participant": p,
                "paid": paid[p] / 100,
                "share": owed[p] / 100,
                "net": net[p] / 100,
            }
            for p in request.participants
        ],
    }

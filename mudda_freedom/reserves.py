"""Reserve requirements from dated obligations and available bill funding."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from .engine import ZERO, money


@dataclass(frozen=True)
class DatedAmount:
    day: date
    amount: str | Decimal


@dataclass(frozen=True)
class ReserveAssessment:
    required: Decimal
    already_saved: Decimal
    remaining: Decimal
    next_payment: Decimal
    funding_before_next_payment: Decimal
    assessed_through: date


def assess_reserve(*, start: date, through: date,
                   payments: Iterable[DatedAmount],
                   arrivals: Iterable[DatedAmount],
                   already_saved: str | Decimal = "0") -> ReserveAssessment:
    """Find the largest cumulative shortfall over an explicit horizon.

    Arrivals are funds available in Bill Pay, after bank processing and delays,
    rather than transfer initiation dates. Payments precede arrivals on the
    same day, conservatively avoiding reliance on unconfirmed bank ordering.
    Include every obligation in the horizon; an incomplete schedule cannot
    establish readiness. Savings are counted once, after calculating the goal.
    """
    if through < start:
        raise ValueError("Assessment end must not precede start.")
    saved = money(already_saved)
    obligations = sorted(((item.day, money(item.amount)) for item in payments))
    funding = sorted(((item.day, money(item.amount)) for item in arrivals))
    if not obligations:
        raise ValueError("At least one upcoming payment is required.")
    if any(not start <= day <= through for day, _ in obligations + funding):
        raise ValueError("All events must fall within the assessment horizon.")
    events = [(day, 0, -amount) for day, amount in obligations]
    events += [(day, 1, amount) for day, amount in funding]
    balance = required = ZERO
    for _, _, delta in sorted(events):
        balance += delta
        required = max(required, -balance)
    first_day = obligations[0][0]
    next_payment = sum((amount for day, amount in obligations if day == first_day), ZERO)
    before = sum((amount for day, amount in funding if day < first_day), ZERO)
    return ReserveAssessment(required, saved, max(ZERO, required-saved),
                             next_payment, before, through)

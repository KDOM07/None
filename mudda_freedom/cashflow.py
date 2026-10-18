"""Explicit dated cash flow, with conservative same-day event ordering."""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from .engine import money, ZERO


class HolidayRule(Enum):
    PREVIOUS = -1
    FOLLOWING = 1
    SKIP = 0


def processing_date(day: date, holidays: frozenset[date], rule: HolidayRule) -> date | None:
    if not isinstance(rule, HolidayRule):
        raise ValueError("Confirm the institution's processing rule first.")
    while day.weekday() >= 5 or day in holidays:
        if rule is HolidayRule.SKIP:
            return None
        day += timedelta(days=rule.value)
    return day


def grouped_transfers(dates, daily, *, holidays, rule):
    """Preserve each scheduled amount when multiple dates shift together."""
    amount = money(daily)
    grouped = {}
    for day in dates:
        actual = processing_date(day, holidays, rule)
        if actual is not None:
            grouped[actual] = grouped.get(actual, ZERO) + amount
    return grouped


@dataclass(frozen=True)
class Event:
    day: date
    order: int
    amount: Decimal
    source: str | None
    destination: str | None


@dataclass(frozen=True)
class Simulation:
    balances: dict[str, Decimal]
    shortages: tuple[tuple[date, str, Decimal], ...]
    income: Decimal
    expenses: Decimal


def simulate(opening, events):
    """Orders must encode confirmed bank timing, including arrival delays.

    None source means external income; None destination means external expense.
    Every account must be declared. Internal movements count as neither.
    No activation decision is made from a finite projection alone.
    """
    balances = {name: money(value) for name, value in opening.items()}
    shortages = []
    income = expenses = ZERO
    ordered = sorted(events, key=lambda event: (event.day, event.order))
    keys = [(event.day, event.order) for event in ordered]
    if len(set(keys)) != len(keys):
        raise ValueError("Same-day event ordering must be explicit and unique.")
    for event in ordered:
        amount = money(event.amount)
        if event.source == event.destination:
            raise ValueError("Event needs distinct source and destination.")
        for account in (event.source, event.destination):
            if account is not None and account not in balances:
                raise ValueError("Unknown account.")
        if event.source is None:
            income += amount
        else:
            balances[event.source] -= amount
            if balances[event.source] < 0:
                shortages.append((event.day, event.source, -balances[event.source]))
        if event.destination is None:
            expenses += amount
        else:
            balances[event.destination] += amount
    return Simulation(balances, tuple(shortages), income, expenses)

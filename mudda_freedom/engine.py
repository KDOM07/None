"""Pure calculations. Monetary inputs must be decimal strings or Decimals.

The customer-confirmed ROUND_HALF_UP policy rounds weekly amounts to cents,
then rounds daily amounts to cents using the rounded weekly amount.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, localcontext
from enum import Enum
from typing import Iterable

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value: str | Decimal) -> Decimal:
    if not isinstance(value, (str, Decimal)):
        raise TypeError("Use a decimal string or Decimal, never a binary float.")
    result = Decimal(value)
    if not result.is_finite() or result < 0:
        raise ValueError("Amounts must be finite and nonnegative.")
    return result


class Frequency(Enum):
    WEEKLY = 52
    BIWEEKLY = 26
    SEMIMONTHLY = 24
    MONTHLY = 12
    QUARTERLY = 4
    SEMIANNUAL = 2
    ANNUAL = 1


class RoundingPolicy(Enum):
    HALF_UP_EACH_STEP = "half_up_each_step"


@dataclass(frozen=True)
class Allocation:
    annual: Decimal
    weekly: Decimal
    daily: Decimal


def allocate(amount: str | Decimal, frequency: Frequency | int, *,
             rounding: RoundingPolicy) -> Allocation:
    """Custom frequency is an explicit positive integer occurrences per year."""
    if rounding is not RoundingPolicy.HALF_UP_EACH_STEP:
        raise ValueError("An explicit supported rounding policy is required.")
    count = frequency.value if isinstance(frequency, Frequency) else frequency
    if type(count) is not int or count <= 0:
        raise ValueError("Occurrences per year must be a positive integer.")
    with localcontext() as ctx:
        ctx.prec = 50
        annual = money(amount) * count
        weekly = (annual / 52).quantize(CENT, rounding=ROUND_HALF_UP)
        daily = (weekly / 5).quantize(CENT, rounding=ROUND_HALF_UP)
    return Allocation(annual, weekly, daily)


def average_amount(history: Iterable[str | Decimal]) -> Decimal:
    values = tuple(money(value) for value in history)
    if not values:
        raise ValueError("At least one observation is required.")
    with localcontext() as ctx:
        ctx.prec = 50
        return sum(values, ZERO) / len(values)


def variable_monthly_bill(history: Iterable[str | Decimal]) -> Decimal:
    """Use the latest 12 monthly observations; require a complete year."""
    values = tuple(history)
    if len(values) < 12:
        raise ValueError("Supply 12 monthly observations or an explicit bill estimate.")
    return average_amount(values[-12:])


class PaycheckMethod(Enum):
    AVERAGE = "average"
    LOWEST_TYPICAL = "lowest_typical"


def representative_paycheck(history: Iterable[str | Decimal], *,
                            method: PaycheckMethod) -> Decimal:
    """Caller supplies normal checks; exclusions require customer input."""
    values = tuple(money(value) for value in history)
    if not values:
        raise ValueError("At least one paycheck is required.")
    if method is PaycheckMethod.AVERAGE:
        return average_amount(values)
    if method is PaycheckMethod.LOWEST_TYPICAL:
        return min(values)
    raise ValueError("Customer must select a paycheck method.")


@dataclass(frozen=True)
class DailyPlan:
    income: Allocation
    bill_daily: Decimal
    free_daily: Decimal
    sustainable_allocation: bool


def daily_plan(income: Allocation, bills: Iterable[Allocation]) -> DailyPlan:
    daily = sum((bill.daily for bill in bills), ZERO)
    remaining = income.daily - daily
    # Preserve negative results so shortages cannot masquerade as zero spending.
    return DailyPlan(income, daily, remaining, remaining >= 0)


def weekdays(start: date, end: date) -> tuple[date, ...]:
    """Weekdays in [start, end); holidays are handled separately."""
    if end < start:
        raise ValueError("End must not precede start.")
    return tuple(start + timedelta(days=i) for i in range((end-start).days)
                 if (start + timedelta(days=i)).weekday() < 5)


@dataclass(frozen=True)
class Reconciliation:
    weekday_count: int
    scheduled: Decimal
    annual_requirement: Decimal
    difference: Decimal


def reconcile_year(allocation: Allocation, year: int) -> Reconciliation:
    count = len(weekdays(date(year, 1, 1), date(year+1, 1, 1)))
    scheduled = allocation.daily * count
    return Reconciliation(count, scheduled, allocation.annual,
                          scheduled-allocation.annual)


@dataclass(frozen=True)
class MigrationProgress:
    required: Decimal
    saved: Decimal
    additional: Decimal
    remaining: Decimal
    percent: Decimal
    reserve_funded: bool
    activation_allowed: bool


def migration_progress(*, required: str | Decimal, saved: str | Decimal,
                       additional: str | Decimal = "0") -> MigrationProgress:
    """Required is an explicit reserve goal, not a hard-coded 30-day formula.

    Savings are customer-selected confirmed amounts. Funding alone never
    authorizes activation; cash-flow and banking validation are still needed.
    """
    goal, existing, contribution = map(money, (required, saved, additional))
    if goal == 0:
        raise ValueError("A positive, assessed reserve goal is required.")
    total = existing + contribution
    remaining = max(ZERO, goal-total)
    percent = min(Decimal(100), total/goal*100)
    return MigrationProgress(goal, existing, contribution, remaining, percent,
                             total >= goal, False)

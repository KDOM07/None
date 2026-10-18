"""Activation gate over explicit, dated projection evidence."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .cashflow import Simulation
from .engine import DailyPlan, money
from .reserves import ReserveAssessment


@dataclass(frozen=True)
class ActivationDecision:
    allowed: bool
    reasons: tuple[str, ...]
    projected_through: date


def check_activation(*, plan: DailyPlan, reserve: ReserveAssessment,
                     simulation: Simulation, projection_through: date,
                     banking_confirmed: bool, schedule_complete: bool,
                     base_reserve: str | Decimal,
                     personalized_buffer: str | Decimal) -> ActivationDecision:
    """Evaluate a caller-supplied complete projection, never execute transfers.

    Base migration reserve and personalized buffer must be explicitly assessed.
    Reserve savings must already be reflected in simulation opening balances;
    this gate does not add or move them. Approval applies only to this projection.
    """
    base, buffer = money(base_reserve), money(personalized_buffer)
    reasons = []
    if not plan.sustainable_allocation:
        reasons.append("Daily expenses exceed your daily income allocation.")
    target = max(base, reserve.required) + buffer
    if reserve.already_saved < target:
        reasons.append(f"Save ${target-reserve.already_saved:.2f} more toward your reserve and buffer.")
    if simulation.shortages:
        day, account, amount = simulation.shortages[0]
        reasons.append(f"The {account} account is projected to be ${amount:.2f} short on {day.isoformat()}.")
    if projection_through < reserve.assessed_through:
        reasons.append("Extend the account projection through the reserve assessment period.")
    if not schedule_complete:
        reasons.append("Confirm the projection includes all paychecks, bills, and transfers.")
    if not banking_confirmed:
        reasons.append("Confirm deposit timing, transfer delays, fees, limits, and holiday rules with your banks.")
    return ActivationDecision(not reasons, tuple(reasons),
                              min(projection_through, reserve.assessed_through))

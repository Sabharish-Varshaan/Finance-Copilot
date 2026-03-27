from __future__ import annotations

from datetime import date
import math
from typing import Any

EXPECTED_RETURN = 0.12
MONTHLY_RATE = EXPECTED_RETURN / 12


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _calculate_required_sip(target_amount: float, years: float) -> float:
    months = years * 12
    if months <= 0:
        raise ValueError("Goal duration must be greater than zero")

    denominator = (1 + MONTHLY_RATE) ** months - 1
    if denominator <= 0:
        raise ValueError("Invalid SIP denominator")

    sip_required = target_amount * MONTHLY_RATE / denominator
    return round(sip_required, 2)


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, 28)
    return date(year, month, day)


def validate_goal(profile: dict, goal: dict, existing_goals: list) -> dict[str, Any]:
    monthly_income = _safe_float(profile.get("monthly_income"))
    monthly_expenses = _safe_float(profile.get("monthly_expenses"))
    monthly_emi = _safe_float(profile.get("monthly_emi"))

    target_amount = _safe_float(goal.get("target_amount"))
    years = _safe_float(goal.get("years"))

    monthly_savings = monthly_income - monthly_expenses - monthly_emi

    try:
        sip_required = _calculate_required_sip(target_amount=target_amount, years=years)
    except ValueError as error:
        return {
            "valid": False,
            "reason": str(error),
            "required_sip": 0.0,
            "available_savings": round(monthly_savings, 2),
            "suggested_sip": 0.0,
            "suggestions": [
                "Extend timeline",
                "Reduce goal amount",
                "Increase income",
            ],
        }

    total_existing_sip = sum(_safe_float(saved_goal.get("monthly_sip")) for saved_goal in existing_goals)
    total_required = sip_required + total_existing_sip

    if total_required > monthly_savings:
        return {
            "valid": False,
            "reason": "Goal exceeds your financial capacity",
            "required_sip": round(sip_required, 2),
            "available_savings": round(monthly_savings, 2),
            "suggested_sip": round(monthly_savings - total_existing_sip, 2),
            "suggestions": [
                "Extend timeline",
                "Reduce goal amount",
                "Increase income",
            ],
        }

    return {
        "valid": True,
        "required_sip": round(sip_required, 2),
    }


def build_auto_adjustment(target_amount: float, feasible_sip: float) -> dict[str, Any] | None:
    feasible_sip = max(feasible_sip, 0.0)
    target_amount = max(target_amount, 0.0)

    if feasible_sip <= 0 or target_amount <= 0:
        return None

    numerator = (target_amount * MONTHLY_RATE) / feasible_sip + 1
    if numerator <= 1:
        return None

    months = max(math.ceil(math.log(numerator) / math.log(1 + MONTHLY_RATE)), 1)
    years = round(months / 12, 2)
    adjusted_target_date = _add_months(date.today(), months)

    return {
        "adjusted_years": years,
        "adjusted_target_date": adjusted_target_date.isoformat(),
        "feasible_sip": round(feasible_sip, 2),
    }

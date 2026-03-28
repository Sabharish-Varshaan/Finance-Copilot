from __future__ import annotations

from datetime import date
import math
from typing import Any

DEFAULT_EXPECTED_RETURN = 0.10
SAFETY_BUFFER_RATE = 0.10
MIN_SAFETY_BUFFER = 5000.0


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _calculate_required_sip(target_amount: float, years: float, annual_return: float) -> float:
    months = years * 12
    if months <= 0:
        raise ValueError("Goal duration must be greater than zero")

    monthly_rate = annual_return / 12
    denominator = (1 + monthly_rate) ** months - 1
    if denominator <= 0:
        raise ValueError("Invalid SIP denominator")

    sip_required = target_amount * monthly_rate / denominator if monthly_rate > 0 else target_amount / months
    return round(sip_required, 2)


def _safety_buffer_amount(monthly_income: float) -> float:
    return round(max(monthly_income * SAFETY_BUFFER_RATE, MIN_SAFETY_BUFFER), 2)


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
    annual_return = _safe_float(goal.get("expected_annual_return"), DEFAULT_EXPECTED_RETURN)

    available_surplus = monthly_income - monthly_expenses - monthly_emi
    safety_buffer_amount = _safety_buffer_amount(monthly_income)
    investable_surplus = max(available_surplus - safety_buffer_amount, 0.0)
    total_existing_sip = sum(_safe_float(saved_goal.get("monthly_sip")) for saved_goal in existing_goals)

    try:
        sip_required = _calculate_required_sip(
            target_amount=target_amount,
            years=years,
            annual_return=annual_return,
        )
    except ValueError as error:
        return {
            "valid": False,
            "reason": str(error),
            "required_sip": 0.0,
            "available_savings": round(available_surplus, 2),
            "available_surplus": round(available_surplus, 2),
            "safety_buffer_amount": safety_buffer_amount,
            "investable_surplus": round(investable_surplus, 2),
            "total_existing_sip": round(total_existing_sip, 2),
            "shortfall_amount": 0.0,
            "sip_to_investable_surplus_ratio": None,
            "reason_codes": ["invalid_goal_duration"],
            "suggested_sip": 0.0,
            "suggestions": [
                "Extend timeline",
                "Reduce goal amount",
                "Increase income",
            ],
        }

    total_required = sip_required + total_existing_sip

    if total_required > investable_surplus:
        shortfall = max(total_required - investable_surplus, 0.0)
        ratio = (sip_required / investable_surplus) if investable_surplus > 0 else None
        return {
            "valid": False,
            "reason": (
                "This SIP exceeds your investable monthly surplus after essentials, EMI, and safety buffer"
            ),
            "required_sip": round(sip_required, 2),
            "available_savings": round(available_surplus, 2),
            "available_surplus": round(available_surplus, 2),
            "safety_buffer_amount": safety_buffer_amount,
            "investable_surplus": round(investable_surplus, 2),
            "total_existing_sip": round(total_existing_sip, 2),
            "shortfall_amount": round(shortfall, 2),
            "sip_to_investable_surplus_ratio": round(ratio, 2) if ratio is not None else None,
            "reason_codes": ["sip_exceeds_investable_surplus"],
            "suggested_sip": round(sip_required, 2),
            "suggestions": [
                "Extend timeline to reduce required monthly SIP",
                "Reduce goal amount to match current investable surplus",
                "Increase monthly surplus by reducing expenses or EMI",
            ],
        }

    return {
        "valid": True,
        "required_sip": round(sip_required, 2),
        "available_savings": round(available_surplus, 2),
        "available_surplus": round(available_surplus, 2),
        "safety_buffer_amount": safety_buffer_amount,
        "investable_surplus": round(investable_surplus, 2),
        "total_existing_sip": round(total_existing_sip, 2),
        "shortfall_amount": 0.0,
        "sip_to_investable_surplus_ratio": (
            round(sip_required / (investable_surplus - total_existing_sip), 2)
            if (investable_surplus - total_existing_sip) > 0
            else None
        ),
    }


def build_auto_adjustment(
    target_amount: float,
    feasible_sip: float,
    annual_return: float = DEFAULT_EXPECTED_RETURN,
) -> dict[str, Any] | None:
    feasible_sip = max(feasible_sip, 0.0)
    target_amount = max(target_amount, 0.0)

    if feasible_sip <= 0 or target_amount <= 0:
        return None

    monthly_rate = annual_return / 12
    if monthly_rate <= 0:
        return None

    numerator = (target_amount * monthly_rate) / feasible_sip + 1
    if numerator <= 1:
        return None

    months = max(math.ceil(math.log(numerator) / math.log(1 + monthly_rate)), 1)
    years = round(months / 12, 2)
    adjusted_target_date = _add_months(date.today(), months)

    return {
        "adjusted_years": years,
        "adjusted_target_date": adjusted_target_date.isoformat(),
        "feasible_sip": round(feasible_sip, 2),
    }

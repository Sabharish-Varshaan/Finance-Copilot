from __future__ import annotations

import asyncio
import json
import re
from datetime import date
from typing import Any

from app.services.ai.llm_service import generate_response
from app.services.finance_constraints.constraint_engine import enforce_goal_sip_constraints


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, 28)
    return date(year, month, day)


def _normalized_risk_profile(value: str) -> str:
    risk = (value or "moderate").strip().lower()
    if risk in {"conservative", "low"}:
        return "low"
    if risk in {"aggressive", "high"}:
        return "high"
    return "moderate"


def get_expected_return(risk_profile: str) -> float:
    risk = _normalized_risk_profile(risk_profile)
    if risk == "low":
        return 0.07
    if risk == "moderate":
        return 0.10
    if risk == "high":
        return 0.12
    return 0.10


def _calculate_required_sip(
    target_amount: float,
    current_amount: float,
    annual_return: float,
    target_date: date,
) -> float:
    remaining = max(target_amount - current_amount, 0.0)
    months = _months_between(date.today(), target_date)

    if months <= 0:
        raise ValueError("Target date must be in the future")

    if remaining <= 0:
        return 0.0

    monthly_rate = annual_return / 12
    if monthly_rate == 0:
        return round(remaining / months, 2)

    denominator = (1 + monthly_rate) ** months - 1
    if denominator <= 0:
        raise ValueError("Invalid SIP calculation inputs")

    sip = remaining * monthly_rate / denominator
    return round(sip, 2)


def _future_value_from_sip(monthly_sip: float, months: int, monthly_rate: float) -> float:
    if monthly_sip <= 0 or months <= 0:
        return 0.0
    if monthly_rate <= 0:
        return monthly_sip * months
    denominator = (1 + monthly_rate) ** months - 1
    return monthly_sip * (denominator / monthly_rate)


def _is_achievable(
    *,
    target_amount: float,
    current_amount: float,
    monthly_sip: float,
    months: int,
    monthly_rate: float,
) -> bool:
    remaining_target = max(target_amount - current_amount, 0.0)
    if remaining_target <= 0:
        return True
    future_value = _future_value_from_sip(monthly_sip, months, monthly_rate)
    return future_value >= remaining_target


def _recalculate_timeline_months(
    *,
    target_amount: float,
    current_amount: float,
    final_sip: float,
    monthly_rate: float,
    original_months: int,
) -> int:
    remaining_target = max(target_amount - current_amount, 0.0)
    months = max(original_months, 1)

    if remaining_target <= 0:
        return months

    if final_sip <= 0:
        raise ValueError("No SIP capacity available to reach this goal")

    max_months = 1200
    while months <= max_months:
        future_value = _future_value_from_sip(final_sip, months, monthly_rate)
        if future_value >= remaining_target:
            return months
        months += 1

    raise ValueError("Goal is not achievable within a reasonable timeline at current SIP")


def _run_async_response(messages: list[dict[str, str]]) -> str:
    try:
        return asyncio.run(generate_response(messages))
    except RuntimeError as exc:
        if "asyncio.run() cannot be called from a running event loop" not in str(exc):
            raise
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(generate_response(messages))
        finally:
            loop.close()


def _extract_json_object(content: str) -> dict[str, Any] | None:
    text = (content or "").strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _ai_messages(
    income: float,
    expenses: float,
    emi: float,
    savings: float,
    existing_goals_sip: float,
    target_amount: float,
    timeline_years: float,
) -> list[dict[str, str]]:
    system_prompt = (
        "You are a financial planning assistant. "
        "Evaluate goal feasibility with safety-first recommendations. "
        "Return JSON only with keys: suggested_timeline, adjustment_reason."
    )
    user_prompt = (
        "Evaluate if this goal is financially realistic.\n\n"
        "INPUT:\n"
        f"income: {income}\n"
        f"expenses: {expenses}\n"
        f"emi: {emi}\n"
        f"savings: {savings}\n"
        f"existing_goals_sip: {existing_goals_sip}\n"
        f"target_amount: {target_amount}\n"
        f"timeline_years: {timeline_years:.2f}\n"
        "Important: Do not return or modify SIP values.\n\n"
        "Return:\n"
        "- suggested_timeline (number, years)\n"
        "- adjustment_reason (string)\n\n"
        "Do NOT exceed user's financial capacity. "
        "Consider obligations, savings stability, and long-term safety."
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _evaluate_with_ai(
    *,
    income: float,
    expenses: float,
    emi: float,
    savings: float,
    existing_goals_sip: float,
    target_amount: float,
    timeline_years: float,
) -> dict[str, Any]:
    messages = _ai_messages(
        income=income,
        expenses=expenses,
        emi=emi,
        savings=savings,
        existing_goals_sip=existing_goals_sip,
        target_amount=target_amount,
        timeline_years=timeline_years,
    )
    try:
        raw = _run_async_response(messages)
        parsed = _extract_json_object(raw) or {}
    except Exception:
        parsed = {}

    suggested_timeline = _safe_float(parsed.get("suggested_timeline"), timeline_years)
    adjustment_reason = str(parsed.get("adjustment_reason") or "AI planning unavailable, deterministic plan used.")

    return {
        "suggested_timeline": max(suggested_timeline, timeline_years),
        "adjustment_reason": adjustment_reason,
    }


def _normalize_existing_goals_sip(existing_goals: list[Any]) -> float:
    total = 0.0
    for item in existing_goals:
        if isinstance(item, dict):
            total += _safe_float(item.get("monthly_sip"), 0.0)
        else:
            total += _safe_float(getattr(item, "monthly_sip_required", 0.0), 0.0)
    return round(total, 2)


def plan_goal(profile: dict[str, Any], goal: dict[str, Any], existing_goals: list[Any], fire_sip: float = 0.0) -> dict[str, Any]:
    income = _safe_float(profile.get("monthly_income"))
    expenses = _safe_float(profile.get("monthly_expenses"))
    emi = _safe_float(profile.get("monthly_emi"))
    savings = _safe_float(profile.get("savings"))

    goal_name = str(goal.get("title") or "Goal")
    target_amount = _safe_float(goal.get("target_amount"))
    current_amount = _safe_float(goal.get("current_amount"))
    risk_profile = str(profile.get("risk_profile") or "moderate")
    annual_return = get_expected_return(risk_profile)
    monthly_return = annual_return / 12
    target_date = goal.get("target_date")

    if not isinstance(target_date, date):
        raise ValueError("Goal target_date is required")

    months = _months_between(date.today(), target_date)
    if months <= 0:
        raise ValueError("Target date must be in the future")

    timeline_years = round(months / 12, 2)
    calculated_sip = _calculate_required_sip(
        target_amount=target_amount,
        current_amount=current_amount,
        annual_return=annual_return,
        target_date=target_date,
    )

    existing_goals_sip_total = _normalize_existing_goals_sip(existing_goals)
    net_savings = income - expenses - emi
    # CRITICAL FIX: Use FIRE-adjusted surplus if fire_sip provided, else fall back to 50% heuristic
    remaining_surplus = max(net_savings - fire_sip, 0.0) if fire_sip > 0 else net_savings
    max_allowed = max(remaining_surplus - existing_goals_sip_total, 0.0)

    ai_eval = _evaluate_with_ai(
        income=income,
        expenses=expenses,
        emi=emi,
        savings=savings,
        existing_goals_sip=existing_goals_sip_total,
        target_amount=target_amount,
        timeline_years=timeline_years,
    )

    ai_reasoning = str(ai_eval.get("adjustment_reason") or "")

    constraint_result = enforce_goal_sip_constraints(
        calculated_sip=calculated_sip,
        max_allowed=max_allowed,
        existing_sip=existing_goals_sip_total,
    )

    final_sip = _safe_float(constraint_result.get("final_sip"), calculated_sip)
    adjusted = bool(constraint_result.get("adjusted", False))
    reason_text = str(constraint_result.get("reason") or "Within safe investment limit")

    timeline_extended = False
    adjusted_timeline_years = timeline_years
    adjusted_target_date = target_date

    if adjusted:
        adjusted_months = _recalculate_timeline_months(
            target_amount=target_amount,
            current_amount=current_amount,
            final_sip=final_sip,
            monthly_rate=monthly_return,
            original_months=months,
        )
        if adjusted_months <= months:
            raise ValueError("Reduced SIP requires a longer timeline to keep the goal feasible")
        adjusted_timeline_years = round(adjusted_months / 12, 2)
        adjusted_target_date = _add_months(date.today(), adjusted_months)
        timeline_extended = adjusted_months > months

    final_months = _months_between(date.today(), adjusted_target_date)
    if not _is_achievable(
        target_amount=target_amount,
        current_amount=current_amount,
        monthly_sip=final_sip,
        months=final_months,
        monthly_rate=monthly_return,
    ):
        raise ValueError("Goal remains unachievable with current SIP and timeline")

    if not ai_reasoning:
        ai_reasoning = reason_text

    return {
        "goal_name": goal_name,
        "raw_sip": round(calculated_sip, 2),
        "calculated_sip": round(calculated_sip, 2),
        "ai_sip": round(calculated_sip, 2),
        "final_sip": round(max(final_sip, 0.0), 2),
        "sip": round(max(final_sip, 0.0), 2),
        "timeline": round(adjusted_timeline_years, 2),
        "original_timeline": round(timeline_years, 2),
        "adjusted_timeline": round(adjusted_timeline_years, 2),
        "timeline_extended": timeline_extended,
        "timeline_adjusted": timeline_extended,
        "adjusted": adjusted,
        "reason": reason_text,
        "ai_reasoning": ai_reasoning,
        "backend_limit": round(max(net_savings * 0.5, 0.0), 2),
        "existing_goals_sip_total": round(existing_goals_sip_total, 2),
        "adjustment_reason_codes": (["sip_above_max_allowed"] if adjusted else []),
        "original_target_date": target_date.isoformat(),
        "adjusted_target_date": adjusted_target_date.isoformat(),
        "new_target_date": adjusted_target_date.isoformat(),
        "net_savings": round(net_savings, 2),
        "max_allowed_new_sip": round(max_allowed, 2),
        "expected_return": round(annual_return, 4),
        "monthly_return": round(monthly_return, 6),
        "return_assumption_note": "Expected return is a planning assumption, not a guaranteed outcome.",
        "adjustment_options": [
            "Increase timeline",
            "Increase SIP",
            "Reduce goal amount",
        ],
    }

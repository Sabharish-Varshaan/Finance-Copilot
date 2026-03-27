from typing import Any


EXPECTED_ANNUAL_RETURN = 0.12
DEFAULT_RETIREMENT_AGE = 55
DEFAULT_MULTIPLIER = 33.0
INFLATION_RATE = 0.06
SAFETY_BUFFER = 1.2
EMERGENCY_MONTHS_TARGET = 6
EMERGENCY_GAP_SIP_REDUCTION = 0.25
DEBT_PRESSURE_SIP_REDUCTION = 0.20
TAX_SUGGESTION_INCOME_THRESHOLD = 700000


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _fire_type(multiplier: float) -> str:
    if multiplier >= 40:
        return "safe"
    if multiplier >= 33:
        return "standard"
    return "lean"


def _monthly_sip_required(target_amount: float, years: int, expected_return: float = EXPECTED_ANNUAL_RETURN) -> float:
    if target_amount <= 0 or years <= 0:
        return 0.0

    monthly_rate = expected_return / 12
    periods = years * 12

    if periods <= 0:
        return 0.0

    if monthly_rate <= 0:
        return round(target_amount / periods, 2)

    denominator = (1 + monthly_rate) ** periods - 1
    if denominator <= 0:
        return 0.0

    sip = target_amount * monthly_rate / denominator
    return round(sip, 2)


def _build_monthly_plan(current_savings: float, monthly_sip: float, total_months: int) -> list[dict[str, float | int]]:
    if total_months <= 0:
        return []

    monthly_return = EXPECTED_ANNUAL_RETURN / 12
    corpus = current_savings
    plan: list[dict[str, float | int]] = []

    for month in range(1, total_months + 1):
        corpus = corpus * (1 + monthly_return) + monthly_sip

        # Return first 12 months and then yearly milestones only.
        if month <= 12 or month % 12 == 0:
            plan.append({"month": month, "corpus": round(corpus, 2)})

    return plan


def generate_fire_plan(
    profile: dict,
    goals: list,
    retirement_age: int = DEFAULT_RETIREMENT_AGE,
    multiplier: float = DEFAULT_MULTIPLIER,
):
    age = max(_safe_int(profile.get("age"), 0), 0)
    monthly_income = max(_safe_float(profile.get("monthly_income"), 0.0), 0.0)
    monthly_expenses = max(_safe_float(profile.get("monthly_expenses"), 0.0), 0.0)
    current_savings = max(_safe_float(profile.get("current_savings"), 0.0), 0.0)
    monthly_emi = max(_safe_float(profile.get("monthly_emi"), 0.0), 0.0)
    retirement_age = max(_safe_int(retirement_age, DEFAULT_RETIREMENT_AGE), age)
    multiplier = _clamp(_safe_float(multiplier, DEFAULT_MULTIPLIER), 25.0, 50.0)

    annual_expense = monthly_expenses * 12
    annual_income = monthly_income * 12
    years_to_retire = max(retirement_age - age, 0)
    adjusted_expense = annual_expense * ((1 + INFLATION_RATE) ** years_to_retire)
    fire_target = adjusted_expense * multiplier
    fire_target *= SAFETY_BUFFER

    monthly_sip_fire = _monthly_sip_required(fire_target, years_to_retire)
    recommendation_flags: list[str] = []

    emergency_threshold = monthly_expenses * EMERGENCY_MONTHS_TARGET
    emergency_gap = current_savings < emergency_threshold
    if emergency_gap:
        recommendation_flags.append("build_emergency_fund")
        monthly_sip_fire = round(monthly_sip_fire * (1 - EMERGENCY_GAP_SIP_REDUCTION), 2)

    if monthly_income > 0 and monthly_emi > 0.4 * monthly_income:
        recommendation_flags.append("reduce_debt")
        monthly_sip_fire = round(monthly_sip_fire * (1 - DEBT_PRESSURE_SIP_REDUCTION), 2)

    insurance_coverage = max(_safe_float(profile.get("insurance_coverage"), 0.0), 0.0)
    insurance_gap = insurance_coverage < (annual_income * 10)

    tax_suggestions: list[str] = []
    if annual_income > TAX_SUGGESTION_INCOME_THRESHOLD:
        tax_suggestions = [
            "Use 80C investments (PPF, ELSS)",
            "Consider NPS for additional tax savings",
        ]

    sorted_goals = sorted(goals or [], key=lambda item: _safe_int(item.get("years"), 0))
    goal_plan: list[dict[str, Any]] = []
    for goal in sorted_goals:
        name = str(goal.get("name", "Goal")).strip() or "Goal"
        target = max(_safe_float(goal.get("amount"), 0.0), 0.0)
        years = max(_safe_int(goal.get("years"), 0), 0)
        adjusted_target = target * ((1 + INFLATION_RATE) ** years) if years > 0 else target
        goal_plan.append(
            {
                "name": name,
                "target": round(adjusted_target, 2),
                "monthly_sip": _monthly_sip_required(adjusted_target, years),
                "years": years,
            }
        )

    equity = max(100 - age, 50)
    debt = 100 - equity
    total_months = years_to_retire * 12
    monthly_plan = _build_monthly_plan(current_savings, monthly_sip_fire, total_months)

    return {
        "fire_target": round(fire_target, 2),
        "years_to_retire": years_to_retire,
        "monthly_sip_fire": round(monthly_sip_fire, 2),
        "goal_plan": goal_plan,
        "monthly_plan": monthly_plan,
        "allocation": {"equity": int(equity), "debt": int(debt)},
        "emergency_gap": emergency_gap,
        "insurance_gap": insurance_gap,
        "tax_suggestions": tax_suggestions,
        "recommendation_flags": recommendation_flags,
        "retirement_age": retirement_age,
        "multiplier": round(multiplier, 2),
        "inflation_rate": INFLATION_RATE,
        "safety_buffer": SAFETY_BUFFER,
        "fire_type": _fire_type(multiplier),
    }

from typing import Any
from datetime import date, timedelta

from app.services.goals.goal_planner import get_expected_return as goal_expected_return


DEFAULT_RETIREMENT_AGE = 55
DEFAULT_MULTIPLIER = 33.0
INFLATION_RATE = 0.06
# Kept for payload compatibility; not applied to corpus calculation.
SAFETY_BUFFER = 1.0
EMERGENCY_MONTHS_TARGET = 6
TAX_SUGGESTION_INCOME_THRESHOLD = 700000
EXPECTED_RETURN_MIN = 0.05
EXPECTED_RETURN_MAX = 0.15
MAX_TIMELINE_YEARS = 45


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


def _monthly_sip_required(target_amount: float, years: int, expected_return: float = 0.10) -> float:
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


def get_expected_return(profile: dict, user_input: float | None) -> tuple[float, str]:
    if user_input is not None:
        clamped = _clamp(_safe_float(user_input, 0.10), EXPECTED_RETURN_MIN, EXPECTED_RETURN_MAX)
        return round(clamped, 4), "user"

    risk_profile = str(profile.get("risk_profile", "moderate") or "moderate")
    return round(goal_expected_return(risk_profile), 4), "system"


def _build_monthly_plan(
    current_savings: float,
    monthly_sip: float,
    total_months: int,
    expected_return: float,
) -> list[dict[str, float | int]]:
    if total_months <= 0:
        return []

    monthly_return = expected_return / 12
    corpus = current_savings
    plan: list[dict[str, float | int]] = []

    for month in range(1, total_months + 1):
        corpus = corpus * (1 + monthly_return) + monthly_sip

        # Return first 12 months and then yearly milestones only.
        if month <= 12 or month % 12 == 0:
            plan.append({"month": month, "corpus": round(corpus, 2)})

    return plan


def _future_value_from_sip(
    current_savings: float,
    monthly_sip: float,
    total_months: int,
    expected_return: float,
) -> float:
    if total_months <= 0:
        return current_savings

    monthly_return = expected_return / 12
    corpus = current_savings

    for _ in range(total_months):
        corpus = corpus * (1 + monthly_return) + monthly_sip

    return corpus


def _years_to_target(
    target_amount: float,
    current_savings: float,
    monthly_sip: float,
    expected_return: float,
    max_years: int = MAX_TIMELINE_YEARS,
) -> int | None:
    if target_amount <= 0:
        return 0

    if current_savings >= target_amount:
        return 0

    if monthly_sip <= 0:
        return None

    max_months = max_years * 12
    for month in range(1, max_months + 1):
        fv = _future_value_from_sip(current_savings, monthly_sip, month, expected_return)
        if fv >= target_amount:
            years = (month + 11) // 12
            return years

    return None


def _target_date_from_years(years: int) -> str:
    target = date.today() + timedelta(days=max(years, 0) * 365)
    return target.isoformat()


def _validate_response(response: dict, goal_status: str, net_savings: float) -> None:
    """
    CRITICAL: Mandatory consistency validation before returning response.
    Ensures financial correctness guarantees are maintained.
    """
    sip = response.get("monthly_sip_fire", 0.0)
    min_required = response.get("minimum_sip_required", 0.0)
    monthly_plan = response.get("monthly_plan", [])
    scenarios = response.get("scenarios", [])
    explanation = response.get("explanation", "")

    # Validation 1: Unrealistic goals must NOT have monthly plan or scenarios
    if goal_status == "unrealistic":
        assert len(monthly_plan) == 0, f"BUG: Unrealistic goal has monthly_plan with {len(monthly_plan)} entries"
        assert len(scenarios) == 0, f"BUG: Unrealistic goal has {len(scenarios)} scenarios"
        assert explanation, "BUG: Unrealistic goal missing explanation"

    # Validation 2: SIP must not be zero UNLESS explicitly unrealistic
    if goal_status in ["achievable", "needs_adjustment"]:
        assert sip > 0, f"BUG: {goal_status} goal has SIP=0, should be positive"

    # Validation 3: SIP must never exceed available surplus
    assert sip <= net_savings + 100, f"BUG: SIP {sip} exceeds net_savings {net_savings}"  # +100 for rounding

    # Validation 4: Minimum required should be tracked
    assert min_required > 0, "BUG: minimum_sip_required should always be positive"

    # Validation 5: Timeline should be positive for feasible goals
    if goal_status in ["achievable", "needs_adjustment"]:
        years = response.get("years_to_retire", 0)
        assert years > 0, f"BUG: {goal_status} goal has {years} years timeline"


def _scenario_result(
    name: str,
    sip: float,
    target_amount: float,
    current_savings: float,
    expected_return: float,
    age: int,
    original_target_age: int,
) -> dict[str, Any]:
    years = _years_to_target(
        target_amount=target_amount,
        current_savings=current_savings,
        monthly_sip=sip,
        expected_return=expected_return,
    )
    if years is None:
        return {
            "name": name,
            "sip": round(max(sip, 0.0), 2),
            "years_to_target": None,
            "target_age": None,
            "achieved_age": None,
            "original_target_age": int(original_target_age),
            "status": "unrealistic",
        }

    achieved_age = int(age + years)
    return {
        "name": name,
        "sip": round(max(sip, 0.0), 2),
        "years_to_target": int(years),
        "target_age": achieved_age,
        "achieved_age": achieved_age,
        "original_target_age": int(original_target_age),
        "status": "achievable",
    }


def _build_priority_text(
    insurance_gap: bool,
    insurance_required: float,
    monthly_sip_fire: float,
    net_savings: float,
) -> list[str]:
    priority_text: list[str] = []
    if insurance_gap:
        priority_text.append(f"Get life insurance (₹{round(insurance_required):,} recommended)")

    target_sip = max(monthly_sip_fire, net_savings * 0.6)
    priority_text.append(f"Invest ₹{round(target_sip):,}/month consistently")
    priority_text.append("Increase SIP gradually")
    return priority_text


def _build_next_steps(
    goal_status: str,
    emergency_gap: bool,
    emergency_threshold: float,
    current_savings: float,
    insurance_gap: bool,
    insurance_required: float,
    insurance_coverage: float,
    monthly_sip_fire: float,
) -> list[str]:
    steps: list[str] = []
    if emergency_gap:
        fund_gap = max(emergency_threshold - current_savings, 0.0)
        steps.append(f"Build emergency buffer: add INR {round(fund_gap):,} to reach 6-month safety")
    if insurance_gap:
        insurance_gap_amount = max(insurance_required - insurance_coverage, 0.0)
        steps.append(f"Close insurance gap: increase cover by INR {round(insurance_gap_amount):,}")

    if goal_status == "unrealistic":
        steps.append("Rework target or timeline before increasing risk")
    elif goal_status == "needs_adjustment":
        steps.append("Review adjusted timeline and keep SIP increases gradual every 6-12 months")
    else:
        steps.append(f"Start auto-investing INR {round(monthly_sip_fire):,}/month immediately")

    return steps[:3]


def _build_explanation(
    goal_status: str,
    fire_target: float,
    monthly_sip_required: float,
    monthly_sip_selected: float,
    base_years: int,
    final_years: int,
    net_savings: float,
    max_allowed_sip: float = 0.0,
) -> str:
    if goal_status == "achievable":
        return (
            f"✓ Your FIRE target of INR {round(fire_target):,} is achievable in about {base_years} years "
            f"with a monthly investment of INR {round(monthly_sip_selected):,}."
        )

    if goal_status == "needs_adjustment":
        if monthly_sip_selected < monthly_sip_required:
            return (
                f"Your ideal SIP of INR {round(monthly_sip_required):,} exceeds your available surplus "
                f"(INR {round(net_savings):,}). We've adjusted your plan to invest INR {round(monthly_sip_selected):,} monthly, "
                f"which will reach your FIRE target in approximately {final_years} years instead of {base_years}."
            )
        return (
            f"To reach INR {round(fire_target):,}, your timeline needs to extend from {base_years} to {final_years} years. "
            f"You'll invest INR {round(monthly_sip_selected):,} monthly, which is within your surplus capacity."
        )

    # unrealistic case
    return (
        f"This FIRE target cannot be achieved within {MAX_TIMELINE_YEARS} years, even at your maximum safe investment "
        f"level of INR {round(max_allowed_sip):,}/month. To make this goal realistic, you would need:\n"
        f"• A minimum monthly investment of INR {round(monthly_sip_required):,} (currently {round(monthly_sip_required - max_allowed_sip):,} "
        f"above your available surplus), OR\n"
        f"• A lower FIRE target, OR\n"
        f"• A longer timeline beyond {MAX_TIMELINE_YEARS} years."
    )


def generate_fire_plan(
    profile: dict,
    goals: list,
    retirement_age: int = DEFAULT_RETIREMENT_AGE,
    multiplier: float = DEFAULT_MULTIPLIER,
    expected_return_input: float | None = None,
):
    age = max(_safe_int(profile.get("age"), 0), 0)
    monthly_income = max(_safe_float(profile.get("monthly_income"), 0.0), 0.0)
    monthly_expenses = max(_safe_float(profile.get("monthly_expenses"), 0.0), 0.0)
    current_savings = max(_safe_float(profile.get("current_savings"), 0.0), 0.0)
    monthly_emi = max(_safe_float(profile.get("monthly_emi"), 0.0), 0.0)
    retirement_age = max(_safe_int(retirement_age, DEFAULT_RETIREMENT_AGE), age)
    multiplier = _clamp(_safe_float(multiplier, DEFAULT_MULTIPLIER), 25.0, 50.0)
    expected_return, return_source = get_expected_return(profile, expected_return_input)

    annual_expense = monthly_expenses * 12
    annual_income = monthly_income * 12
    years_to_retire = max(retirement_age - age, 0)
    future_expenses = annual_expense * ((1 + INFLATION_RATE) ** years_to_retire)
    # Standard FIRE corpus formula: inflate annual expenses once until retirement,
    # then apply corpus multiplier. No additional compounding/buffer on corpus.
    fire_target = future_expenses * multiplier

    monthly_sip_fire_required = _monthly_sip_required(
        fire_target, years_to_retire, expected_return=expected_return
    )
    recommendation_flags: list[str] = []
    risk_flags: list[str] = []

    net_savings = max(monthly_income - monthly_expenses - monthly_emi, 0.0)

    emergency_threshold = monthly_expenses * EMERGENCY_MONTHS_TARGET
    emergency_gap = current_savings < emergency_threshold
    if emergency_gap:
        recommendation_flags.append("build_emergency_fund")
        risk_flags.append("low_emergency_fund")

    if monthly_income > 0 and monthly_emi > 0.4 * monthly_income:
        recommendation_flags.append("reduce_debt")

    if monthly_income > 0 and monthly_emi > 0.3 * monthly_income:
        risk_flags.append("high_debt_pressure")

    insurance_coverage = max(_safe_float(profile.get("insurance_coverage"), 0.0), 0.0)
    insurance_gap = insurance_coverage < (annual_income * 10)
    if insurance_gap:
        recommendation_flags.append("increase_insurance")

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
        target_original = max(_safe_float(goal.get("amount"), 0.0), 0.0)
        years = max(_safe_int(goal.get("years"), 0), 0)
        adjusted_target = target_original * ((1 + INFLATION_RATE) ** years) if years > 0 else target_original
        inflation_impact = max(adjusted_target - target_original, 0.0)
        monthly_sip_required = _monthly_sip_required(adjusted_target, years, expected_return=expected_return)
        goal_plan.append(
            {
                "name": name,
                "target": round(adjusted_target, 2),
                "target_amount_original": round(target_original, 2),
                "target_amount_inflated": round(adjusted_target, 2),
                "inflation_impact": round(inflation_impact, 2),
                "monthly_sip_required": monthly_sip_required,  # PHASE 2.1: Track required
                "monthly_sip": monthly_sip_required,  # Will be adjusted if constrained
                "years": years,
                "status": "achievable",  # Will be updated if constrained
                "status_description": "On track",
                "underfunded": False,
                "timeline_adjusted": False,  # Will be updated if timeline extended
                "adjusted_years": None,  # Will be updated if timeline extended
            }
        )

    goal_sip_total = sum(_safe_float(goal.get("monthly_sip"), 0.0) for goal in goal_plan)

    # CRITICAL FIX: Respect FIRE priority
    # Priority order: 1. Emergency fund buffer, 2. FIRE minimum base, 3. Goals, 4. Remaining to FIRE
    min_fire_base = max(monthly_sip_fire_required * 0.5, 2000.0)  # At least 50% of required or 2K minimum
    available_for_goals = max(net_savings - min_fire_base, 0.0)
    
    # Cap goal SIP to available surplus
    if goal_sip_total > available_for_goals:
        goal_sip_total = available_for_goals
        # Proportionally reduce each goal SIP and mark as constrained
        if goal_plan:
            original_total = sum(_safe_float(goal.get("monthly_sip"), 0.0) for goal in goal_plan)
            if original_total > 0:
                factor = available_for_goals / original_total
                for goal in goal_plan:
                    original_sip = _safe_float(goal.get("monthly_sip"), 0.0)
                    reduced_sip = round(original_sip * factor, 2)
                    goal["monthly_sip"] = reduced_sip
                    # PHASE 2.1: Mark goal status as constrained if SIP was reduced
                    if reduced_sip < original_sip:
                        goal["status"] = "adjusted_plan"
                        goal["status_description"] = "Adjusted Plan (SIP reduced + timeline extended)"

    max_fire_sip = max(net_savings - goal_sip_total, 0.0)
    monthly_sip_fire = monthly_sip_fire_required
    sip_capped = False

    # CRITICAL FIX: Track required SIP even when capped (for "unrealistic" status)
    minimum_sip_required = monthly_sip_fire_required

    if monthly_sip_fire_required > max_fire_sip:
        monthly_sip_fire = max_fire_sip
        sip_capped = True

    base_years = years_to_retire
    years_to_target = _years_to_target(
        target_amount=fire_target,
        current_savings=current_savings,
        monthly_sip=monthly_sip_fire,
        expected_return=expected_return,
    )

    goal_status = "achievable"
    final_timeline_years = base_years
    timeline_adjusted = False

    if years_to_target is None:
        goal_status = "unrealistic"
        final_timeline_years = MAX_TIMELINE_YEARS
    elif years_to_target > base_years:
        goal_status = "needs_adjustment"
        timeline_adjusted = True
        final_timeline_years = years_to_target
    elif sip_capped:
        goal_status = "needs_adjustment"

    if goal_status == "achievable" and monthly_sip_fire > 0 and net_savings > 0 and monthly_sip_fire > (0.4 * net_savings):
        risk_flags.append("high_sip_dependency")

    if goal_status == "needs_adjustment" and not timeline_adjusted and years_to_target is not None:
        # Hard invariant: reduced SIP should never be returned with unchanged timeline.
        timeline_adjusted = years_to_target > base_years
        final_timeline_years = max(final_timeline_years, years_to_target)

    if goal_status == "unrealistic":
        timeline_adjusted = True

    for goal in goal_plan:
        goal_sip = _safe_float(goal.get("monthly_sip"), 0.0)
        goal["underfunded"] = goal_sip < 1000

    # CRITICAL FIX: Only generate roadmap for achievable/needs_adjustment goals
    # Do NOT generate monthly_plan for unrealistic goals (empty list instead)
    total_months = final_timeline_years * 12 if goal_status != "unrealistic" else 0
    monthly_plan = _build_monthly_plan(current_savings, monthly_sip_fire, total_months, expected_return)

    # CRITICAL FIX: Only generate scenarios for achievable goals
    # When unrealistic, scenarios list is empty (user cannot act on them anyway)
    scenarios: list[dict[str, Any]] = []
    
    if goal_status != "unrealistic":
        # Use a meaningful base for scenarios: use max_fire_sip if current is 0
        scenario_base_sip = max(monthly_sip_fire, max_fire_sip * 0.5) if monthly_sip_fire > 0 else max_fire_sip * 0.5
        
        scenarios = [
            _scenario_result(
                name="current_sip",
                sip=scenario_base_sip,
                target_amount=fire_target,
                current_savings=current_savings,
                expected_return=expected_return,
                age=age,
                original_target_age=retirement_age,
            ),
            _scenario_result(
                name="sip_plus_25",
                sip=scenario_base_sip * 1.25,
                target_amount=fire_target,
                current_savings=current_savings,
                expected_return=expected_return,
                age=age,
                original_target_age=retirement_age,
            ),
            _scenario_result(
                name="sip_minus_25",
                sip=max(scenario_base_sip * 0.75, 500.0),  # Ensure minimum 500 for 75% scenario
                target_amount=fire_target,
                current_savings=current_savings,
                expected_return=expected_return,
                age=age,
                original_target_age=retirement_age,
            ),
        ]

    # CRITICAL FIX: Improved priority order respecting FIRE priority
    priority_order: list[str] = [
        "establish_emergency_fund" if emergency_gap else None,
        "eliminate_high_debt" if monthly_income > 0 and monthly_emi > 0.3 * monthly_income else None,
        "increase_life_insurance" if insurance_gap else None,
        "invest_in_fire_and_goals",
    ]
    priority_order = [p for p in priority_order if p is not None]

    pre_conditions = {
        "required_emergency_fund": round(emergency_threshold, 2),
        "current_emergency_fund": round(current_savings, 2),
        "required_insurance": round(annual_income * 10, 2),
        "current_insurance": round(insurance_coverage, 2),
        "monthly_surplus": round(net_savings, 2),
    }

    priority_text = _build_priority_text(
        insurance_gap=insurance_gap,
        insurance_required=annual_income * 10,
        monthly_sip_fire=monthly_sip_fire,
        net_savings=net_savings,
    )

    next_steps = _build_next_steps(
        goal_status=goal_status,
        emergency_gap=emergency_gap,
        emergency_threshold=emergency_threshold,
        current_savings=current_savings,
        insurance_gap=insurance_gap,
        insurance_required=annual_income * 10,
        insurance_coverage=insurance_coverage,
        monthly_sip_fire=monthly_sip_fire,
    )

    explanation = _build_explanation(
        goal_status=goal_status,
        fire_target=fire_target,
        monthly_sip_required=minimum_sip_required,
        monthly_sip_selected=monthly_sip_fire,
        base_years=base_years,
        final_years=final_timeline_years,
        net_savings=net_savings,
        max_allowed_sip=max_fire_sip,
    )

    equity = max(100 - age, 50)
    debt = 100 - equity

    # CRITICAL FIX: Build response with validation checks
    response = {
        "fire_target": round(fire_target, 2),
        "years_to_retire": final_timeline_years,
        "monthly_sip_fire": round(monthly_sip_fire, 2),
        "minimum_sip_required": round(minimum_sip_required, 2),  # NEW: Always track required SIP
        "goal_plan": goal_plan,
        "monthly_plan": monthly_plan,  # Empty list for unrealistic goals
        "allocation": {"equity": int(equity), "debt": int(debt)},
        "emergency_gap": emergency_gap,
        "insurance_gap": insurance_gap,
        "tax_suggestions": tax_suggestions,
        "recommendation_flags": recommendation_flags,
        "retirement_age": retirement_age,
        "multiplier": round(multiplier, 2),
        "expected_return": round(expected_return, 4),
        "return_source": return_source,
        "inflation_rate": INFLATION_RATE,
        "safety_buffer": SAFETY_BUFFER,
        "fire_type": _fire_type(multiplier),
        "goal_status": goal_status,
        "explanation": explanation,
        "risk_flags": sorted(set(risk_flags)),
        "scenarios": scenarios,  # Empty list for unrealistic goals
        "priority_order": priority_order,
        "priority_text": priority_text,
        "next_steps": next_steps,
        "pre_conditions": pre_conditions,
        "timeline_adjusted": timeline_adjusted,
        "adjusted_timeline_years": final_timeline_years if timeline_adjusted else None,
        "new_target_date": _target_date_from_years(final_timeline_years),
    }

    # CRITICAL FIX: Mandatory consistency validation before returning
    _validate_response(response, goal_status, net_savings)
    
    return response

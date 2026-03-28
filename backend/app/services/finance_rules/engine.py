from typing import Any

from app.services.finance_rules.rules import (
    debt_ratio_rule,
    emergency_fund_rule,
    investment_presence_rule,
    savings_rate_rule,
)


SAVINGS_RATE_TARGET_MIN = 0.20
DEBT_RATIO_HIGH_THRESHOLD = 0.30
EMERGENCY_MONTHS_MIN = 3.0
LOAN_MAX_DEBT_RATIO = 0.30
SAFETY_BUFFER_RATE = 0.10
MIN_SAFETY_BUFFER = 5000.0


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _surplus_metrics(profile: Any) -> dict[str, float]:
    monthly_income = _safe_float(getattr(profile, "income", 0.0))
    monthly_expenses = _safe_float(getattr(profile, "expenses", 0.0))
    monthly_emi = _safe_float(getattr(profile, "emi", 0.0))

    available_surplus = monthly_income - monthly_expenses - monthly_emi
    safety_buffer_amount = max(monthly_income * SAFETY_BUFFER_RATE, MIN_SAFETY_BUFFER)
    investable_surplus = max(available_surplus - safety_buffer_amount, 0.0)

    return {
        "available_surplus": round(available_surplus, 2),
        "safety_buffer_amount": round(safety_buffer_amount, 2),
        "investable_surplus": round(investable_surplus, 2),
        "sip_to_surplus_ratio": (
            round(investable_surplus / available_surplus, 2) if available_surplus > 0 else 0.0
        ),
    }


def _confidence_level(profile: Any, metrics: dict[str, Any]) -> str:
    # Inputs are considered complete when core numeric fields are valid and positive where required.
    required_numbers = [
        getattr(profile, "income", None),
        getattr(profile, "expenses", None),
        getattr(profile, "savings", None),
        getattr(profile, "loans", None),
        getattr(profile, "emi", None),
    ]
    has_missing_values = any(value is None for value in required_numbers)
    if has_missing_values:
        return "Low"

    income = float(getattr(profile, "income", 0.0))
    expenses = float(getattr(profile, "expenses", 0.0))
    savings_rate = float(metrics.get("savings_rate", 0.0))
    debt_ratio = float(metrics.get("debt_ratio", 1.0))

    # Zero-income or zero-expense scenarios are valid but reduce certainty for advisory decisions.
    if income <= 0 or expenses <= 0:
        return "Medium"

    # Sanity envelope for derived metrics.
    if savings_rate < -1.0 or savings_rate > 2.0 or debt_ratio < 0.0 or debt_ratio > 2.0:
        return "Low"

    return "High"


def _decision_flags(metrics: dict[str, Any]) -> dict[str, Any]:
    savings_rate = float(metrics.get("savings_rate", 0.0))
    debt_ratio = float(metrics.get("debt_ratio", 1.0))
    emergency_months = float(
        metrics.get("emergency_months", metrics.get("emergency_fund_months", 0.0))
    )
    has_investments = bool(metrics.get("investment_presence", False))
    investable_surplus = float(metrics.get("investable_surplus", 0.0))
    available_surplus = float(metrics.get("available_surplus", 0.0))

    needs_emergency_fund = emergency_months < EMERGENCY_MONTHS_MIN
    high_debt = debt_ratio > DEBT_RATIO_HIGH_THRESHOLD
    should_increase_savings = savings_rate < SAVINGS_RATE_TARGET_MIN or needs_emergency_fund
    can_take_loan = (
        not high_debt
        and debt_ratio <= LOAN_MAX_DEBT_RATIO
        and emergency_months >= EMERGENCY_MONTHS_MIN
    )
    # Start investing only when basics are safe enough.
    has_investable_surplus = investable_surplus > 0
    should_invest = (
        (not has_investments)
        and (not high_debt)
        and (not needs_emergency_fund)
        and has_investable_surplus
    )

    investability_reasons: list[str] = []
    if has_investments:
        investability_reasons.append("already_investing")
    if high_debt:
        investability_reasons.append("debt_pressure")
    if needs_emergency_fund:
        investability_reasons.append("emergency_shortfall")
    if available_surplus <= 0:
        investability_reasons.append("no_monthly_surplus")
    elif not has_investable_surplus:
        investability_reasons.append("surplus_reserved_for_safety_buffer")

    if should_invest:
        investability_reasons.append("eligible_to_start_sip")

    return {
        "should_increase_savings": should_increase_savings,
        "should_invest": should_invest,
        "high_debt": high_debt,
        "can_take_loan": can_take_loan,
        "needs_emergency_fund": needs_emergency_fund,
        "investability_reasons": investability_reasons,
    }


def run_all_rules(profile: Any, investments: Any = None) -> dict[str, Any]:
    results = [
        savings_rate_rule(profile),
        emergency_fund_rule(profile),
        debt_ratio_rule(profile),
        investment_presence_rule(profile),
    ]

    result_map = {item["name"]: item for item in results}

    savings = result_map["savings_rate"]
    emergency = result_map["emergency_fund"]
    debt = result_map["debt_ratio"]
    investments_result = result_map["investment_presence"]
    surplus = _surplus_metrics(profile)

    has_external_investments = bool(investments) if investments is not None else bool(profile.has_investments)

    insights = [
        f"Savings rate is {savings['value'] * 100:.1f}% ({savings['status']})",
        f"Debt ratio is {debt['value'] * 100:.1f}% ({debt['status']})",
        f"Emergency fund covers {emergency['value']:.1f} months ({emergency['status']})",
        (
            "Investments are active (good)"
            if has_external_investments
            else "No investments found (warning)"
        ),
    ]

    return {
        "results": results,
        "insights": insights,
        "metrics": {
            "savings_rate": savings["value"],
            "debt_ratio": debt["value"],
            "emergency_months": emergency["value"],
            # Compatibility alias for older prompt consumers.
            "emergency_fund_months": emergency["value"],
            "investment_presence": bool(investments_result["value"]),
            "available_surplus": surplus["available_surplus"],
            "safety_buffer_amount": surplus["safety_buffer_amount"],
            "investable_surplus": surplus["investable_surplus"],
            "sip_to_surplus_ratio": surplus["sip_to_surplus_ratio"],
        },
        "flags": _decision_flags(
            {
                "savings_rate": savings["value"],
                "debt_ratio": debt["value"],
                "emergency_months": emergency["value"],
                "investment_presence": bool(investments_result["value"]),
                "available_surplus": surplus["available_surplus"],
                "investable_surplus": surplus["investable_surplus"],
            }
        ),
        "confidence": _confidence_level(
            profile,
            {
                "savings_rate": savings["value"],
                "debt_ratio": debt["value"],
                "emergency_months": emergency["value"],
                "investment_presence": bool(investments_result["value"]),
            },
        ),
    }

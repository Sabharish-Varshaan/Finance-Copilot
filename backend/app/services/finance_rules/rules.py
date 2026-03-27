from typing import Any


RuleResult = dict[str, Any]


def _safe_ratio(numerator: float, denominator: float, default: float) -> float:
    if denominator <= 0:
        return default
    return round(numerator / denominator, 4)


def savings_rate_rule(profile: Any) -> RuleResult:
    savings_rate = _safe_ratio(profile.income - profile.expenses, profile.income, 0.0)

    if savings_rate < 0.2:
        status = "poor"
    elif savings_rate <= 0.4:
        status = "average"
    elif savings_rate <= 0.6:
        status = "good"
    else:
        status = "excellent"

    if profile.income <= 0:
        message = "Income is zero, so savings rate defaults to 0% (poor)."
    else:
        message = f"Savings rate is {savings_rate * 100:.1f}% ({status})."

    return {
        "name": "savings_rate",
        "value": savings_rate,
        "status": status,
        "message": message,
    }


def emergency_fund_rule(profile: Any) -> RuleResult:
    months = _safe_ratio(profile.savings, profile.expenses, 99.0)

    if months < 3:
        status = "critical"
    elif months <= 6:
        status = "moderate"
    else:
        status = "strong"

    if profile.expenses <= 0:
        message = "Monthly expenses are zero, so emergency fund coverage is treated as strong."
    else:
        message = f"Emergency fund covers {months:.1f} months ({status})."

    return {
        "name": "emergency_fund",
        "value": months,
        "status": status,
        "message": message,
    }


def debt_ratio_rule(profile: Any) -> RuleResult:
    debt_ratio = _safe_ratio(profile.emi, profile.income, 1.0)

    if debt_ratio > 0.4:
        status = "dangerous"
    elif debt_ratio > 0.3:
        status = "high"
    elif debt_ratio > 0.2:
        status = "acceptable"
    else:
        status = "safe"

    if profile.income <= 0:
        message = "Income is zero, so debt ratio is treated as dangerous by default."
    else:
        message = f"Debt ratio is {debt_ratio * 100:.1f}% ({status})."

    return {
        "name": "debt_ratio",
        "value": debt_ratio,
        "status": status,
        "message": message,
    }


def investment_presence_rule(profile: Any) -> RuleResult:
    has_investments = bool(profile.has_investments)
    status = "good" if has_investments else "warning"
    message = (
        "Investment portfolio is active (good)."
        if has_investments
        else "No investments found (warning). Start a diversified investment plan."
    )

    return {
        "name": "investment_presence",
        "value": 1.0 if has_investments else 0.0,
        "status": status,
        "message": message,
    }

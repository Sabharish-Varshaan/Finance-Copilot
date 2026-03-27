from typing import Any

from app.services.finance_rules.rules import (
    debt_ratio_rule,
    emergency_fund_rule,
    investment_presence_rule,
    savings_rate_rule,
)


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
            "emergency_fund_months": emergency["value"],
            "investment_presence": bool(investments_result["value"]),
        },
        "flags": {
            "high_risk": debt["status"] in {"high", "dangerous"},
            "good_savings": savings["status"] in {"good", "excellent"},
            "needs_emergency_fund": emergency["status"] == "critical",
            "needs_investment_start": investments_result["status"] == "warning",
        },
    }

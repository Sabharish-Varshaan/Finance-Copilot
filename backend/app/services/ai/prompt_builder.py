from collections.abc import Sequence
from typing import Any


def _format_currency(value: float) -> str:
    return f"₹{value:,.0f}"


def _goals_block(goals: Sequence[Any]) -> str:
    if not goals:
        return "No active goals yet."

    lines: list[str] = []
    for goal in goals:
        lines.append(
            "- "
            f"{goal.title} ({goal.category}): target {_format_currency(goal.target_amount)}, "
            f"current {_format_currency(goal.current_amount)}, "
            f"monthly SIP {_format_currency(goal.monthly_sip_required)}, "
            f"deadline {goal.target_date}"
        )

    return "\n".join(lines)


def _history_messages(chat_history: Sequence[Any]) -> list[dict[str, str]]:
    recent_messages = sorted(chat_history, key=lambda item: (item.created_at, item.id))[-5:]
    formatted_messages: list[dict[str, str]] = []

    for item in recent_messages:
        content = (item.content or "").strip()
        if not content:
            continue

        role = "assistant" if item.role == "assistant" else "user"
        formatted_messages.append({"role": role, "content": content})

    return formatted_messages


def _result_map(financial_analysis: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not financial_analysis:
        return {}
    return {
        item.get("name"): item
        for item in financial_analysis.get("results", [])
        if isinstance(item, dict) and item.get("name")
    }


def _financial_analysis_block(financial_analysis: dict[str, Any] | None) -> str:
    if not financial_analysis:
        return ""

    metrics = financial_analysis.get("metrics", {})
    result_by_name = _result_map(financial_analysis)

    savings_rate = float(metrics.get("savings_rate", 0.0))
    debt_ratio = float(metrics.get("debt_ratio", 0.0))
    emergency_months = float(metrics.get("emergency_fund_months", 0.0))

    savings_status = result_by_name.get("savings_rate", {}).get("status", "unknown")
    debt_status = result_by_name.get("debt_ratio", {}).get("status", "unknown")
    emergency_status = result_by_name.get("emergency_fund", {}).get("status", "unknown")
    investments_status = result_by_name.get("investment_presence", {}).get("status", "unknown")

    return (
        "\n\nFinancial Analysis (System Generated):\n"
        f"- Savings rate: {savings_rate * 100:.1f}% ({savings_status})\n"
        f"- Debt ratio: {debt_ratio * 100:.1f}% ({debt_status})\n"
        f"- Emergency fund: {emergency_months:.1f} months ({emergency_status})\n"
        f"- Investment presence: {investments_status}\n"
        "\nSystem insights:\n"
        + "\n".join(f"- {line}" for line in financial_analysis.get("insights", []))
    )


def build_messages(
    user_profile: Any,
    goals: Sequence[Any],
    user_query: str,
    chat_history: Sequence[Any],
    financial_analysis: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    system_prompt = (
        "You are FinMentor, an Indian personal finance advisor. "
        "Give concise, practical, and personalized advice. "
        "Always quote amounts in INR (₹), avoid generic statements, and provide clear next actions. "
        "When relevant, include affordability checks, savings rate impact, and investment trade-offs. "
        "Use system-generated financial analysis as source-of-truth and anchor your advice to it. "
        "Do not ignore computed metrics or respond with generic suggestions. "
        "Format responses in clean markdown: use short headings, bullets, and bold for key numbers or actions."
    )

    profile_context = (
        "User Financial Profile:\n"
        f"- Monthly income: {_format_currency(user_profile.income)}\n"
        f"- Monthly expenses: {_format_currency(user_profile.expenses)}\n"
        f"- Current savings: {_format_currency(user_profile.savings)}\n"
        f"- Outstanding loans: {_format_currency(user_profile.loans)}\n"
        f"- Monthly EMI: {_format_currency(user_profile.emi)}\n"
        f"- Risk profile: {user_profile.risk_profile}\n"
        f"- Has investments: {user_profile.has_investments}\n"
        "Goals:\n"
        f"{_goals_block(goals)}"
        f"{_financial_analysis_block(financial_analysis)}"
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "Use this context for all advice in this turn.\n"
                f"{profile_context}"
            ),
        },
    ]

    messages.extend(_history_messages(chat_history))
    messages.append({"role": "user", "content": user_query.strip()})
    return messages
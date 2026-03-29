from collections.abc import Sequence
from typing import Any

from app.services.ai.retriever import retrieve_relevant_docs


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


def _yes_no(value: Any) -> str:
    return "YES" if bool(value) else "NO"


def _primary_priority(flags: dict[str, Any]) -> str:
    reasons = flags.get("investability_reasons", [])
    if isinstance(reasons, list) and "no_monthly_surplus" in reasons:
        return "Create monthly surplus before starting new SIP commitments"
    if bool(flags.get("high_debt")):
        return "Debt repayment and EMI reduction"
    if bool(flags.get("needs_emergency_fund")):
        return "Build emergency fund to minimum safety threshold"
    if bool(flags.get("should_increase_savings")):
        return "Increase savings rate"
    if bool(flags.get("should_invest")):
        return "Start investing with disciplined SIP"
    return "Maintain current allocation with periodic review"


def _metrics_section(financial_analysis: dict[str, Any] | None) -> str:
    if not financial_analysis:
        return "- Metrics unavailable"

    metrics = financial_analysis.get("metrics", {})
    result_by_name = _result_map(financial_analysis)
    savings_rate = float(metrics.get("savings_rate", 0.0))
    debt_ratio = float(metrics.get("debt_ratio", 0.0))
    emergency_months = float(metrics.get("emergency_months", metrics.get("emergency_fund_months", 0.0)))
    available_surplus = float(metrics.get("available_surplus", 0.0))
    safety_buffer_amount = float(metrics.get("safety_buffer_amount", 0.0))
    investable_surplus = float(metrics.get("investable_surplus", 0.0))

    savings_status = result_by_name.get("savings_rate", {}).get("status", "unknown")
    debt_status = result_by_name.get("debt_ratio", {}).get("status", "unknown")
    emergency_status = result_by_name.get("emergency_fund", {}).get("status", "unknown")
    investments_status = result_by_name.get("investment_presence", {}).get("status", "unknown")

    return (
        f"- Savings rate: {savings_rate * 100:.1f}% ({savings_status})\n"
        f"- Debt ratio: {debt_ratio * 100:.1f}% ({debt_status})\n"
        f"- Emergency fund: {emergency_months:.1f} months ({emergency_status})\n"
        f"- Investment presence: {investments_status}\n"
        f"- Available surplus: {_format_currency(available_surplus)} per month\n"
        f"- Safety buffer reserve: {_format_currency(safety_buffer_amount)} per month\n"
        f"- Investable surplus: {_format_currency(investable_surplus)} per month"
    )


def _flags_section(financial_analysis: dict[str, Any] | None) -> str:
    if not financial_analysis:
        return "- Decisions unavailable"

    flags = financial_analysis.get("flags", {})
    investability_reasons = flags.get("investability_reasons", [])
    reasons_text = ", ".join(str(item) for item in investability_reasons) if investability_reasons else "none"
    return (
        f"- should_increase_savings: {_yes_no(flags.get('should_increase_savings'))}\n"
        f"- should_invest: {_yes_no(flags.get('should_invest'))}\n"
        f"- high_debt: {_yes_no(flags.get('high_debt'))}\n"
        f"- can_take_loan: {_yes_no(flags.get('can_take_loan'))}\n"
        f"- needs_emergency_fund: {_yes_no(flags.get('needs_emergency_fund'))}\n"
        f"- investability_reasons: {reasons_text}"
    )


def _financial_analysis_block(financial_analysis: dict[str, Any] | None) -> str:
    if not financial_analysis:
        return ""

    flags = financial_analysis.get("flags", {})
    priority = _primary_priority(flags)
    confidence = str(financial_analysis.get("confidence", "Medium"))

    return (
        "\n\nFinancial Analysis (SYSTEM - MUST BE FOLLOWED):\n"
        + f"{_metrics_section(financial_analysis)}\n\n"
        "System Decisions:\n"
        + f"{_flags_section(financial_analysis)}\n\n"
        "Primary Priority:\n"
        f"- {priority}\n"
        f"- Confidence: {confidence}"
    )


def _fire_plan_summary(fire_plan: dict[str, Any] | None) -> str:
    if not fire_plan:
        return ""

    fire_target = float(fire_plan.get("fire_target", 0.0))
    monthly_sip_fire = float(fire_plan.get("monthly_sip_fire", 0.0))
    years_to_retire = int(fire_plan.get("years_to_retire", 0))

    goal_entries: list[str] = []
    for goal in fire_plan.get("goal_plan", []):
        if not isinstance(goal, dict):
            continue
        name = str(goal.get("name", "Goal"))
        monthly_sip = float(goal.get("monthly_sip", 0.0))
        goal_entries.append(f"{name} {_format_currency(monthly_sip)} SIP")

    goals_text = ", ".join(goal_entries) if goal_entries else "No active goal SIPs"
    return (
        f"FIRE target: {_format_currency(fire_target)}\n"
        f"Years to retire: {years_to_retire}\n"
        f"SIP: {_format_currency(monthly_sip_fire)}/month\n"
        f"Goals: {goals_text}"
    )


def _user_context_block(user_context: dict[str, Any] | None) -> str:
    """Format full user context (profile, investments, goals, FIRE plan) for AI prompt."""
    if not user_context:
        return ""

    lines: list[str] = []

    # Profile context
    profile = user_context.get("profile", {})
    if profile:
        lines.append("USER FINANCIAL CONTEXT:")
        lines.append(f"- Age: {int(profile.get('age', 0))} years")
        lines.append(f"- Monthly income: {_format_currency(float(profile.get('monthly_income', 0.0)))}")
        lines.append(f"- Monthly expenses: {_format_currency(float(profile.get('monthly_expenses', 0.0)))}")
        lines.append(f"- Monthly EMI: {_format_currency(float(profile.get('monthly_emi', 0.0)))}")
        lines.append(f"- Current savings: {_format_currency(float(profile.get('current_savings', 0.0)))}")
        lines.append(f"- Insurance coverage: {_format_currency(float(profile.get('insurance_coverage', 0.0)))}")
        lines.append(f"- Outstanding loans: {_format_currency(float(profile.get('outstanding_loans', 0.0)))}")
        lines.append(f"- Risk profile: {str(profile.get('risk_profile', 'moderate'))}")

    # Investment context
    investments = user_context.get("investments", {})
    if investments and investments.get("total_amount", 0.0) > 0:
        lines.append("")
        lines.append("INVESTMENT ALLOCATION:")
        lines.append(f"- Total investments: {_format_currency(float(investments.get('total_amount', 0.0)))}")
        lines.append(f"  - Equity: {_format_currency(float(investments.get('equity_amount', 0.0)))} ({float(investments.get('equity_percent', 0.0)):.1f}%)")
        lines.append(f"  - Debt: {_format_currency(float(investments.get('debt_amount', 0.0)))} ({float(investments.get('debt_percent', 0.0)):.1f}%)")
        lines.append(f"  - Gold: {_format_currency(float(investments.get('gold_amount', 0.0)))} ({float(investments.get('gold_percent', 0.0)):.1f}%)")

    # FIRE plan context
    fire_plan = user_context.get("fire_plan", {})
    if fire_plan and fire_plan.get("fire_target", 0.0) > 0:
        lines.append("")
        lines.append("FIRE PLAN STATUS:")
        lines.append(f"- FIRE target: {_format_currency(float(fire_plan.get('fire_target', 0.0)))}")
        lines.append(f"- Monthly FIRE SIP: {_format_currency(float(fire_plan.get('monthly_sip_fire', 0.0)))}")
        lines.append(f"- Available monthly surplus: {_format_currency(float(fire_plan.get('available_surplus', 0.0)))}")
        lines.append(f"- Remaining surplus (after FIRE): {_format_currency(float(fire_plan.get('remaining_surplus', 0.0)))}")
        lines.append(f"- Investable for goals: {_format_currency(float(fire_plan.get('investable_surplus', 0.0)))}")
        lines.append(f"- Years to retirement: {int(fire_plan.get('years_to_retire', 0))}")
        lines.append(f"- Goals feasible: {'YES' if fire_plan.get('goals_feasible') else 'NO'}")

    # Goals context
    goals = user_context.get("goals", [])
    if goals:
        lines.append("")
        lines.append("ACTIVE GOALS:")
        for goal in goals:
            if str(goal.get("status", "")).lower() == "active":
                lines.append(f"- {goal.get('title', 'Goal')} ({goal.get('category', 'Other')})")
                lines.append(f"  Target: {_format_currency(float(goal.get('target_amount', 0.0)))} | Current: {_format_currency(float(goal.get('current_amount', 0.0)))}")
                lines.append(f"  Monthly SIP: {_format_currency(float(goal.get('monthly_sip', 0.0)))} | Target: {goal.get('target_date', 'N/A')}")

    return "\n".join(lines) if lines else ""


def build_messages(
    user_profile: Any,
    goals: Sequence[Any],
    user_query: str,
    chat_history: Sequence[Any],
    financial_analysis: dict[str, Any] | None = None,
    fire_plan: dict[str, Any] | None = None,
    user_context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    metrics_section = _metrics_section(financial_analysis)
    flags_section = _flags_section(financial_analysis)
    priority_section = _primary_priority(financial_analysis.get("flags", {}) if financial_analysis else {})
    retrieved_docs = retrieve_relevant_docs(user_query, k=3)
    knowledge_block = "\n".join([f"- {doc['content']}" for doc in retrieved_docs])
    if not knowledge_block:
        knowledge_block = "- No additional finance knowledge retrieved for this query."
    fire_plan_summary = _fire_plan_summary(fire_plan)
    fire_plan_block = f"FIRE PLAN:\n{fire_plan_summary}\n\n" if fire_plan_summary else ""
    
    # USER CONTEXT INJECTION: Build comprehensive user context block
    user_context_block = _user_context_block(user_context) if user_context else ""
    user_context_section = f"{user_context_block}\n\n" if user_context_block else ""

    system_prompt = (
        "You are an AI personal finance advisor for Indian users.\n\n"
        "You are a decision-making advisor, not a chatbot.\n\n"
        f"{user_context_section}"
        "Financial Analysis (SYSTEM - MUST BE FOLLOWED):\n"
        f"{metrics_section}\n\n"
        "System Decisions:\n"
        f"{flags_section}\n\n"
        "Primary Priority:\n"
        f"- {priority_section}\n\n"
        f"{fire_plan_block}"
        "RELEVANT FINANCIAL KNOWLEDGE:\n"
        f"{knowledge_block}\n\n"
        "INSTRUCTIONS:\n"
        "1. Follow system decisions exactly and never contradict flags.\n"
        "2. Do not suggest actions that conflict with system decisions.\n"
        "3. Avoid repeating the same phrases across responses.\n"
        "4. Focus only on what is relevant to the user's query.\n"
        "5. Do not explain all metrics unless necessary.\n"
        "6. Keep responses concise and non-redundant.\n"
        "7. Do not use: consider, might, maybe, could.\n"
        "8. Use direct language: You should / You should NOT.\n"
        "9. If savings rate is high, do NOT suggest increasing savings.\n"
        "10. If debt is high, strongly discourage taking new loans.\n"
        "11. If no investments, prioritize investing only after debt and emergency constraints are handled.\n"
        "12. If a decision is allowed (YES):\n"
        "- Clearly state it is allowed\n"
        "- Explain concrete trade-offs (not soft phrases like 'proceed with caution')\n"
        "- Recommend the smarter long-term choice\n"
        "13. If a decision is allowed but not optimal:\n"
        "- State it is allowed\n"
        "- But guide the user toward better financial behavior\n"
        "14. You MUST align your answer with the Primary Priority above.\n"
        "15. Only reference metrics that are relevant to the user's question.\n"
        "16. When giving advice, always explain the financial trade-off in practical terms (impact on savings, investments, or financial flexibility).\n"
        "17. Use strong, professional wording:\n"
        "- 'this will reduce your financial flexibility'\n"
        "- 'this will slow your wealth growth'\n"
        "- 'this will limit your investment capacity'\n"
        "Avoid vague phrases like 'be careful' or 'proceed cautiously'.\n\n"
        "18. Always validate user statements against system financial metrics.\n"
        "19. If a user assumption conflicts with system metrics (e.g., claims high debt when debt is low):\n"
        "- Start with: 'Based on your financial data...' and then state the correct metric reality\n"
        "- Base the answer ONLY on system metrics\n"
        "- Do NOT reinforce incorrect assumptions\n"
        "20. When a user assumption is incorrect:\n"
        "- Correct first, then provide the right guidance\n"
        "- Keep the correction clear, respectful, and direct\n"
        "21. System financial metrics are the single source of truth. User-provided assumptions must not override them.\n"
        "22. If a financial action is risky or suboptimal:\n"
        "- Use strong language: 'You should NOT do this' or 'This is not advisable'\n"
        "- Avoid weak phrasing like 'you can if needed' or 'proceed with caution'\n"
        "23. When multiple valid financial standards exist, use ranges instead of fixed numbers (example: maintain 6-12 months of emergency fund depending on income stability).\n"
        "24. For high-risk scenarios (especially taking loans to invest), always give a strong NO and clearly explain the downside risk.\n"
        "25. Use natural, conversational advisor language. Avoid robotic phrasing while staying concise and decisive.\n\n"
        "26. For SIP affordability questions, always cite three numbers: required SIP, investable surplus, and monthly shortfall/surplus.\n"
        "27. If required SIP is higher than investable surplus, clearly state it is not feasible now and suggest one concrete adjustment path.\n"
        "28. Do not use a fixed percent cap to judge SIP affordability. Base guidance on monthly surplus after expenses, EMI, and safety buffer.\n\n"
        "RESPONSE STYLE:\n"
        "- Start with a clear, strong decision\n"
        "- Explain concrete financial consequences (not warnings or cautions)\n"
        "- Keep explanation brief and relevant (2–3 lines max)\n"
        "- Provide 2–3 actionable steps if useful\n"
        "- Sound like a real financial advisor, not a generic chatbot\n\n"
        "FINAL INSTRUCTION:\n"
        "Be deterministic, concise, advisor-grade, and unapologetically clear about trade-offs."
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
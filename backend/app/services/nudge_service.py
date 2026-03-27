from app.models.financial_profile import FinancialProfile
from app.schemas.finance import MoneyHealthScoreResponse


def generate_nudges(profile: FinancialProfile, score_result: MoneyHealthScoreResponse) -> list[str]:
    nudges: list[str] = []

    if score_result.breakdown.emergency_fund_months < 6:
        nudges.append("Increase emergency fund to at least 6 months of expenses.")

    if score_result.breakdown.debt_ratio >= 0.3:
        nudges.append("Reduce EMI burden to below 30% of monthly income.")

    if score_result.breakdown.savings_rate < 0.2:
        nudges.append("Improve savings rate by budgeting and automating monthly transfers.")

    if not profile.has_investments:
        nudges.append("Start a diversified investment plan aligned with your risk profile.")

    if not nudges:
        nudges.append("Great job. Maintain consistency and review your plan monthly.")

    return nudges

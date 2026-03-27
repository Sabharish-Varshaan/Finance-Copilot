from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.financial_profile import FinancialProfile
from app.models.user import User
from app.schemas.finance import FinancialProfileUpsert, MoneyHealthBreakdown, MoneyHealthScoreResponse


def upsert_financial_profile(db: Session, user: User, payload: FinancialProfileUpsert) -> FinancialProfile:
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == user.id).first()

    if profile is None:
        profile = FinancialProfile(user_id=user.id, **payload.model_dump())
        db.add(profile)
    else:
        for field, value in payload.model_dump().items():
            setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


def get_financial_profile(db: Session, user: User) -> FinancialProfile:
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial profile not found. Please create one first.",
        )
    return profile


def _grade_from_score(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    if score >= 35:
        return "D"
    return "E"


def calculate_money_health_score(profile: FinancialProfile) -> MoneyHealthScoreResponse:
    emergency_fund_months = round(profile.savings / profile.expenses, 2) if profile.expenses > 0 else 99.0
    debt_ratio = round(profile.emi / profile.income, 4) if profile.income > 0 else 1.0
    savings_rate = (
        round((profile.income - profile.expenses) / profile.income, 4) if profile.income > 0 else 0.0
    )

    emergency_score = min(30.0, (emergency_fund_months / 6.0) * 30.0)

    if debt_ratio <= 0.3:
        debt_score = 25.0
    else:
        debt_score = max(0.0, 25.0 * (1 - min((debt_ratio - 0.3) / 0.7, 1.0)))

    savings_score = max(0.0, min(30.0, (savings_rate / 0.2) * 30.0))
    investment_score = 15.0 if profile.has_investments else 0.0

    component_scores = {
        "emergency_fund": round(emergency_score, 2),
        "debt_ratio": round(debt_score, 2),
        "savings_rate": round(savings_score, 2),
        "investment_presence": round(investment_score, 2),
    }

    total_score = round(sum(component_scores.values()), 2)

    breakdown = MoneyHealthBreakdown(
        emergency_fund_months=emergency_fund_months,
        debt_ratio=debt_ratio,
        savings_rate=savings_rate,
        investment_presence=profile.has_investments,
        component_scores=component_scores,
    )

    return MoneyHealthScoreResponse(score=total_score, grade=_grade_from_score(total_score), breakdown=breakdown)

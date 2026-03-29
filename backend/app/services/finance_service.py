from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.financial_profile import FinancialProfile
from app.models.user import User
from app.models.user_investment import UserInvestment
from app.schemas.finance import (
    FinancialProfileRead,
    FinancialProfileUpsert,
    MoneyHealthBreakdown,
    MoneyHealthScoreResponse,
    UserInvestmentCreate,
    UserInvestmentRead,
)


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


def get_latest_user_investment(db: Session, user_id: int) -> UserInvestment | None:
    return (
        db.query(UserInvestment)
        .filter(UserInvestment.user_id == user_id)
        .order_by(UserInvestment.created_at.desc())
        .first()
    )


def get_financial_profile_read(db: Session, user: User) -> FinancialProfileRead:
    profile = get_financial_profile(db, user)
    latest_investment = get_latest_user_investment(db, user.id)
    response = FinancialProfileRead.model_validate(profile)
    response.latest_investment = (
        UserInvestmentRead.model_validate(latest_investment) if latest_investment else None
    )
    return response


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


def _calculate_insurance_score(coverage: float, annual_income: float) -> float:
    """Calculate insurance score (0-10). 10x annual income = perfect score."""
    if annual_income <= 0:
        return 0.0
    recommended = annual_income * 10
    if coverage >= recommended:
        return 10.0
    return min(10.0, (coverage / recommended) * 10.0)


def _calculate_emergency_score_0_10(savings: float, monthly_expenses: float) -> float:
    """Calculate emergency fund score (0-10). 6 months expenses = perfect score."""
    if monthly_expenses <= 0:
        return 0.0
    months = savings / monthly_expenses
    if months >= 6:
        return 10.0
    return min(10.0, (months / 6.0) * 10.0)


def _calculate_debt_score_0_10(emi: float, monthly_income: float) -> float:
    """Calculate debt ratio score (0-10). Low EMI/income ratio = perfect."""
    if monthly_income <= 0:
        return 0.0
    ratio = emi / monthly_income
    if ratio <= 0.3:
        return 10.0
    if ratio >= 1.0:
        return 0.0
    return 10.0 * (1 - ((ratio - 0.3) / 0.7))


def _calculate_savings_score_0_10(income: float, expenses: float) -> float:
    """Calculate savings rate score (0-10). 20% savings rate = perfect score."""
    if income <= 0:
        return 0.0
    savings_rate = (income - expenses) / income
    if savings_rate >= 0.2:
        return 10.0
    if savings_rate <= 0:
        return 0.0
    return min(10.0, (savings_rate / 0.2) * 10.0)


def _calculate_investment_score_0_10(
    profile: FinancialProfile, investment: UserInvestment | None = None
) -> float:
    """
    Calculate investment score (0-10) with quality + quantity.
    Quantity: relative to annual income (0-5)
    Quality: alignment with risk profile (0-5)
    """
    if not investment or investment.total_amount == 0:
        return 0.0

    annual_income = profile.income
    if annual_income <= 0:
        return 0.0

    # Quantity: 0-5 points based on investment relative to income
    quantity_score = min(5.0, (investment.total_amount / annual_income) * 5.0)

    # Quality: 0-5 points based on alignment with risk profile
    total = investment.total_amount
    equity_pct = (investment.equity_amount / total * 100) if total > 0 else 0
    debt_pct = (investment.debt_amount / total * 100) if total > 0 else 0
    gold_pct = (investment.gold_amount / total * 100) if total > 0 else 0

    # Expected allocation by risk profile
    expected = {
        "conservative": {"equity": 40, "debt": 50, "gold": 10},
        "moderate": {"equity": 60, "debt": 30, "gold": 10},
        "aggressive": {"equity": 80, "debt": 15, "gold": 5},
    }

    expected_alloc = expected.get(profile.risk_profile, expected["moderate"])
    deviation = (
        abs(equity_pct - expected_alloc["equity"])
        + abs(debt_pct - expected_alloc["debt"])
        + abs(gold_pct - expected_alloc["gold"])
    ) / 3.0

    # Quality score drops with higher deviation
    quality_score = max(0.0, 5.0 - (deviation / 10.0))

    return round(quantity_score + quality_score, 2)


def _get_latest_fire_plan(db: Session, user_id: int):
    """Fetch the most recent FIRE plan for a user. Returns None if not exists."""
    from app.models.fire_plan import FirePlan

    return db.query(FirePlan).filter(FirePlan.user_id == user_id).order_by(FirePlan.created_at.desc()).first()


def _calculate_retirement_score_0_10(db: Session, profile: FinancialProfile) -> float:
    """
    Calculate retirement score (0-10).
    If FIRE plan exists: 0-5 for SIP commitment + 0-5 for progress toward target.
    Else: based on savings rate estimate.
    """
    fire_plan = _get_latest_fire_plan(db, profile.user_id)

    if fire_plan:
        # Use FIRE plan data: SIP commitment (0-5) + progress (0-5)
        monthly_surplus = (profile.income - profile.expenses) / 1.0 if profile.income > 0 else 0
        if monthly_surplus <= 0:
            commitment_score = 0.0
        else:
            # Score based on how much of surplus is allocated to SIP
            sip_ratio = fire_plan.monthly_sip_fire / monthly_surplus
            commitment_score = min(5.0, sip_ratio * 5.0)

        # Progress score: how much progress toward FIRE target.
        # `assets_saved` is a legacy field; use current_savings plus latest investment corpus.
        latest_investment = (
            db.query(UserInvestment)
            .filter(UserInvestment.user_id == profile.user_id)
            .order_by(UserInvestment.created_at.desc())
            .first()
        )
        saved_assets = float(getattr(fire_plan, "current_savings", 0.0) or 0.0)
        if latest_investment:
            saved_assets += float(latest_investment.total_amount or 0.0)

        if saved_assets > 0 and fire_plan.fire_target > 0:
            progress_ratio = saved_assets / fire_plan.fire_target
            progress_score = min(5.0, progress_ratio * 5.0)
        else:
            progress_score = 0.0

        return round(commitment_score + progress_score, 2)
    else:
        # Fallback: estimate from savings rate
        if profile.income <= 0:
            return 0.0
        savings_rate = (profile.income - profile.expenses) / profile.income
        if savings_rate >= 0.2:
            return 10.0
        return min(10.0, (savings_rate / 0.2) * 10.0)


def _compute_six_dimensions(
    db: Session, profile: FinancialProfile, investment: UserInvestment | None = None
) -> tuple[dict[str, float], str, list[str]]:
    """
    Compute all 6 dimensions and return breakdown dict, category, and insights.
    """
    dimensions = {
        "emergency": _calculate_emergency_score_0_10(profile.savings, profile.expenses / 12.0),
        "insurance": _calculate_insurance_score(profile.insurance_coverage, profile.income),
        "debt": _calculate_debt_score_0_10(profile.emi, profile.income / 12.0),
        "investment": _calculate_investment_score_0_10(profile, investment),
        "retirement": _calculate_retirement_score_0_10(db, profile),
        "savings": _calculate_savings_score_0_10(profile.income, profile.expenses),
    }

    # Aggregate score (average of 6)
    aggregate_score = sum(dimensions.values()) / len(dimensions)

    # Category based on aggregate
    if aggregate_score >= 8.0:
        category = "Excellent"
    elif aggregate_score >= 6.5:
        category = "Good"
    elif aggregate_score >= 5.0:
        category = "Needs Improvement"
    else:
        category = "Poor"

    # Generate insights (identify weak areas)
    weak_areas = [(k, v) for k, v in dimensions.items() if v < 5.0]
    weak_areas.sort(key=lambda x: x[1])  # Sort by score (lowest first)

    insights = []
    for dim_name, score in weak_areas[:2]:  # Top 2 weak areas
        if dim_name == "emergency":
            insights.append("Increase emergency fund to 6 months of expenses")
        elif dim_name == "insurance":
            insights.append("Get life insurance coverage of 10x annual income")
        elif dim_name == "debt":
            insights.append("Reduce monthly EMI to below 30% of income")
        elif dim_name == "investment":
            insights.append("Start investing according to your risk profile")
        elif dim_name == "retirement":
            insights.append("Create or update your retirement plan using FIRE planner")
        elif dim_name == "savings":
            insights.append("Increase savings rate to 20% of income")

    return dimensions, category, insights


def calculate_money_health_score(
    profile: FinancialProfile, db: Session | None = None, include_fire: bool = False
) -> MoneyHealthScoreResponse:
    """
    Calculate money health score with legacy (0-100) and new (0-10, 6D) scoring.
    If include_fire=true and db provided, fetch latest FIRE plan for retirement dimension.
    """
    # Legacy 0-100 scoring
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

    # New 0-10 6D scoring
    score_0_10 = 0.0
    category = ""
    dimensions_dict = {}
    insights = []
    
    if db:
        # Fetch latest investment
        investment = (
            db.query(UserInvestment)
            .filter(UserInvestment.user_id == profile.user_id)
            .order_by(UserInvestment.created_at.desc())
            .first()
        )
        
        dimensions_dict, category, insights = _compute_six_dimensions(db, profile, investment)
        score_0_10 = round(sum(dimensions_dict.values()) / len(dimensions_dict), 2)

    breakdown = MoneyHealthBreakdown(
        emergency_fund_months=emergency_fund_months,
        debt_ratio=debt_ratio,
        savings_rate=savings_rate,
        investment_presence=profile.has_investments,
        component_scores=component_scores,
        emergency_score=dimensions_dict.get("emergency", 0.0),
        insurance_score=dimensions_dict.get("insurance", 0.0),
        debt_score=dimensions_dict.get("debt", 0.0),
        investment_score=dimensions_dict.get("investment", 0.0),
        retirement_score=dimensions_dict.get("retirement", 0.0),
        savings_score=dimensions_dict.get("savings", 0.0),
    )

    return MoneyHealthScoreResponse(
        score=total_score,
        grade=_grade_from_score(total_score),
        breakdown=breakdown,
        score_0_10=score_0_10,
        category=category,
        dimensions=dimensions_dict,
        insights=insights,
    )


def create_user_investment(db: Session, user: User, payload: UserInvestmentCreate) -> UserInvestmentRead:
    """Create a new user investment record (preserves history; always creates new record)."""
    investment = UserInvestment(
        user_id=user.id,
        total_amount=payload.total_amount,
        equity_amount=payload.equity_amount,
        debt_amount=payload.debt_amount,
        gold_amount=payload.gold_amount,
    )
    db.add(investment)
    
    # Update profile's has_investments flag if total_amount > 0
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == user.id).first()
    if profile and payload.total_amount > 0:
        profile.has_investments = True
    
    db.commit()
    db.refresh(investment)
    return UserInvestmentRead.model_validate(investment)

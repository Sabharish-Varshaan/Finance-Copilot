from datetime import date
from math import pow
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalUpdate
from app.services.goals.goal_planner import get_expected_return, plan_goal

GoalStatusFilter = Literal["active", "paused", "completed", "all"]


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def _future_value(monthly_sip: float, months: int, annual_return: float) -> float:
    if monthly_sip <= 0 or months <= 0:
        return 0.0
    monthly_rate = annual_return / 12
    if monthly_rate <= 0:
        return monthly_sip * months
    return monthly_sip * (((1 + monthly_rate) ** months - 1) / monthly_rate)


def calculate_monthly_sip(
    target_amount: float,
    current_amount: float,
    expected_annual_return: float,
    target_date: date,
) -> float:
    remaining = max(target_amount - current_amount, 0)
    months = _months_between(date.today(), target_date)

    if months <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target date must be in the future")

    if remaining <= 0:
        return 0.0

    monthly_rate = expected_annual_return / 12

    if monthly_rate == 0:
        return round(remaining / months, 2)

    denominator = pow(1 + monthly_rate, months) - 1
    if denominator <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid SIP calculation inputs")

    sip = remaining * monthly_rate / denominator
    return round(sip, 2)


def create_goal(db: Session, user: User, payload: GoalCreate) -> dict[str, Any]:
    profile = user.financial_profile
    risk_profile = str(getattr(profile, "risk_profile", "moderate") or "moderate")
    expected_return = get_expected_return(risk_profile)

    sip = calculate_monthly_sip(
        target_amount=payload.target_amount,
        current_amount=payload.current_amount,
        expected_annual_return=expected_return,
        target_date=payload.target_date,
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "valid": False,
                "reason": "Update your income, expenses, and EMI in onboarding so we can calculate a feasible SIP",
                "required_sip": round(sip, 2),
                "available_savings": 0.0,
                "available_surplus": 0.0,
                "safety_buffer_amount": 0.0,
                "investable_surplus": 0.0,
                "total_existing_sip": 0.0,
                "shortfall_amount": round(sip, 2),
                "sip_to_investable_surplus_ratio": None,
                "reason_codes": ["missing_financial_profile"],
                "suggested_sip": 0.0,
                "suggestions": [
                    "Complete onboarding with income, expense, and EMI details",
                    "Extend timeline",
                    "Reduce goal amount",
                ],
            },
        )

    existing_goals = (
        db.query(Goal)
        .filter(Goal.user_id == user.id, Goal.status == "active")
        .order_by(Goal.id.asc())
        .all()
    )

    try:
        planned_goal = plan_goal(
            profile={
                "monthly_income": profile.income,
                "monthly_expenses": profile.expenses,
                "monthly_emi": profile.emi,
                "savings": profile.savings,
                "risk_profile": profile.risk_profile,
            },
            goal={
                "title": payload.title,
                "target_amount": payload.target_amount,
                "current_amount": payload.current_amount,
                "target_date": payload.target_date,
            },
            existing_goals=existing_goals,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "valid": False,
                "reason": str(exc),
                "required_sip": round(sip, 2),
                "available_savings": round(profile.income - profile.expenses - profile.emi, 2),
                "suggested_sip": 0.0,
                "suggestions": [
                    "Increase timeline",
                    "Increase SIP",
                    "Reduce goal amount",
                ],
            },
        ) from exc

    adjusted_target_date = payload.target_date
    adjusted_target_date_str = planned_goal.get("adjusted_target_date")
    if isinstance(adjusted_target_date_str, str):
        adjusted_target_date = date.fromisoformat(adjusted_target_date_str)

    planned_expected_return = float(planned_goal.get("expected_return", expected_return))
    planned_final_sip = float(planned_goal.get("final_sip", sip))
    months_to_target = _months_between(date.today(), adjusted_target_date)
    remaining_target = max(payload.target_amount - payload.current_amount, 0.0)
    achievable_value = _future_value(planned_final_sip, months_to_target, planned_expected_return)
    if achievable_value < remaining_target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "valid": False,
                "reason": "Goal plan is not mathematically achievable with current SIP and timeline",
                "required_sip": round(sip, 2),
                "available_savings": round(profile.income - profile.expenses - profile.emi, 2),
                "suggested_sip": 0.0,
                "suggestions": [
                    "Increase timeline",
                    "Increase SIP",
                    "Reduce goal amount",
                ],
            },
        )

    goal = Goal(
        user_id=user.id,
        category=payload.category,
        title=payload.title,
        target_amount=payload.target_amount,
        current_amount=payload.current_amount,
        expected_annual_return=planned_expected_return,
        target_date=adjusted_target_date,
        monthly_sip_required=planned_final_sip,
    )

    db.add(goal)
    db.commit()
    db.refresh(goal)
    return {
        "goal": goal,
        "planning": planned_goal,
    }


def list_goals(db: Session, user: User, status: GoalStatusFilter = "active") -> list[Goal]:
    query = db.query(Goal).filter(Goal.user_id == user.id)
    if status != "all":
        query = query.filter(Goal.status == status)
    return query.order_by(Goal.created_at.desc()).all()


def update_goal(db: Session, user: User, goal_id: int, payload: GoalUpdate) -> Goal:
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(goal, field, value)

    recalc_fields = {"target_amount", "current_amount", "expected_annual_return", "target_date"}
    should_recalculate_sip = recalc_fields.intersection(updates.keys()) and "monthly_sip_required" not in updates
    if should_recalculate_sip:
        goal.monthly_sip_required = calculate_monthly_sip(
            target_amount=goal.target_amount,
            current_amount=goal.current_amount,
            expected_annual_return=goal.expected_annual_return,
            target_date=goal.target_date,
        )

    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, user: User, goal_id: int) -> None:
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    db.delete(goal)
    db.commit()

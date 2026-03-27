from datetime import date
from math import pow
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalUpdate
from app.services.goals.goal_validator import build_auto_adjustment, validate_goal


RISK_DEFAULT_RETURNS = {
    "conservative": 0.08,
    "moderate": 0.12,
    "aggressive": 0.15,
}

GoalStatusFilter = Literal["active", "paused", "completed", "all"]


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


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


def create_goal(db: Session, user: User, payload: GoalCreate) -> Goal:
    profile = user.financial_profile
    expected_return = payload.expected_annual_return
    if profile and payload.expected_annual_return == 0.12:
        expected_return = RISK_DEFAULT_RETURNS.get(profile.risk_profile, payload.expected_annual_return)

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
                "reason": "Complete onboarding to enable feasibility validation",
                "required_sip": round(sip, 2),
                "available_savings": 0.0,
                "suggested_sip": 0.0,
                "suggestions": [
                    "Complete onboarding with income and expense details",
                    "Extend timeline",
                    "Reduce goal amount",
                ],
            },
        )

    months = _months_between(date.today(), payload.target_date)
    years = months / 12
    remaining_amount = max(payload.target_amount - payload.current_amount, 0)

    existing_goals = (
        db.query(Goal)
        .filter(Goal.user_id == user.id, Goal.status == "active")
        .order_by(Goal.id.asc())
        .all()
    )

    validation = validate_goal(
        profile={
            "monthly_income": profile.income,
            "monthly_expenses": profile.expenses,
            "monthly_emi": profile.emi,
        },
        goal={
            "target_amount": remaining_amount,
            "years": years,
        },
        existing_goals=[{"monthly_sip": goal.monthly_sip_required} for goal in existing_goals],
    )

    if not validation.get("valid", False):
        if payload.smart_adjust:
            auto_adjustment = build_auto_adjustment(
                target_amount=remaining_amount,
                feasible_sip=max(float(validation.get("suggested_sip", 0.0)), 0.0),
            )
            if auto_adjustment is not None:
                validation["auto_adjustment"] = auto_adjustment

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=validation)

    goal = Goal(
        user_id=user.id,
        category=payload.category,
        title=payload.title,
        target_amount=payload.target_amount,
        current_amount=payload.current_amount,
        expected_annual_return=expected_return,
        target_date=payload.target_date,
        monthly_sip_required=sip,
    )

    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


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

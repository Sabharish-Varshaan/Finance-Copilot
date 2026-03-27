from datetime import date
import json
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.fire_plan import FireGoal, FirePlan
from app.models.user import User
from app.schemas.fire import FirePlanHistoryItem, FirePlanRecord, FirePlanRequest
from app.services.finance_service import get_financial_profile
from app.services.fire.fire_planner import generate_fire_plan
from app.services.goal_service import list_goals


def _profile_from_model(profile) -> dict:
    return {
        "age": int(profile.age),
        "monthly_income": float(profile.income),
        "monthly_expenses": float(profile.expenses),
        "current_savings": float(profile.savings),
        "insurance_coverage": float(getattr(profile, "insurance_coverage", 0.0) or 0.0),
        "monthly_emi": float(profile.emi),
        "risk_profile": str(profile.risk_profile),
    }


def _years_from_target_date(target_date: date) -> int:
    days_remaining = (target_date - date.today()).days
    if days_remaining <= 0:
        return 0
    return max(ceil(days_remaining / 365), 1)


def _goals_from_models(goals: list) -> list[dict]:
    mapped_goals: list[dict] = []
    for goal in goals:
        mapped_goals.append(
            {
                "name": str(goal.title),
                "amount": float(goal.target_amount),
                "years": _years_from_target_date(goal.target_date),
            }
        )
    return mapped_goals


def _to_plan_response(plan: FirePlan) -> FirePlanRecord:
    goal_plan = [
        {
            "name": goal.name,
            "target": float(goal.target_amount),
            "monthly_sip": float(goal.monthly_sip),
        }
        for goal in sorted(plan.goals, key=lambda item: item.id)
    ]
    monthly_plan = json.loads(plan.monthly_plan) if plan.monthly_plan else []
    tax_suggestions = json.loads(plan.tax_suggestions) if plan.tax_suggestions else []

    return FirePlanRecord(
        id=plan.id,
        fire_target=float(plan.fire_target),
        years_to_retire=int(plan.years_to_retire),
        monthly_sip_fire=float(plan.monthly_sip_fire),
        goal_plan=goal_plan,
        monthly_plan=monthly_plan,
        allocation={"equity": int(plan.allocation_equity), "debt": int(plan.allocation_debt)},
        emergency_gap=bool(plan.emergency_gap),
        insurance_gap=bool(plan.insurance_gap),
        tax_suggestions=tax_suggestions,
        recommendation_flags=[flag for flag in plan.recommendation_flags.split(",") if flag],
        retirement_age=int(plan.retirement_age),
        multiplier=float(plan.multiplier),
        created_at=plan.created_at,
    )


def generate_fire_plan_for_user(db: Session, user: User, payload: FirePlanRequest) -> FirePlanRecord:
    profile_model = get_financial_profile(db, user)
    goal_models = list_goals(db, user, status="active")

    profile_data = _profile_from_model(profile_model)
    if payload.profile is not None:
        profile_data = payload.profile.model_dump()

    goals_data = _goals_from_models(goal_models)
    if payload.goals is not None:
        goals_data = [goal.model_dump() for goal in payload.goals]
    goals_data = sorted(goals_data, key=lambda item: int(item.get("years", 0)))

    fire_plan = generate_fire_plan(
        profile=profile_data,
        goals=goals_data,
        retirement_age=payload.retirement_age,
        multiplier=payload.multiplier if payload.multiplier is not None else 33,
    )

    allocation = fire_plan.get("allocation", {})
    plan_row = FirePlan(
        user_id=user.id,
        age=int(profile_data.get("age", 0)),
        monthly_income=float(profile_data.get("monthly_income", 0.0)),
        monthly_expenses=float(profile_data.get("monthly_expenses", 0.0)),
        current_savings=float(profile_data.get("current_savings", 0.0)),
        insurance_coverage=float(profile_data.get("insurance_coverage", 0.0)),
        monthly_emi=float(profile_data.get("monthly_emi", 0.0)),
        risk_profile=str(profile_data.get("risk_profile", "moderate")),
        retirement_age=int(fire_plan.get("retirement_age", payload.retirement_age)),
        multiplier=float(fire_plan.get("multiplier", payload.multiplier or 33)),
        inflation_rate=float(fire_plan.get("inflation_rate", 0.06)),
        safety_buffer=float(fire_plan.get("safety_buffer", 1.2)),
        recommendation_flags=",".join(fire_plan.get("recommendation_flags", [])),
        fire_target=float(fire_plan.get("fire_target", 0.0)),
        years_to_retire=int(fire_plan.get("years_to_retire", 0)),
        monthly_sip_fire=float(fire_plan.get("monthly_sip_fire", 0.0)),
        allocation_equity=int(allocation.get("equity", 0)),
        allocation_debt=int(allocation.get("debt", 0)),
        emergency_gap=bool(fire_plan.get("emergency_gap", False)),
        insurance_gap=bool(fire_plan.get("insurance_gap", False)),
        tax_suggestions=json.dumps(fire_plan.get("tax_suggestions", [])),
        monthly_plan=json.dumps(fire_plan.get("monthly_plan", [])),
    )
    db.add(plan_row)
    db.flush()

    for goal_input, goal_output in zip(goals_data, fire_plan.get("goal_plan", []), strict=False):
        db.add(
            FireGoal(
                fire_plan_id=plan_row.id,
                name=str(goal_output.get("name", goal_input.get("name", "Goal"))),
                target_amount=float(goal_output.get("target", goal_input.get("amount", 0.0))),
                years=int(goal_input.get("years", 0)),
                monthly_sip=float(goal_output.get("monthly_sip", 0.0)),
            )
        )

    db.commit()
    db.refresh(plan_row)
    return _to_plan_response(plan_row)


def list_fire_plan_history(db: Session, user: User) -> list[FirePlanHistoryItem]:
    rows = (
        db.query(FirePlan)
        .filter(FirePlan.user_id == user.id)
        .order_by(FirePlan.created_at.desc(), FirePlan.id.desc())
        .all()
    )

    return [
        FirePlanHistoryItem(
            id=row.id,
            fire_target=float(row.fire_target),
            monthly_sip_fire=float(row.monthly_sip_fire),
            years_to_retire=int(row.years_to_retire),
            created_at=row.created_at,
        )
        for row in rows
    ]


def get_fire_plan_by_id(db: Session, user: User, plan_id: int) -> FirePlanRecord:
    row = db.query(FirePlan).filter(FirePlan.id == plan_id, FirePlan.user_id == user.id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FIRE plan not found")
    return _to_plan_response(row)

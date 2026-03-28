from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.fire import FirePlanHistoryItem, FirePlanRecord, FirePlanRequest
from app.services.fire_service import generate_fire_plan_for_user, get_current_fire_plan, get_fire_plan_by_id, list_fire_plan_history

router = APIRouter(prefix="/fire-plan", tags=["fire"])


@router.post("/create", response_model=FirePlanRecord)
def create_fire_plan(
    payload: FirePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return generate_fire_plan_for_user(db, current_user, payload)


@router.get("/history", response_model=list[FirePlanHistoryItem])
def get_fire_plan_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_fire_plan_history(db, current_user)


@router.get("/current", response_model=FirePlanRecord)
def get_current_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the most recently created FIRE plan for the user."""
    return get_current_fire_plan(db, current_user)


@router.get("/{plan_id}", response_model=FirePlanRecord)
def get_fire_plan_detail(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_fire_plan_by_id(db, current_user, plan_id)

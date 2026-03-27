from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalRead, GoalUpdate
from app.services.goal_service import create_goal, list_goals, update_goal

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=GoalRead)
def create_goal_endpoint(
    payload: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_goal(db, current_user, payload)


@router.get("", response_model=list[GoalRead])
def list_goals_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_goals(db, current_user)


@router.patch("/{goal_id}", response_model=GoalRead)
def update_goal_endpoint(
    goal_id: int,
    payload: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_goal(db, current_user, goal_id, payload)

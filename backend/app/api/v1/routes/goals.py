from fastapi import APIRouter, Depends, Response, status
from fastapi import Query
from sqlalchemy.orm import Session
from typing import Literal

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalRead, GoalUpdate
from app.services.goal_service import create_goal, delete_goal, list_goals, update_goal

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
    status: Literal["active", "paused", "completed", "all"] = Query(default="active"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_goals(db, current_user, status=status)


@router.patch("/{goal_id}", response_model=GoalRead)
def update_goal_endpoint(
    goal_id: int,
    payload: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_goal(db, current_user, goal_id, payload)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal_endpoint(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_goal(db, current_user, goal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

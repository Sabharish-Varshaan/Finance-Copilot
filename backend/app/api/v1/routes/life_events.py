from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.life_event import LifeEventRequest, LifeEventResponse
from app.services.life_event_service import analyze_life_event, apply_life_event

router = APIRouter(prefix="/life-events", tags=["life-events"])


@router.post("/analyze", response_model=LifeEventResponse)
def analyze_life_event_endpoint(
    payload: LifeEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return analyze_life_event(db, current_user, payload)


@router.post("/apply", response_model=LifeEventResponse)
def apply_life_event_endpoint(
    payload: LifeEventRequest,
    analysis: LifeEventResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return apply_life_event(db, current_user, payload, analysis)

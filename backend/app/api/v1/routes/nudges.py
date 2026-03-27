from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.nudge import NudgeResponse
from app.services.finance_service import calculate_money_health_score, get_financial_profile
from app.services.nudge_service import generate_nudges

router = APIRouter(prefix="/nudges", tags=["nudges"])


@router.get("", response_model=NudgeResponse)
def get_nudges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = get_financial_profile(db, current_user)
    score_result = calculate_money_health_score(profile)
    nudges = generate_nudges(profile, score_result)
    return NudgeResponse(nudges=nudges)

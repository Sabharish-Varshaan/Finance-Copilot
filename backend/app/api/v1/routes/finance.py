from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.finance import FinancialProfileRead, FinancialProfileUpsert, MoneyHealthScoreResponse
from app.services.finance_service import (
    calculate_money_health_score,
    get_financial_profile,
    upsert_financial_profile,
)

router = APIRouter(prefix="/finance", tags=["finance"])


@router.put("/profile", response_model=FinancialProfileRead)
def upsert_profile(
    payload: FinancialProfileUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return upsert_financial_profile(db, current_user, payload)


@router.get("/profile", response_model=FinancialProfileRead)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_financial_profile(db, current_user)


@router.get("/health-score", response_model=MoneyHealthScoreResponse)
def get_money_health_score(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = get_financial_profile(db, current_user)
    return calculate_money_health_score(profile)

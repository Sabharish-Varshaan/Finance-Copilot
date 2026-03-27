from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


GoalCategory = Literal["retirement", "house", "travel", "education", "other"]


class GoalCreate(BaseModel):
    category: GoalCategory
    title: str = Field(min_length=2, max_length=150)
    target_amount: float = Field(gt=0)
    current_amount: float = Field(default=0, ge=0)
    target_date: date
    expected_annual_return: float = Field(default=0.12, ge=0, le=0.3)
    smart_adjust: bool = False


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=150)
    target_amount: float | None = Field(default=None, gt=0)
    current_amount: float | None = Field(default=None, ge=0)
    target_date: date | None = None
    expected_annual_return: float | None = Field(default=None, ge=0, le=0.3)
    monthly_sip_required: float | None = Field(default=None, ge=0)
    status: Literal["active", "completed", "paused"] | None = None


class GoalRead(BaseModel):
    id: int
    user_id: int
    category: str
    title: str
    target_amount: float
    current_amount: float
    expected_annual_return: float
    target_date: date
    monthly_sip_required: float
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

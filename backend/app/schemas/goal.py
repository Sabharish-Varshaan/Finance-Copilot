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
    source: str = "manual"  # "fire" or "manual"
    fire_plan_id: int | None = None
    monthly_sip_allocated: float = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GoalPlanningSummary(BaseModel):
    goal_name: str
    raw_sip: float
    calculated_sip: float
    ai_sip: float
    final_sip: float
    sip: float
    timeline: float
    original_timeline: float
    adjusted_timeline: float
    timeline_extended: bool
    timeline_adjusted: bool
    adjusted: bool
    reason: str
    ai_reasoning: str
    backend_limit: float
    existing_goals_sip_total: float
    adjustment_reason_codes: list[str]
    original_target_date: date
    adjusted_target_date: date
    new_target_date: date
    net_savings: float
    max_allowed_new_sip: float
    expected_return: float
    monthly_return: float
    return_assumption_note: str
    adjustment_options: list[str]


class GoalCreateResponse(BaseModel):
    goal: GoalRead
    planning: GoalPlanningSummary

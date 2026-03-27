from datetime import datetime

from pydantic import BaseModel, Field


class FireProfileInput(BaseModel):
    age: int = Field(ge=18, le=100)
    monthly_income: float = Field(ge=0)
    monthly_expenses: float = Field(ge=0)
    current_savings: float = Field(ge=0)
    insurance_coverage: float = Field(default=0, ge=0)
    monthly_emi: float = Field(ge=0)
    risk_profile: str = Field(default="moderate", min_length=3, max_length=32)


class FireGoalInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    amount: float = Field(gt=0)
    years: int = Field(gt=0)


class FirePlanRequest(BaseModel):
    profile: FireProfileInput | None = None
    goals: list[FireGoalInput] | None = None
    retirement_age: int = Field(default=55, ge=40, le=75)
    multiplier: float | None = Field(default=None, ge=25, le=50)


class FireGoalPlan(BaseModel):
    name: str
    target: float
    monthly_sip: float


class FireAllocation(BaseModel):
    equity: int
    debt: int


class FireMonthlyMilestone(BaseModel):
    month: int
    corpus: float


class FirePlanResponse(BaseModel):
    fire_target: float
    years_to_retire: int
    monthly_sip_fire: float
    goal_plan: list[FireGoalPlan]
    monthly_plan: list[FireMonthlyMilestone]
    allocation: FireAllocation
    emergency_gap: bool
    insurance_gap: bool
    tax_suggestions: list[str] = []
    recommendation_flags: list[str] = []
    retirement_age: int
    multiplier: float


class FirePlanRecord(FirePlanResponse):
    id: int
    created_at: datetime


class FirePlanHistoryItem(BaseModel):
    id: int
    fire_target: float
    monthly_sip_fire: float
    years_to_retire: int
    created_at: datetime

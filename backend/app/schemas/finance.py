from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RiskProfile = Literal["conservative", "moderate", "aggressive"]


class FinancialProfileUpsert(BaseModel):
    age: int = Field(ge=18, le=100)
    income: float = Field(ge=0)
    expenses: float = Field(ge=0)
    savings: float = Field(ge=0)
    insurance_coverage: float = Field(default=0, ge=0)
    loans: float = Field(ge=0)
    emi: float = Field(ge=0)
    risk_profile: RiskProfile
    has_investments: bool = False


class FinancialProfileRead(FinancialProfileUpsert):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MoneyHealthBreakdown(BaseModel):
    emergency_fund_months: float
    debt_ratio: float
    savings_rate: float
    investment_presence: bool
    component_scores: dict[str, float]


class MoneyHealthScoreResponse(BaseModel):
    score: float
    grade: str
    breakdown: MoneyHealthBreakdown

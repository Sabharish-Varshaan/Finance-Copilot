from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


RiskProfile = Literal["conservative", "moderate", "aggressive"]


class UserInvestmentBreakdown(BaseModel):
    equity_amount: float = Field(ge=0, description="Amount invested in equity instruments")
    debt_amount: float = Field(ge=0, description="Amount invested in debt instruments")
    gold_amount: float = Field(ge=0, description="Amount invested in gold/commodity")


class UserInvestmentCreate(UserInvestmentBreakdown):
    total_amount: float = Field(ge=0, description="Total investment amount")

    @field_validator("total_amount")
    @classmethod
    def validate_total_amount(cls, v: float, info) -> float:
        data = info.data
        expected = data.get("equity_amount", 0) + data.get("debt_amount", 0) + data.get("gold_amount", 0)
        if abs(v - expected) > 0.01:  # Allow small floating point errors
            raise ValueError(f"total_amount ({v}) must equal sum of breakdown ({expected})")
        return v


class UserInvestmentRead(UserInvestmentCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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
    latest_investment: UserInvestmentRead | None = None

    model_config = {"from_attributes": True}


class MoneyHealthBreakdown(BaseModel):
    emergency_fund_months: float
    debt_ratio: float
    savings_rate: float
    investment_presence: bool
    component_scores: dict[str, float]
    # 6D scores (0-10 scale)
    emergency_score: float = 0.0
    insurance_score: float = 0.0
    debt_score: float = 0.0
    investment_score: float = 0.0
    retirement_score: float = 0.0
    savings_score: float = 0.0


class MoneyHealthScoreResponse(BaseModel):
    # Legacy 0-100 score and grade
    score: float
    grade: str
    breakdown: MoneyHealthBreakdown
    # New 0-10 score with 6D breakdown
    score_0_10: float = 0.0
    category: str = ""  # "Excellent" | "Good" | "Needs Improvement" | "Poor"
    dimensions: dict[str, float] = {}  # 6D breakdown
    insights: list[str] = []  # 2-3 actionable recommendations

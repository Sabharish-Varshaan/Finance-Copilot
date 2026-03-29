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
    expected_return: float | None = Field(default=None)
    investment_mode: str | None = Field(default=None)


class FireGoalPlan(BaseModel):
    name: str
    target: float
    target_amount_original: float = 0
    target_amount_inflated: float = 0
    inflation_impact: float = 0
    monthly_sip: float
    monthly_sip_required: float = 0
    status: str = "achievable"
    status_description: str = ""
    underfunded: bool = False
    timeline_adjusted: bool = False
    adjusted_years: int | None = None


class FireAllocation(BaseModel):
    equity: int
    debt: int


class FireMonthlyMilestone(BaseModel):
    month: int
    corpus: float


class FireScenario(BaseModel):
    name: str
    sip: float
    years_to_target: int | None = None
    target_age: int | None = None
    achieved_age: int | None = None
    original_target_age: int | None = None
    status: str


class FirePreConditions(BaseModel):
    required_emergency_fund: float
    current_emergency_fund: float
    required_insurance: float
    current_insurance: float
    monthly_surplus: float
    remaining_surplus: float = 0.0
    investable_surplus: float = 0.0


class FireInvestmentBreakdownItem(BaseModel):
    type: str
    amount: float


class FireInvestmentAssetPlan(BaseModel):
    percentage: int
    amount: float
    breakdown: list[FireInvestmentBreakdownItem] = Field(default_factory=list)


class FireInvestmentAllocation(BaseModel):
    equity: FireInvestmentAssetPlan
    debt: FireInvestmentAssetPlan
    gold: FireInvestmentAssetPlan


class FireInvestmentPlan(BaseModel):
    total_investment: float
    mode: str
    allocation: FireInvestmentAllocation
    explanation: str


class FireInvestmentBreakdown(BaseModel):
    equity: float = 0.0
    debt: float = 0.0
    gold: float = 0.0


class FireAllocationSplit(BaseModel):
    fire_percentage: float = 0.0
    goal_percentage: float = 0.0


class FirePlanResponse(BaseModel):
    fire_target: float
    years_to_retire: int
    monthly_sip_fire: float
    fire_sip: float = 0.0
    goal_sip_total: float = 0.0
    available_surplus: float = 0.0
    remaining_surplus: float = 0.0
    investable_surplus: float = 0.0
    required_goal_sip: float = 0.0
    goals_feasible: bool = False
    allocation_split: FireAllocationSplit = Field(default_factory=FireAllocationSplit)
    minimum_sip_required: float = Field(default=0.0, description="Minimum SIP needed for FIRE target")
    total_assets: float = 0.0
    investment_breakdown: FireInvestmentBreakdown = Field(default_factory=FireInvestmentBreakdown)
    goal_plan: list[FireGoalPlan]
    monthly_plan: list[FireMonthlyMilestone]
    allocation: FireAllocation
    emergency_gap: bool
    insurance_gap: bool
    tax_suggestions: list[str] = Field(default_factory=list)
    recommendation_flags: list[str] = Field(default_factory=list)
    retirement_age: int
    multiplier: float
    expected_return: float
    return_source: str
    goal_status: str = "achievable"
    explanation: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    scenarios: list[FireScenario] = Field(default_factory=list)
    priority_order: list[str] = Field(default_factory=list)
    priority_text: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    investment_plan: FireInvestmentPlan | None = None
    pre_conditions: FirePreConditions | None = None
    timeline_adjusted: bool = False
    adjusted_timeline_years: int | None = None
    new_target_date: str | None = None
    # Investment portfolio integration
    investment_portfolio_current: float = 0.0
    fire_target_adjusted: float = 0.0
    fire_gap: float = 0.0
    portfolio_projected_value: float = 0.0


class FirePlanRecord(FirePlanResponse):
    id: int
    created_at: datetime


class FirePlanHistoryItem(BaseModel):
    id: int
    fire_target: float
    monthly_sip_fire: float
    years_to_retire: int
    created_at: datetime

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


LifeEventType = Literal[
    "bonus",
    "inheritance",
    "marriage",
    "child",
    "job_loss",
    "salary_increase",
]


class LifeEventRequest(BaseModel):
    event_type: LifeEventType
    amount: float = Field(default=0.0, ge=0)
    date: date


class FireTimelineComparison(BaseModel):
    years_before: int | None = None
    years_after: int | None = None


class EventAnalysis(BaseModel):
    impact: str
    recommended_allocation: dict[str, float]
    updated_plan: dict
    action_steps: list[str]
    ai_response: str
    fire_timeline: FireTimelineComparison = Field(default_factory=FireTimelineComparison)


class LifeEventResponse(BaseModel):
    mode: Literal["simulation", "applied"] = "simulation"
    total_assets_before: float = 0.0
    total_assets_after: float = 0.0
    debt_before: float = 0.0
    debt_after: float = 0.0
    investments_before: dict[str, float] = Field(default_factory=lambda: {"equity": 0.0, "debt": 0.0, "gold": 0.0})
    investments_after: dict[str, float] = Field(default_factory=lambda: {"equity": 0.0, "debt": 0.0, "gold": 0.0})
    event_analysis: EventAnalysis

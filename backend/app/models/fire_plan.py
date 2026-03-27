from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base


class FirePlan(Base):
    __tablename__ = "fire_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    age: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_income: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_expenses: Mapped[float] = mapped_column(Float, nullable=False)
    current_savings: Mapped[float] = mapped_column(Float, nullable=False)
    insurance_coverage: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    monthly_emi: Mapped[float] = mapped_column(Float, nullable=False)
    risk_profile: Mapped[str] = mapped_column(String(32), nullable=False)
    retirement_age: Mapped[int] = mapped_column(Integer, nullable=False, default=55)
    multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=33.0)
    inflation_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.06)
    safety_buffer: Mapped[float] = mapped_column(Float, nullable=False, default=1.2)
    recommendation_flags: Mapped[str] = mapped_column(Text, nullable=False, default="")

    fire_target: Mapped[float] = mapped_column(Float, nullable=False)
    years_to_retire: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_sip_fire: Mapped[float] = mapped_column(Float, nullable=False)
    allocation_equity: Mapped[int] = mapped_column(Integer, nullable=False)
    allocation_debt: Mapped[int] = mapped_column(Integer, nullable=False)
    emergency_gap: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    insurance_gap: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tax_suggestions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    monthly_plan: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="fire_plans")
    goals: Mapped[list["FireGoal"]] = relationship(
        "FireGoal", back_populates="plan", cascade="all, delete-orphan"
    )


class FireGoal(Base):
    __tablename__ = "fire_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fire_plan_id: Mapped[int] = mapped_column(ForeignKey("fire_plans.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    years: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_sip: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plan: Mapped["FirePlan"] = relationship("FirePlan", back_populates="goals")
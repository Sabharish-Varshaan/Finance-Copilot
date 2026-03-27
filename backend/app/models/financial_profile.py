from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    age: Mapped[int] = mapped_column(Integer, nullable=False)
    income: Mapped[float] = mapped_column(Float, nullable=False)
    expenses: Mapped[float] = mapped_column(Float, nullable=False)
    savings: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    loans: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    emi: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    risk_profile: Mapped[str] = mapped_column(String(32), nullable=False)
    has_investments: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="financial_profile")

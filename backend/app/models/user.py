from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    financial_profile: Mapped["FinancialProfile | None"] = relationship(
        "FinancialProfile", back_populates="user", uselist=False
    )
    goals: Mapped[list["Goal"]] = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="user", cascade="all, delete-orphan"
    )
    fire_plans: Mapped[list["FirePlan"]] = relationship(
        "FirePlan", back_populates="user", cascade="all, delete-orphan"
    )

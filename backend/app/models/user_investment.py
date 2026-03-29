from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base


class UserInvestment(Base):
    __tablename__ = "user_investments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    equity_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    debt_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    gold_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="investments")

    def __init__(self, user_id: int, total_amount: float, equity_amount: float, debt_amount: float, gold_amount: float):
        self.user_id = user_id
        self.total_amount = total_amount
        self.equity_amount = equity_amount
        self.debt_amount = debt_amount
        self.gold_amount = gold_amount

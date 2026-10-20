"""Budgets and savings goals."""

import uuid
from datetime import date

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import BudgetPeriod, SavingsGoalStatus, enum_column


class Budget(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A spending limit. Actual spend is always calculated, never stored.

    ``category_id = NULL`` means an overall budget across all expense categories.
    """

    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint(
            "warning_threshold > 0 AND warning_threshold <= critical_threshold "
            "AND critical_threshold <= 100",
            name="thresholds_ordered",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency_code: Mapped[str] = mapped_column(
        String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False
    )
    period: Mapped[BudgetPeriod] = mapped_column(
        enum_column(BudgetPeriod, "budget_period"), nullable=False, default=BudgetPeriod.MONTHLY
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    warning_threshold: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=80)
    critical_threshold: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=90)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class SavingsGoal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "savings_goals"
    __table_args__ = (
        CheckConstraint("target_minor > 0", name="target_positive"),
        CheckConstraint("saved_minor >= 0", name="saved_non_negative"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    saved_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    currency_code: Mapped[str] = mapped_column(
        String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False
    )
    target_date: Mapped[date | None] = mapped_column(Date)
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL")
    )
    status: Mapped[SavingsGoalStatus] = mapped_column(
        enum_column(SavingsGoalStatus, "savings_goal_status"),
        nullable=False,
        default=SavingsGoalStatus.ACTIVE,
    )

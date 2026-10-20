"""Recurring templates and their scheduled bill occurrences.

A ``RecurringTransaction`` is a template. Each ``Bill`` is one dated
occurrence. The unique constraint on (recurring_id, due_date) is what makes
the daily generation job idempotent: running it twice creates no duplicates.
"""

import uuid
from datetime import date

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    BillStatus,
    PaymentMethod,
    RecurrenceFrequency,
    TransactionType,
    enum_column,
)


class RecurringTransaction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "recurring_transactions"
    __table_args__ = (CheckConstraint("amount_minor > 0", name="amount_positive"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    dest_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT")
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT")
    )

    type: Mapped[TransactionType] = mapped_column(
        enum_column(TransactionType, "recurring_transaction_type"), nullable=False
    )
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency_code: Mapped[str] = mapped_column(
        String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False
    )
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        enum_column(PaymentMethod, "recurring_payment_method")
    )
    vendor: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    frequency: Mapped[RecurrenceFrequency] = mapped_column(
        enum_column(RecurrenceFrequency, "recurrence_frequency"), nullable=False
    )
    interval_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    next_occurrence: Mapped[date] = mapped_column(Date, nullable=False)
    reminder_days: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=3)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    account = relationship("Account", foreign_keys=[account_id])
    destination_account = relationship("Account", foreign_keys=[dest_account_id])
    category = relationship("Category")
    bills = relationship(
        "Bill", back_populates="recurring", cascade="all, delete-orphan", order_by="Bill.due_date"
    )


class Bill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "bills"
    __table_args__ = (
        UniqueConstraint("recurring_id", "due_date", name="uq_bills_recurring_due_date"),
        CheckConstraint("amount_minor > 0", name="amount_positive"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recurring_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recurring_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency_code: Mapped[str] = mapped_column(
        String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[BillStatus] = mapped_column(
        enum_column(BillStatus, "bill_status"), nullable=False, default=BillStatus.PENDING
    )
    paid_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL")
    )

    recurring = relationship("RecurringTransaction", back_populates="bills")

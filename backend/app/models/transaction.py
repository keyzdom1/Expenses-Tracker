"""Transactions, tags and the transaction/tag link table."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentMethod, TransactionType, enum_column


class Transaction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A single financial movement.

    Rules encoded here and in the service layer:
      * amounts are positive minor units; ``type`` gives the direction
      * a transfer has a destination account and no other type may have one
      * rows are soft-deleted via ``deleted_at`` and then excluded everywhere
    """

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint(
            "(type = 'transfer' AND dest_account_id IS NOT NULL "
            "AND dest_account_id <> account_id) "
            "OR (type <> 'transfer' AND dest_account_id IS NULL)",
            name="transfer_destination_rule",
        ),
        Index("ix_transactions_user_date", "user_id", text("transaction_date DESC")),
        Index("ix_transactions_user_category", "user_id", "category_id"),
        Index("ix_transactions_user_account", "user_id", "account_id"),
        Index("ix_transactions_user_deleted", "user_id", "deleted_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
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
        enum_column(TransactionType, "transaction_type"), nullable=False
    )
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency_code: Mapped[str] = mapped_column(
        String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        enum_column(PaymentMethod, "payment_method")
    )
    vendor: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    # A refund may point at the expense it reverses.
    refund_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    account: Mapped["Account"] = relationship(foreign_keys=[account_id])
    destination_account: Mapped["Account | None"] = relationship(foreign_keys=[dest_account_id])
    category: Mapped["Category | None"] = relationship()
    tags: Mapped[list["Tag"]] = relationship(
        secondary="transaction_tags", back_populates="transactions"
    )


class Tag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_tags_user_name"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str | None] = mapped_column(String(20))

    transactions: Mapped[list["Transaction"]] = relationship(
        secondary="transaction_tags", back_populates="tags"
    )


class TransactionTag(Base):
    __tablename__ = "transaction_tags"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )

"""Financial accounts (cash, bank, cards, mobile wallets)."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AccountType, enum_column


class Account(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A wallet/account. Balance is always derived, never stored.

    Credit-card accounts hold a negative balance representing money owed.
    Accounts with transactions are archived (``is_active=False``), not deleted.
    """

    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_accounts_user_name"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[AccountType] = mapped_column(enum_column(AccountType, "account_type"), nullable=False)
    currency_code: Mapped[str] = mapped_column(
        String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False, default="NGN"
    )
    opening_balance_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

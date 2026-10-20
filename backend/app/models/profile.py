"""User profile and preferences (linked to the Supabase Auth user id)."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Theme, enum_column


class Profile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One row per Supabase Auth user; `id` equals the token's `sub` claim."""

    __tablename__ = "profiles"

    email: Mapped[str | None] = mapped_column(String(320))
    full_name: Mapped[str | None] = mapped_column(String(120))
    avatar_url: Mapped[str | None] = mapped_column(String(500))

    preferences: Mapped["UserPreferences"] = relationship(
        back_populates="profile", uselist=False, cascade="all, delete-orphan"
    )


class UserPreferences(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    currency_code: Mapped[str] = mapped_column(
        String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False, default="NGN"
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Africa/Lagos")
    theme: Mapped[Theme] = mapped_column(
        enum_column(Theme, "theme"), nullable=False, default=Theme.SYSTEM
    )
    notify_budget_thresholds: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_upcoming_bills: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_recurring_events: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    profile: Mapped["Profile"] = relationship(back_populates="preferences")

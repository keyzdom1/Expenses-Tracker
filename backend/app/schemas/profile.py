"""Profile and preference schemas."""

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Theme


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str | None
    full_name: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency_code: str
    timezone: str
    theme: Theme
    notify_budget_thresholds: bool
    notify_upcoming_bills: bool
    notify_recurring_events: bool


class PreferencesUpdate(BaseModel):
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = Field(default=None, max_length=64)
    theme: Theme | None = None
    notify_budget_thresholds: bool | None = None
    notify_upcoming_bills: bool | None = None
    notify_recurring_events: bool | None = None

    @field_validator("currency_code")
    @classmethod
    def normalise_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Unknown IANA timezone") from exc
        return value


class AccountDeleteRequest(BaseModel):
    """Typed confirmation so a stray request cannot delete an account."""

    confirm: str = Field(min_length=1, max_length=10)

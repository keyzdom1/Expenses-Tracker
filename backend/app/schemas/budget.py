"""Budget request/response schemas."""

import uuid
from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import BudgetPeriod


class BudgetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category_id: uuid.UUID | None = None
    amount_minor: int = Field(gt=0)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    period: BudgetPeriod = BudgetPeriod.MONTHLY
    start_date: date | None = None
    end_date: date | None = None
    warning_threshold: int = Field(default=80, ge=1, le=100)
    critical_threshold: int = Field(default=90, ge=1, le=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name cannot be blank.")
        return cleaned

    @field_validator("currency_code")
    @classmethod
    def upper_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @model_validator(mode="after")
    def check_thresholds(self):
        if self.warning_threshold > self.critical_threshold:
            raise ValueError("The warning threshold must not exceed the critical threshold.")
        if self.period == BudgetPeriod.CUSTOM and self.end_date is None:
            raise ValueError("A custom budget needs an end date.")
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValueError("The end date must be on or after the start date.")
        return self


class BudgetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category_id: uuid.UUID | None = None
    amount_minor: int | None = Field(default=None, gt=0)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    period: BudgetPeriod | None = None
    start_date: date | None = None
    end_date: date | None = None
    warning_threshold: int | None = Field(default=None, ge=1, le=100)
    critical_threshold: int | None = Field(default=None, ge=1, le=100)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name cannot be blank.")
        return cleaned

    @field_validator("currency_code")
    @classmethod
    def upper_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class BudgetOut(BaseModel):
    id: uuid.UUID
    name: str
    category_id: uuid.UUID | None
    category_name: str | None
    amount_minor: int
    currency_code: str
    period: BudgetPeriod
    start_date: date
    end_date: date | None
    warning_threshold: int
    critical_threshold: int
    is_active: bool
    period_start: date
    period_end: date
    spent_minor: int
    remaining_minor: int
    percent_used: float
    state: str

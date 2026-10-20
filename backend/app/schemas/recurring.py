"""Recurring templates and bill schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import (
    BillStatus,
    PaymentMethod,
    RecurrenceFrequency,
    TransactionType,
)
from app.schemas.transaction import AccountRef, CategoryRef


class RecurringCreate(BaseModel):
    type: TransactionType
    amount_minor: int = Field(gt=0)
    account_id: uuid.UUID
    dest_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    payment_method: PaymentMethod | None = None
    vendor: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    frequency: RecurrenceFrequency
    interval_count: int = Field(default=1, ge=1, le=12)
    start_date: date
    end_date: date | None = None
    reminder_days: int = Field(default=3, ge=0, le=30)

    @field_validator("vendor", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def check_dates(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("The end date must be on or after the start date.")
        return self


class RecurringUpdate(BaseModel):
    type: TransactionType | None = None
    amount_minor: int | None = Field(default=None, gt=0)
    account_id: uuid.UUID | None = None
    dest_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    payment_method: PaymentMethod | None = None
    vendor: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    frequency: RecurrenceFrequency | None = None
    interval_count: int | None = Field(default=None, ge=1, le=12)
    start_date: date | None = None
    end_date: date | None = None
    reminder_days: int | None = Field(default=None, ge=0, le=30)
    is_active: bool | None = None


class RecurringOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: TransactionType
    amount_minor: int
    currency_code: str
    payment_method: PaymentMethod | None
    vendor: str | None
    description: str | None
    frequency: RecurrenceFrequency
    interval_count: int
    start_date: date
    end_date: date | None
    next_occurrence: date
    reminder_days: int
    is_active: bool
    account: AccountRef
    destination_account: AccountRef | None
    category: CategoryRef | None
    created_at: datetime


class BillOut(BaseModel):
    id: uuid.UUID
    recurring_id: uuid.UUID
    due_date: date
    amount_minor: int
    currency_code: str
    status: BillStatus
    paid_transaction_id: uuid.UUID | None
    type: TransactionType
    vendor: str | None
    description: str | None
    account_name: str
    destination_account_name: str | None
    category_name: str | None

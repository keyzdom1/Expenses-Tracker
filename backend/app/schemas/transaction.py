"""Transaction request/response schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import CategoryKind, PaymentMethod, TransactionType

MAX_MINOR_UNITS = 9_000_000_000_000_000_000  # BIGINT upper bound


class TransactionCreate(BaseModel):
    type: TransactionType
    amount_minor: int = Field(gt=0, le=MAX_MINOR_UNITS)
    account_id: uuid.UUID
    dest_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    transaction_date: date
    occurred_at: datetime | None = None
    payment_method: PaymentMethod | None = None
    vendor: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    refund_of_id: uuid.UUID | None = None
    tag_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("currency_code")
    @classmethod
    def upper_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("vendor", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class TransactionUpdate(BaseModel):
    """Every field is optional; omitted fields stay unchanged.

    Sending an explicit ``null`` clears a nullable field.
    """

    type: TransactionType | None = None
    amount_minor: int | None = Field(default=None, gt=0, le=MAX_MINOR_UNITS)
    account_id: uuid.UUID | None = None
    dest_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    transaction_date: date | None = None
    occurred_at: datetime | None = None
    payment_method: PaymentMethod | None = None
    vendor: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    refund_of_id: uuid.UUID | None = None
    tag_ids: list[uuid.UUID] | None = None

    @field_validator("currency_code")
    @classmethod
    def upper_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("vendor", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class AccountRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class CategoryRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    kind: CategoryKind


class TagRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    color: str | None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: TransactionType
    amount_minor: int
    currency_code: str
    transaction_date: date
    occurred_at: datetime | None
    payment_method: PaymentMethod | None
    vendor: str | None
    description: str | None
    refund_of_id: uuid.UUID | None
    account: AccountRef
    destination_account: AccountRef | None
    category: CategoryRef | None
    tags: list[TagRef]
    created_at: datetime
    updated_at: datetime


class TransactionTotals(BaseModel):
    """Totals for the current filter, always per currency."""

    currency_code: str
    income_minor: int
    expenses_minor: int
    refunds_minor: int
    spending_minor: int
    net_minor: int
    transaction_count: int

"""Reporting schemas: one authoritative shape for the dashboard."""

import uuid
from datetime import date

from pydantic import BaseModel

from app.models.enums import AccountType
from app.schemas.transaction import TransactionOut


class PeriodOut(BaseModel):
    date_from: date
    date_to: date
    label: str


class TotalsOut(BaseModel):
    currency_code: str
    income_minor: int
    expenses_minor: int
    refunds_minor: int
    spending_minor: int
    net_minor: int
    transaction_count: int
    savings_rate: float | None


class CategorySliceOut(BaseModel):
    category_id: uuid.UUID | None
    name: str
    spent_minor: int
    share: float


class TrendPointOut(BaseModel):
    period: str
    label: str
    income_minor: int
    spending_minor: int
    net_minor: int


class AccountSliceOut(BaseModel):
    id: uuid.UUID
    name: str
    type: AccountType
    currency_code: str
    balance_minor: int


class OverviewOut(BaseModel):
    period: PeriodOut
    currency_code: str
    totals: TotalsOut
    by_category: list[CategorySliceOut]
    trend: list[TrendPointOut]
    accounts: list[AccountSliceOut]
    recent: list[TransactionOut]

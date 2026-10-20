"""Shared enum types.

``native_enum=False`` stores values as VARCHAR. Validation happens in the
Pydantic schemas and services before anything reaches the database.
"""

import enum

from sqlalchemy import Enum


class AccountType(str, enum.Enum):
    CASH = "cash"
    BANK = "bank"
    SAVINGS = "savings"
    DEBIT_CARD = "debit_card"
    CREDIT_CARD = "credit_card"
    MOBILE_WALLET = "mobile_wallet"


class CategoryKind(str, enum.Enum):
    EXPENSE = "expense"
    INCOME = "income"


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    REFUND = "refund"
    TRANSFER = "transfer"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    DEBIT_CARD = "debit_card"
    CREDIT_CARD = "credit_card"
    MOBILE_WALLET = "mobile_wallet"
    OTHER = "other"


class BudgetPeriod(str, enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class RecurrenceFrequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class BillStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    SKIPPED = "skipped"
    OVERDUE = "overdue"


class SavingsGoalStatus(str, enum.Enum):
    ACTIVE = "active"
    ACHIEVED = "achieved"
    ARCHIVED = "archived"


class Theme(str, enum.Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


def enum_column(enum_cls: type[enum.Enum], name: str) -> Enum:
    """Build a VARCHAR-backed enum column.

    ``create_constraint`` is disabled because SQLAlchemy/Alembic otherwise emit
    the same CHECK constraint twice. Values are validated by Pydantic schemas
    and the service layer before they reach the database.
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=False,
        length=32,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )

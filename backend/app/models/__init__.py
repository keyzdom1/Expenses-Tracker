"""Import every model so SQLAlchemy's metadata and Alembic see them all."""

from app.db.base import Base
from app.models.account import Account
from app.models.audit import AuditLog, IdempotencyKey
from app.models.budget import Budget, SavingsGoal
from app.models.category import Category
from app.models.currency import Currency
from app.models.notification import Notification
from app.models.profile import Profile, UserPreferences
from app.models.receipt import Receipt
from app.models.recurring import Bill, RecurringTransaction
from app.models.transaction import Tag, Transaction, TransactionTag

__all__ = [
    "Account",
    "AuditLog",
    "Base",
    "Bill",
    "Budget",
    "Category",
    "Currency",
    "IdempotencyKey",
    "Notification",
    "Profile",
    "Receipt",
    "RecurringTransaction",
    "SavingsGoal",
    "Tag",
    "Transaction",
    "TransactionTag",
    "UserPreferences",
]

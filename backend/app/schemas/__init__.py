"""Schema imports for convenience."""

from app.schemas.account import AccountCreate, AccountOut, AccountUpdate
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import PageMeta
from app.schemas.profile import PreferencesOut, PreferencesUpdate, ProfileOut, ProfileUpdate
from app.schemas.tag import TagCreate, TagOut
from app.schemas.transaction import (
    TransactionCreate,
    TransactionOut,
    TransactionTotals,
    TransactionUpdate,
)

__all__ = [
    "AccountCreate",
    "AccountOut",
    "AccountUpdate",
    "CategoryCreate",
    "CategoryOut",
    "CategoryUpdate",
    "PageMeta",
    "PreferencesOut",
    "PreferencesUpdate",
    "ProfileOut",
    "ProfileUpdate",
    "TagCreate",
    "TagOut",
    "TransactionCreate",
    "TransactionOut",
    "TransactionTotals",
    "TransactionUpdate",
]

"""Data-access helpers for profiles and preferences."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.currency import Currency
from app.models.profile import Profile, UserPreferences


def get_profile(db: Session, user_id: uuid.UUID) -> Profile | None:
    return db.get(Profile, user_id)


def get_preferences(db: Session, user_id: uuid.UUID) -> UserPreferences | None:
    return db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))


def currency_exists(db: Session, code: str) -> bool:
    return db.get(Currency, code) is not None

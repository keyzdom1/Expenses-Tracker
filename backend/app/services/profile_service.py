"""Profile and preference business rules."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.models.profile import Profile, UserPreferences
from app.repositories import profile_repository


def ensure_profile(db: Session, user_id: uuid.UUID, email: str | None) -> Profile:
    """Return the profile for an authenticated user, creating it on first use.

    Supabase owns authentication, so the profile row is created lazily from the
    verified token rather than during registration.
    """
    settings = get_settings()
    profile = profile_repository.get_profile(db, user_id)

    if profile is None:
        profile = Profile(id=user_id, email=email)
        preferences = UserPreferences(
            user_id=user_id,
            currency_code=settings.default_currency,
            timezone=settings.default_timezone,
        )
        try:
            db.add(profile)
            db.add(preferences)
            db.commit()
        except IntegrityError:
            # Two concurrent first requests: the other one won the race.
            db.rollback()
            profile = profile_repository.get_profile(db, user_id)
            if profile is None:
                raise
        return profile

    # Keep the email in sync when the user changes it in Supabase.
    if email and profile.email != email:
        profile.email = email
        db.commit()

    return profile


def update_profile(db: Session, user_id: uuid.UUID, changes: dict) -> Profile:
    profile = profile_repository.get_profile(db, user_id)
    if profile is None:
        raise APIError(404, "not_found", "Profile not found.")

    for field, value in changes.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


def get_preferences(db: Session, user_id: uuid.UUID) -> UserPreferences:
    preferences = profile_repository.get_preferences(db, user_id)
    if preferences is None:
        raise APIError(404, "not_found", "Preferences not found.")
    return preferences


def update_preferences(db: Session, user_id: uuid.UUID, changes: dict) -> UserPreferences:
    preferences = get_preferences(db, user_id)

    currency = changes.get("currency_code")
    if currency and not profile_repository.currency_exists(db, currency):
        raise APIError(
            422, "unknown_currency", f"Currency {currency} is not supported.", {"currency": currency}
        )

    for field, value in changes.items():
        setattr(preferences, field, value)

    db.commit()
    db.refresh(preferences)
    return preferences

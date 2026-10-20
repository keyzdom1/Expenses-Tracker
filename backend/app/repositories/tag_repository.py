"""Tag data access."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.transaction import Tag


def get(db: Session, user_id: uuid.UUID, tag_id: uuid.UUID) -> Tag | None:
    return db.scalar(select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id))


def list_for_user(db: Session, user_id: uuid.UUID) -> list[Tag]:
    return list(db.scalars(select(Tag).where(Tag.user_id == user_id).order_by(Tag.name)).all())


def get_many(db: Session, user_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> list[Tag]:
    if not tag_ids:
        return []
    return list(
        db.scalars(
            select(Tag).where(Tag.user_id == user_id, Tag.id.in_(set(tag_ids)))
        ).all()
    )


def name_exists(db: Session, user_id: uuid.UUID, name: str, exclude_id: uuid.UUID | None = None) -> bool:
    statement = select(Tag.id).where(
        Tag.user_id == user_id, func.lower(Tag.name) == name.lower()
    )
    if exclude_id:
        statement = statement.where(Tag.id != exclude_id)
    return db.scalar(statement) is not None

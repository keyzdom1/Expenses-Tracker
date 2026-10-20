"""Budget data access."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.budget import Budget


def get(db: Session, user_id: uuid.UUID, budget_id: uuid.UUID) -> Budget | None:
    return db.scalar(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    )


def list_for_user(
    db: Session, user_id: uuid.UUID, include_inactive: bool = False
) -> list[Budget]:
    statement = select(Budget).where(Budget.user_id == user_id)
    if not include_inactive:
        statement = statement.where(Budget.is_active.is_(True))
    return list(
        db.scalars(statement.order_by(Budget.is_active.desc(), Budget.created_at.desc())).all()
    )

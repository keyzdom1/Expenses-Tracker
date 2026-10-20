"""Categories and optional subcategories."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import CategoryKind, enum_column


class Category(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "categories"
    __table_args__ = (
        # Subcategories are unique under their parent; top-level names are
        # enforced in the service layer (PostgreSQL treats NULLs as distinct).
        UniqueConstraint("user_id", "parent_id", "name", name="uq_categories_user_parent_name"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[CategoryKind] = mapped_column(
        enum_column(CategoryKind, "category_kind"), nullable=False
    )
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    parent: Mapped["Category | None"] = relationship(remote_side="Category.id", back_populates="children")
    children: Mapped[list["Category"]] = relationship(back_populates="parent")

"""Receipt metadata.

Files live in private object storage. Only the storage path is stored here, so
OCR can be added later by filling ``ocr_status``/``ocr_text`` without a rewrite.
"""

import uuid

from sqlalchemy import BigInteger, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Receipt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "receipts"
    __table_args__ = (
        UniqueConstraint("transaction_id", name="uq_receipts_transaction_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )

    storage_path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Reserved for the deferred OCR feature.
    ocr_status: Mapped[str | None] = mapped_column(String(20))
    ocr_text: Mapped[str | None] = mapped_column(Text)

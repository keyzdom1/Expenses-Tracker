"""Receipt business rules: validation, ownership and signed links."""

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.receipt import Receipt
from app.models.transaction import Transaction
from app.repositories import transaction_repository
from app.schemas.receipt import ReceiptOut
from app.services import receipt_storage


def _transaction(db: Session, user_id: uuid.UUID, transaction_id: uuid.UUID) -> Transaction:
    transaction = transaction_repository.get(db, user_id, transaction_id)
    if transaction is None:
        raise APIError(404, "not_found", "Transaction not found.")
    return transaction


def _get(db: Session, user_id: uuid.UUID, transaction_id: uuid.UUID) -> Receipt | None:
    return db.scalar(
        select(Receipt).where(
            Receipt.user_id == user_id, Receipt.transaction_id == transaction_id
        )
    )


def get_receipt(db: Session, user_id: uuid.UUID, transaction_id: uuid.UUID) -> dict:
    _transaction(db, user_id, transaction_id)
    receipt = _get(db, user_id, transaction_id)
    if receipt is None:
        raise APIError(404, "not_found", "This transaction has no receipt.")
    return ReceiptOut.model_validate(receipt).model_dump(mode="json")


def upload(
    db: Session,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
    file_name: str | None,
    content: bytes,
) -> dict:
    _transaction(db, user_id, transaction_id)

    if len(content) > receipt_storage.MAX_RECEIPT_BYTES:
        raise APIError(
            413,
            "file_too_large",
            "Receipts must be 5 MB or smaller.",
        )
    if not content:
        raise APIError(422, "empty_file", "The uploaded file is empty.")

    detected = receipt_storage.detect_file_type(content)
    if detected is None:
        raise APIError(
            422,
            "unsupported_file_type",
            "Upload a JPEG, PNG, WebP or PDF receipt.",
        )
    mime_type, extension = detected

    if _get(db, user_id, transaction_id) is not None:
        raise APIError(
            409,
            "receipt_exists",
            "This transaction already has a receipt. Delete it first to replace it.",
        )

    safe_name = Path(file_name or f"receipt.{extension}").name[:255] or f"receipt.{extension}"

    storage_path = receipt_storage.save(user_id, transaction_id, content, extension)
    receipt = Receipt(
        user_id=user_id,
        transaction_id=transaction_id,
        storage_path=storage_path,
        file_name=safe_name,
        mime_type=mime_type,
        size_bytes=len(content),
    )
    db.add(receipt)

    try:
        db.commit()
    except Exception:
        db.rollback()
        receipt_storage.delete(storage_path)
        raise

    db.refresh(receipt)
    return ReceiptOut.model_validate(receipt).model_dump(mode="json")


def delete(db: Session, user_id: uuid.UUID, transaction_id: uuid.UUID) -> None:
    _transaction(db, user_id, transaction_id)
    receipt = _get(db, user_id, transaction_id)
    if receipt is None:
        raise APIError(404, "not_found", "This transaction has no receipt.")

    receipt_storage.delete(receipt.storage_path)
    db.delete(receipt)
    db.commit()


def signed_url(
    db: Session, user_id: uuid.UUID, transaction_id: uuid.UUID, base_url: str
) -> dict:
    _transaction(db, user_id, transaction_id)
    receipt = _get(db, user_id, transaction_id)
    if receipt is None:
        raise APIError(404, "not_found", "This transaction has no receipt.")

    url, expires_at = receipt_storage.signed_url(receipt.storage_path, base_url)
    return {"url": url, "expires_at": expires_at.isoformat()}

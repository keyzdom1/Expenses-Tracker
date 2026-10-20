"""Receipt endpoints.

Receipts are private: metadata and links require the owning user's token. The
local development link is itself signed and expires, so it can be opened
directly by a browser without a bearer header.
"""

import uuid

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.responses import ok
from app.core.deps import CurrentUserId, DbSession
from app.services import receipt_service, receipt_storage

router = APIRouter(prefix="/transactions", tags=["receipts"])
local_router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.post("/{transaction_id}/receipt", status_code=201, summary="Upload a receipt")
def upload_receipt(
    transaction_id: uuid.UUID,
    user_id: CurrentUserId,
    db: DbSession,
    file: UploadFile = File(...),
):
    content = file.file.read(receipt_storage.MAX_RECEIPT_BYTES + 1)
    receipt = receipt_service.upload(db, user_id, transaction_id, file.filename, content)
    return ok(receipt)


@router.get("/{transaction_id}/receipt", summary="Get receipt metadata")
def get_receipt(transaction_id: uuid.UUID, user_id: CurrentUserId, db: DbSession):
    return ok(receipt_service.get_receipt(db, user_id, transaction_id))


@router.get("/{transaction_id}/receipt/url", summary="Create a short-lived receipt URL")
def get_receipt_url(
    transaction_id: uuid.UUID,
    user_id: CurrentUserId,
    db: DbSession,
    request: Request,
):
    base_url = str(request.base_url).rstrip("/")
    return ok(receipt_service.signed_url(db, user_id, transaction_id, base_url))


@router.delete("/{transaction_id}/receipt", summary="Delete a receipt")
def delete_receipt(transaction_id: uuid.UUID, user_id: CurrentUserId, db: DbSession):
    receipt_service.delete(db, user_id, transaction_id)
    return ok({"transaction_id": str(transaction_id), "deleted": True})


@local_router.get("/local/{token}", summary="Serve a signed local receipt")
def serve_local_receipt(token: str):
    """Development-only equivalent of a Supabase Storage signed URL."""
    path = receipt_storage.verify_local_token(token)
    file_path = receipt_storage.local_file_path(path)
    if not file_path.is_file():
        from app.core.errors import APIError

        raise APIError(404, "not_found", "Receipt file not found.")

    media_type = "application/octet-stream"
    suffix = file_path.suffix.lower()
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }.get(suffix, media_type)

    return FileResponse(file_path, media_type=media_type)

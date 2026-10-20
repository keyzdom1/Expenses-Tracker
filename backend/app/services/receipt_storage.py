"""Private receipt storage.

Supabase Storage is used when a service-role key is configured. In local
development the same API is backed by a private directory and HMAC-signed,
short-lived URLs, so the feature works end to end without cloud credentials.
"""

import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.errors import APIError

MAX_RECEIPT_BYTES = 5 * 1024 * 1024

SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"%PDF-", "application/pdf", "pdf"),
)


def detect_file_type(content: bytes) -> tuple[str, str] | None:
    """Return (mime_type, extension) from magic bytes, ignoring the client."""
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp", "webp"
    for signature, mime_type, extension in SIGNATURES:
        if content.startswith(signature):
            return mime_type, extension
    return None


def _local_root() -> Path:
    return Path(get_settings().local_receipts_dir).resolve()


def _signing_secret() -> bytes:
    return get_settings().receipt_signing_secret.encode("utf-8")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def make_local_token(path: str, ttl_seconds: int) -> str:
    payload = json.dumps({"path": path, "exp": int(time.time()) + ttl_seconds}).encode()
    signature = hmac.new(_signing_secret(), payload, hashlib.sha256).digest()
    return f"{_b64encode(payload)}.{_b64encode(signature)}"


def verify_local_token(token: str) -> str:
    """Return the storage path for a valid, unexpired token."""
    try:
        payload_b64, signature_b64 = token.split(".", 1)
        payload = _b64decode(payload_b64)
        signature = _b64decode(signature_b64)
    except (ValueError, TypeError) as exc:
        raise APIError(403, "invalid_receipt_link", "This receipt link is invalid.") from exc

    expected = hmac.new(_signing_secret(), payload, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise APIError(403, "invalid_receipt_link", "This receipt link is invalid.")

    try:
        data = json.loads(payload)
        expires = int(data["exp"])
        path = str(data["path"])
    except (ValueError, KeyError, TypeError) as exc:
        raise APIError(403, "invalid_receipt_link", "This receipt link is invalid.") from exc

    if expires < int(time.time()):
        raise APIError(403, "receipt_link_expired", "This receipt link has expired.")

    return path


def local_file_path(path: str) -> Path:
    root = _local_root()
    candidate = (root / path).resolve()
    if root != candidate and root not in candidate.parents:
        raise APIError(403, "invalid_receipt_path", "Invalid receipt path.")
    return candidate


def _storage_headers() -> dict[str, str]:
    key = get_settings().supabase_service_role_key
    return {"Authorization": f"Bearer {key}", "apikey": key}


def _use_supabase() -> bool:
    settings = get_settings()
    return bool(settings.supabase_url and settings.supabase_service_role_key)


def save(user_id: uuid.UUID, transaction_id: uuid.UUID, content: bytes, extension: str) -> str:
    path = f"{user_id}/{transaction_id}/{uuid.uuid4()}.{extension}"
    settings = get_settings()

    if _use_supabase():
        bucket = settings.supabase_receipts_bucket
        url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{path}"
        try:
            response = httpx.post(
                url,
                content=content,
                headers={
                    **_storage_headers(),
                    "content-type": "application/octet-stream",
                    "x-upsert": "false",
                },
                timeout=30,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise APIError(502, "storage_error", "Could not store the receipt.") from exc
        return path

    destination = local_file_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return path


def delete(path: str) -> None:
    settings = get_settings()

    if _use_supabase():
        bucket = settings.supabase_receipts_bucket
        url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{path}"
        try:
            httpx.delete(url, headers=_storage_headers(), timeout=30)
        except httpx.HTTPError as exc:
            raise APIError(502, "storage_error", "Could not delete the receipt.") from exc
        return

    local_file_path(path).unlink(missing_ok=True)


def signed_url(path: str, base_url: str) -> tuple[str, datetime]:
    settings = get_settings()
    ttl = min(max(settings.signed_url_ttl_seconds, 60), 300)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

    if _use_supabase():
        bucket = settings.supabase_receipts_bucket
        url = f"{settings.supabase_url}/storage/v1/object/sign/{bucket}/{path}"
        try:
            response = httpx.post(
                url,
                json={"expiresIn": ttl},
                headers=_storage_headers(),
                timeout=30,
            )
            response.raise_for_status()
            signed_path = response.json()["signedURL"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise APIError(502, "storage_error", "Could not create a receipt link.") from exc
        return f"{settings.supabase_url}/storage/v1{signed_path}", expires_at

    token = make_local_token(path, ttl)
    return f"{base_url.rstrip('/')}/api/v1/receipts/local/{token}", expires_at

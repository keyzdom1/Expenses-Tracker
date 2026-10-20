"""Shared FastAPI dependencies (authentication, database session)."""

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.security import InvalidCredentials, decode_access_token
from app.db.session import get_db

# auto_error=False so we can return our own consistent 401 envelope.
bearer_scheme = HTTPBearer(auto_error=False, description="Supabase access token")


def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise APIError(
            401, "unauthenticated", "A valid bearer token is required.", {"header": "Authorization"}
        )

    try:
        return decode_access_token(credentials.credentials)
    except InvalidCredentials as exc:
        raise APIError(
            401,
            "unauthenticated",
            str(exc),
            {"header": "Authorization"},
        ) from exc


def get_current_user_id(payload: Annotated[dict, Depends(get_token_payload)]) -> uuid.UUID:
    """Resolve the authenticated user's ID from the token's `sub` claim.

    The client never sends a user ID; this is the only source of identity.
    """
    subject = payload.get("sub")
    try:
        return uuid.UUID(str(subject))
    except (TypeError, ValueError) as exc:
        raise APIError(401, "unauthenticated", "The token subject is invalid.") from exc


CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]
TokenPayload = Annotated[dict, Depends(get_token_payload)]
DbSession = Annotated[Session, Depends(get_db)]

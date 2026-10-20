"""Verification of Supabase-issued access tokens.

Two modes are supported:

* **JWKS (preferred)** - newer Supabase projects sign tokens with an asymmetric
  key (ES256/RS256). Public keys are fetched from the project's JWKS endpoint
  and cached; a key rotation is picked up automatically by PyJWT.
* **Shared secret (legacy)** - older projects sign with HS256 using the
  project's JWT secret.

The application never handles passwords and never stores tokens.
"""

import logging

import jwt
from jwt import PyJWKClient

from app.core.config import get_settings

logger = logging.getLogger("expense_tracker.security")

# Asymmetric algorithms Supabase may use for access tokens.
ASYMMETRIC_ALGORITHMS = ["ES256", "RS256"]


class InvalidCredentials(Exception):
    """Raised when a token is missing, expired, forged or not configured."""


_jwks_clients: dict[str, PyJWKClient] = {}


def _get_jwks_client(url: str) -> PyJWKClient:
    client = _jwks_clients.get(url)
    if client is None:
        client = PyJWKClient(url, cache_keys=True, lifespan=300)
        _jwks_clients[url] = client
    return client


def decode_access_token(token: str) -> dict:
    """Validate a Supabase access token and return its claims."""
    settings = get_settings()
    options = {"require": ["exp", "sub"], "verify_aud": True}

    if settings.supabase_jwks_url:
        try:
            signing_key = _get_jwks_client(settings.supabase_jwks_url).get_signing_key_from_jwt(
                token
            )
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=ASYMMETRIC_ALGORITHMS,
                audience=settings.supabase_jwt_aud,
                options=options,
            )
        except jwt.PyJWKClientError as exc:
            # Unknown key id, unreachable JWKS, etc. Never echo the raw error.
            logger.warning("JWKS key lookup failed: %s", type(exc).__name__)
            raise InvalidCredentials("Token could not be verified") from exc
        except jwt.InvalidTokenError as exc:
            raise InvalidCredentials("Token is invalid or expired") from exc

    if settings.supabase_jwt_secret:
        try:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=settings.supabase_jwt_aud,
                options=options,
            )
        except jwt.InvalidTokenError as exc:
            raise InvalidCredentials("Token is invalid or expired") from exc

    # Fail closed: never accept unverified tokens just because config is missing.
    raise InvalidCredentials("Authentication is not configured on the server")

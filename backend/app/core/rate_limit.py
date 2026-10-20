"""Rate limiting keyed by access token, falling back to the client IP.

The token is hashed before it becomes a key, so raw credentials never appear
in logs or the in-memory limiter store. A user's limit therefore follows their
session across proxies instead of sharing one bucket for every user behind
Render's load balancer.
"""

import hashlib

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import get_settings


def rate_limit_key(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]
        return f"token:{digest}"
    return get_remote_address(request)


limiter = Limiter(
    key_func=rate_limit_key,
    default_limits=[get_settings().rate_limit_default],
)

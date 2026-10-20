"""FastAPI application entry point."""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app import __version__
from app.api.responses import ok
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import error_response, register_exception_handlers
from app.core.rate_limit import limiter
from app.db.session import get_engine

settings = get_settings()

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
)
logger = logging.getLogger("expense_tracker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    logger.info("%s v%s starting (env=%s)", settings.app_name, __version__, settings.app_env)
    if not settings.database_url:
        logger.warning("DATABASE_URL is not set - database features are unavailable.")
    yield
    logger.info("%s shutting down", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="API for the Expense Tracker & Personal Finance Management System.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Attach a request ID to every request/response for traceable logs.

    Privacy rule (Section 10): we log the request ID, method and path only -
    never amounts, tokens or personal data.
    """
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    logger.info("rid=%s %s %s", request_id, request.method, request.url.path)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    # Baseline hardening headers for every API response.
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    if settings.is_production:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


# Rate limiting sits inside CORS so 429 responses still carry CORS headers,
# but outside the routes so every endpoint shares one bucket per caller.
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return error_response(
        429,
        "rate_limited",
        "Too many requests. Please slow down and try again shortly.",
        {"limit": str(exc.detail)},
        getattr(request.state, "request_id", None),
    )


# CORS: only the deployed frontend origin and localhost during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.api_v1_prefix)


def _database_status() -> str:
    """Cheap connectivity probe for the health endpoint."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except Exception:  # noqa: BLE001 - health must never raise
        logger.warning("Database health check failed", exc_info=True)
        return "unavailable"


@app.get("/", tags=["system"], summary="Service index")
async def index():
    return ok(
        {
            "name": settings.app_name,
            "version": __version__,
            "environment": settings.app_env,
            "docs": "/docs",
            "health": "/health",
        }
    )


@app.get("/health", tags=["system"], summary="Health check")
async def health():
    """Liveness probe used by local dev, Render and CI."""
    return ok(
        {
            "status": "ok",
            "version": __version__,
            "environment": settings.app_env,
            "api_prefix": settings.api_v1_prefix,
            "database": _database_status(),
        }
    )

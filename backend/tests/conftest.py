"""Shared pytest fixtures.

Tests run against a **separate database** (TEST_DATABASE_URL), never the
development one. Alembic builds the schema once per session, then every test
starts from an empty set of user tables.
"""

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_SECRET = "test-jwt-secret-not-used-outside-tests"
TEST_AUDIENCE = "authenticated"

settings = get_settings()
# Point every database consumer at the isolated test database.
settings.database_url = settings.test_database_url
settings.migration_database_url = settings.test_database_url
# Use HS256 for tests so no network/JWKS access is required.
settings.supabase_jwks_url = ""
settings.supabase_jwt_secret = TEST_SECRET
settings.supabase_jwt_aud = TEST_AUDIENCE
# Receipt tests use the local signed-storage fallback, never the network.
settings.supabase_service_role_key = ""
settings.local_receipts_dir = str(BACKEND_DIR / "var" / "test-receipts")
# Jobs are open in the test suite unless a test opts into a secret.
settings.cron_secret = ""

from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

# Rate limiting is exercised explicitly in test_phase7; keep it off elsewhere.
app.state.limiter.enabled = False

engine = create_engine(settings.test_database_url, pool_pre_ping=True)
TestSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

USER_TABLES = (
    "accounts",
    "audit_logs",
    "bills",
    "budgets",
    "categories",
    "idempotency_keys",
    "notifications",
    "profiles",
    "receipts",
    "recurring_transactions",
    "savings_goals",
    "tags",
    "transaction_tags",
    "transactions",
    "user_preferences",
)


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Apply all migrations to the test database once."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.test_database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    yield


@pytest.fixture(autouse=True)
def clean_database(migrated_database):
    """Empty user data before each test, keeping seeded currencies/RLS."""
    with engine.begin() as connection:
        connection.execute(
            text(f"TRUNCATE {', '.join(USER_TABLES)} RESTART IDENTITY CASCADE")
        )
    receipts_dir = Path(settings.local_receipts_dir)
    if receipts_dir.exists():
        shutil.rmtree(receipts_dir)
    yield


@pytest.fixture
def db():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    def override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_token():
    """Create a signed access token for a user (mirrors Supabase claims)."""

    def _make(
        user_id: uuid.UUID | None = None,
        *,
        email: str | None = None,
        expires_in: int = 3600,
        secret: str = TEST_SECRET,
        audience: str = TEST_AUDIENCE,
        include_exp: bool = True,
        subject: str | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        claims = {
            "sub": subject if subject is not None else str(user_id or uuid.uuid4()),
            "aud": audience,
            "iat": now,
            "role": "authenticated",
        }
        if email:
            claims["email"] = email
        if include_exp:
            claims["exp"] = now + timedelta(seconds=expires_in)
        return jwt.encode(claims, secret, algorithm="HS256")

    return _make


@pytest.fixture
def user_token(make_token):
    return make_token(email="user@example.com")

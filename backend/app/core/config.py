"""Typed application settings, loaded from environment variables / .env.

Every secret lives here and is read once at startup. Nothing in this module
should ever be imported into frontend code.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration.

    Values come from (in order of precedence):
      1. real environment variables
      2. the ``backend/.env`` file (never committed)
      3. the defaults below (safe for local development only)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "Expense Tracker API"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # --- CORS: comma-separated list of allowed browser origins ---
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Database (Supabase PostgreSQL in deployed environments) ---
    # Pooled connection string (port 6543) used by the running API.
    # Default points at the local PostgreSQL used for development.
    database_url: str = "postgresql+psycopg://postgres@127.0.0.1:5432/expense_tracker"
    # Direct connection string (port 5432) used by Alembic migrations.
    # Falls back to database_url when empty.
    migration_database_url: str = ""
    # Separate database used only by the automated test suite.
    test_database_url: str = "postgresql+psycopg://postgres@127.0.0.1:5432/expense_tracker_test"

    # --- Supabase Auth ---
    supabase_url: str = ""
    supabase_jwks_url: str = ""
    supabase_jwt_aud: str = "authenticated"
    # Legacy/shared-secret projects sign access tokens with HS256. Newer
    # projects publish asymmetric keys through JWKS, so this stays optional.
    supabase_jwt_secret: str = ""

    # --- Supabase Storage (private receipts bucket) ---
    supabase_service_role_key: str = ""
    supabase_receipts_bucket: str = "receipts"
    signed_url_ttl_seconds: int = 300
    # Used only for the local development storage fallback. Set a strong value
    # in production if receipts are served without Supabase Storage.
    receipt_signing_secret: str = "dev-only-receipt-signing-secret"
    local_receipts_dir: str = "var/receipts"

    # --- Defaults for new users ---
    default_currency: str = "NGN"
    default_timezone: str = "Africa/Lagos"

    # --- Rate limiting ---
    rate_limit_default: str = "120/minute"

    # --- Scheduled jobs ---
    # Render Cron Job sends this value so only our own scheduler can trigger jobs.
    cron_secret: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        """Split the comma-separated CORS setting into a clean list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def migration_url(self) -> str:
        """Direct connection used by Alembic (falls back to the pooled URL)."""
        return self.migration_database_url or self.database_url


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read once per process)."""
    return Settings()

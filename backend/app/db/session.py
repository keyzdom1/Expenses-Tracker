"""Database engine and session factory.

The engine is created lazily so importing the application never fails when
DATABASE_URL is unset (e.g. during static checks).
"""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return the process-wide engine, creating it on first use."""
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={
                # Fail fast rather than hanging a request if the DB is unreachable.
                "connect_timeout": 10,
                # Supabase's transaction pooler (Supavisor/PgBouncer) cannot
                # reuse server-side prepared statements. Disabling psycopg's
                # statement cache keeps both the pooler and local PostgreSQL
                # working with the same code path.
                "prepare_threshold": None,
            },
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False
        )
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped database session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()

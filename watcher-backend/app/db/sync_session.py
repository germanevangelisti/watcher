"""
Synchronous session for endpoints that require traditional SQLAlchemy.
Supports both SQLite and PostgreSQL based on SYNC_DATABASE_URL.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine_kwargs: dict = {
    "echo": False,
}

if not settings.is_postgres:
    from sqlalchemy.pool import StaticPool
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool

sync_engine = create_engine(settings.SYNC_DATABASE_URL, **engine_kwargs)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def get_sync_db():
    """Dependency for synchronous database sessions (DS Lab endpoints)."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

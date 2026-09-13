"""
Database configuration

Supports both SQLite (development) and PostgreSQL (production).
The driver is selected automatically based on DATABASE_URL.
"""

import logging
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

engine_kwargs: dict = {
    "echo": False,
}

if settings.is_postgres:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_pre_ping"] = True
else:
    from sqlalchemy.pool import NullPool
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

if not settings.is_postgres:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

BackgroundSessionLocal = AsyncSessionLocal

Base = declarative_base()

_vector_db_initialized = False


def init_vector_db():
    """Initialize Vector Database (ChromaDB) lazily."""
    global _vector_db_initialized

    if _vector_db_initialized:
        return

    try:
        from app.services.embedding_service import get_embedding_service
        service = get_embedding_service()

        if service.client:
            logger.info("Vector database (ChromaDB) initialized successfully")
            _vector_db_initialized = True
        else:
            logger.warning("Vector database initialization skipped (ChromaDB not available)")

    except Exception as e:
        logger.error(f"Error initializing vector database: {e}")


async def _create_pg_fts_infrastructure(conn):
    """Create PostgreSQL full-text search index and trigger for chunk_records."""
    await conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'chunk_records' AND column_name = 'search_vector'
            ) THEN
                ALTER TABLE chunk_records ADD COLUMN search_vector tsvector;
            END IF;
        END $$;
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_chunk_search_vector
        ON chunk_records USING GIN (search_vector);
    """))
    await conn.execute(text("""
        CREATE OR REPLACE FUNCTION chunk_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('spanish', COALESCE(NEW.text, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """))
    await conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'trg_chunk_search_vector'
            ) THEN
                CREATE TRIGGER trg_chunk_search_vector
                    BEFORE INSERT OR UPDATE OF text ON chunk_records
                    FOR EACH ROW
                    EXECUTE FUNCTION chunk_search_vector_update();
            END IF;
        END $$;
    """))
    await conn.execute(text("""
        UPDATE chunk_records SET search_vector = to_tsvector('spanish', COALESCE(text, ''))
        WHERE search_vector IS NULL;
    """))


_SQLITE_ADDED_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "analisis": [
        ("aiu_summary_json", "TEXT"),
        ("firewall_score", "REAL"),
        ("transparency_score", "REAL"),
        ("red_flags_json", "TEXT"),
        ("num_red_flags", "INTEGER"),
        ("is_gasto_publico", "INTEGER"),
        ("etapa_gasto", "TEXT"),
        ("jurisdiccion_gasto", "TEXT"),
    ],
    "ejecucion_presupuestaria": [
        ("is_duplicate", "INTEGER NOT NULL DEFAULT 0"),
        ("analisis_id", "INTEGER"),
        ("etapa_gasto", "TEXT"),
        ("jurisdiccion", "TEXT"),
    ],
}


async def _ensure_sqlite_columns(conn) -> None:
    """
    Idempotent SQLite column migrations — runs on every startup, safe to re-run.
    SQLite does not support IF NOT EXISTS in ALTER TABLE, so we check PRAGMA first.
    """
    for table, columns in _SQLITE_ADDED_COLUMNS.items():
        result = await conn.execute(text(f"PRAGMA table_info({table})"))
        existing = {row[1] for row in result.fetchall()}
        if not existing:
            continue  # table not created yet; create_all will build it complete
        for col_name, col_type in columns:
            if col_name not in existing:
                await conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                )
                logger.info(f"SQLite migration: added {table}.{col_name}")


async def init_db():
    """Initialize SQL database and Vector DB."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        if settings.is_postgres:
            await _create_pg_fts_infrastructure(conn)
        else:
            await _ensure_sqlite_columns(conn)

    init_vector_db()


async def get_db():
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_test_db():
    """Test session."""
    async with AsyncSessionLocal() as session:
        yield session

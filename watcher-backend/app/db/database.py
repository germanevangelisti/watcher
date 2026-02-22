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
        cursor.execute("PRAGMA busy_timeout=5000")
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


async def init_db():
    """Initialize SQL database and Vector DB."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        if settings.is_postgres:
            await _create_pg_fts_infrastructure(conn)

    init_vector_db()


async def get_db():
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_test_db():
    """Test session."""
    async with AsyncSessionLocal() as session:
        yield session

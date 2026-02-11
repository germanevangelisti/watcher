"""
Configuración de la base de datos

Incluye:
- SQLite para datos estructurados
- ChromaDB para embeddings y búsqueda semántica
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

logger = logging.getLogger(__name__)

# URL de la base de datos SQLite
SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{settings.BASE_DIR}/sqlite.db"

# Crear el motor de base de datos
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Crear sesión asíncrona
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base para los modelos
Base = declarative_base()

# Vector Database (ChromaDB) - Will be initialized on demand
_vector_db_initialized = False

def init_vector_db():
    """
    Initialize Vector Database (ChromaDB).
    
    This is called lazily when embeddings are first needed.
    """
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

async def init_db():
    """Inicializa la base de datos SQL y Vector DB."""
    # Initialize SQL database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize Vector database (non-blocking)
    init_vector_db()

async def get_db():
    """
    Dependencia para obtener una sesión de base de datos.
    Para usar con FastAPI.
    """
    async with AsyncSessionLocal() as session:
        yield session

# Función para pruebas
async def get_test_db():
    """Obtiene una sesión de prueba."""
    async with AsyncSessionLocal() as session:
        yield session
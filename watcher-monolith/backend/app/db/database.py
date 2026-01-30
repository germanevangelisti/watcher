"""
Configuración de la base de datos
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

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

async def init_db():
    """Inicializa la base de datos."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
"""
Sesión síncrona para endpoints que necesitan SQLAlchemy tradicional
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.config import settings

# URL de la base de datos SQLite (síncrona)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{settings.BASE_DIR}/sqlite.db"

# Crear el motor de base de datos síncrono
sync_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Crear sesión síncrona
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

def get_sync_db():
    """
    Dependencia para obtener una sesión de base de datos síncrona.
    Para usar con endpoints del DS Lab.
    """
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


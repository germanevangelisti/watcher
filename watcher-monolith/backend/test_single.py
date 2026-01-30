"""
Script para probar el procesamiento de un solo archivo
"""

import asyncio
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.services.batch_processor import BatchProcessor
from app.db.database import Base

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def main():
    # Configurar base de datos
    engine = create_async_engine(
        "sqlite+aiosqlite:///sqlite.db",
        echo=True  # SQL logging
    )
    
    # Crear tablas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Crear sesión
    async_session = sessionmaker(
        engine, 
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    # Usar sesión sin transacción inicial
    async with async_session() as session:
        # Crear procesador
        processor = BatchProcessor(session)
        
        # Procesar un solo archivo
        source_dir = Path("/Users/germanevangelisti/watcher-agent/boletines")
        result = await processor.process_directory(
            source_dir=source_dir,
            batch_size=1  # Procesar de a uno
        )
        
        print("Resultado:", result)

if __name__ == "__main__":
    asyncio.run(main())
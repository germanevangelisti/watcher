"""
Script de prueba usando el servicio mock (sin OpenAI)
"""

import asyncio
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal, init_db
from app.services.batch_processor import BatchProcessor
from app.services.mock_watcher_service import MockWatcherService

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Monkey patch para usar el servicio mock
import app.services.batch_processor
app.services.batch_processor.WatcherService = MockWatcherService

async def main():
    """Función principal de prueba."""
    
    # Inicializar base de datos
    await init_db()
    logger.info("Base de datos inicializada")
    
    # Crear sesión de base de datos
    async with AsyncSessionLocal() as session:
        # Crear procesador con servicio mock
        processor = BatchProcessor(session)
        
        # Directorio de boletines
        boletines_dir = Path("/Users/germanevangelisti/watcher-agent/boletines")
        
        if not boletines_dir.exists():
            logger.error(f"Directorio {boletines_dir} no encontrado")
            return
        
        logger.info(f"Procesando boletines desde: {boletines_dir}")
        
        try:
            # Procesar solo los primeros 3 archivos para prueba
            # Necesitamos modificar el batch processor para aceptar un límite
            pdf_files = sorted(list(boletines_dir.glob('*.pdf')))[:3]  # Solo los primeros 3
            logger.info(f"Procesando {len(pdf_files)} archivos de prueba")
            
            processed_count = 0
            for pdf_file in pdf_files:
                logger.info(f"Procesando: {pdf_file.name}")
                result = await processor._process_single_pdf(pdf_file)
                logger.info(f"Resultado: {result}")
                processed_count += 1
            
            stats = {
                "total": len(pdf_files),
                "processed": processed_count,
                "failed": 0,
                "skipped": 0
            }
            
            logger.info("Procesamiento completado!")
            logger.info(f"Estadísticas finales: {stats}")
            
        except Exception as e:
            logger.error(f"Error durante el procesamiento: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())

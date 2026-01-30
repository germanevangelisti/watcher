"""
Script de prueba simple para verificar el funcionamiento básico
"""

import asyncio
import logging
from pathlib import Path

from app.services.content_extractor import ContentExtractor
from app.services.mock_watcher_service import MockWatcherService

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Función principal de prueba."""
    
    # Crear servicios
    extractor = ContentExtractor()
    watcher = MockWatcherService()
    
    # Directorio de boletines
    boletines_dir = Path("/Users/germanevangelisti/watcher-agent/boletines")
    
    if not boletines_dir.exists():
        logger.error(f"Directorio {boletines_dir} no encontrado")
        return
    
    # Procesar solo el primer archivo
    pdf_files = sorted(list(boletines_dir.glob('*.pdf')))[:1]
    
    for pdf_file in pdf_files:
        logger.info(f"Procesando: {pdf_file.name}")
        
        try:
            # Extraer contenido
            sections = await extractor.extract_from_pdf(pdf_file)
            logger.info(f"Extraídas {len(sections)} secciones")
            
            # Analizar cada sección
            for i, section in enumerate(sections):
                logger.info(f"Analizando sección {i+1}/{len(sections)}")
                
                analysis = await watcher.analyze_content(
                    content=section["content"],
                    metadata=section["metadata"]
                )
                
                logger.info(f"Análisis: {analysis}")
                
        except Exception as e:
            logger.error(f"Error procesando {pdf_file.name}: {e}")
            raise
    
    logger.info("Prueba completada exitosamente!")

if __name__ == "__main__":
    asyncio.run(main())

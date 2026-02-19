"""
Servicio para procesar archivos PDF
---------------------------------
DEPRECADO: Este módulo se mantiene por compatibilidad.
Usar ExtractorRegistry en su lugar.

Convierte PDFs a texto y gestiona los archivos procesados.
"""

import os
from pathlib import Path
from typing import Dict
import logging
import aiofiles
import asyncio
import warnings

from app.core.config import settings

logger = logging.getLogger(__name__)

# Deprecation warning
warnings.warn(
    "pdf_service.PDFProcessor está deprecado. "
    "Usar ExtractorRegistry de app.services.extractors en su lugar.",
    DeprecationWarning,
    stacklevel=2
)

class PDFProcessor:
    """Procesa archivos PDF y los convierte a texto."""
    
    def __init__(self):
        """Inicializa las rutas de datos."""
        self.raw_dir = settings.DATA_DIR / "raw"
        self.processed_dir = settings.DATA_DIR / "processed"
        self.results_dir = settings.DATA_DIR / "results"
        
        # Crear directorios si no existen
        os.makedirs(str(self.raw_dir), exist_ok=True)
        os.makedirs(str(self.processed_dir), exist_ok=True)
        os.makedirs(str(self.results_dir), exist_ok=True)
    
    def _parse_filename(self, filename: str) -> Dict[str, str]:
        """
        Extrae información del nombre del archivo.
        Formato esperado: YYYYMMDD_N_Secc.pdf
        """
        name = Path(filename).stem
        parts = name.split('_')
        
        if len(parts) != 3:
            raise ValueError(f"Formato de nombre inválido: {filename}")
            
        return {
            "date": parts[0],
            "section": parts[1]
        }
    
    async def process_pdf(self, pdf_path: Path) -> Path:
        """
        Convierte un PDF a texto de forma asíncrona.
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            Ruta al archivo de texto generado
        """
        # Asegurar que pdf_path sea Path
        pdf_path = Path(pdf_path).resolve()
        txt_path = self.processed_dir / f"{pdf_path.stem}.txt"
        
        logger.debug(f"Procesando PDF: {pdf_path}")
        logger.debug(f"Archivo de texto destino: {txt_path}")
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
            
        try:
            # Leer PDF y extraer texto (operación sincrónica)
            text = await asyncio.to_thread(self._extract_text_from_pdf, pdf_path)
            logger.debug(f"Texto extraído: {len(text)} caracteres")
            
            # Guardar texto de forma asíncrona
            async with aiofiles.open(txt_path, 'w', encoding='utf-8') as f:
                await f.write(text)
                logger.debug(f"Texto guardado en {txt_path}")
                
            return txt_path
            
        except Exception as e:
            logger.error(f"Error procesando {pdf_path.name}: {str(e)}", exc_info=True)
            raise
    
    def _extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extrae texto de un PDF usando ExtractorRegistry (wrapper de compatibilidad).
        DEPRECADO: Usar ExtractorRegistry directamente.
        
        NOTA: En notebooks, usar el método async _extract_text_from_pdf_async()
        """
        import asyncio
        from app.services.extractors import ExtractorRegistry
        
        logger.debug(f"Extrayendo texto de {pdf_path} (usando ExtractorRegistry)")
        
        # Intentar ejecutar async
        try:
            # Verificar si ya hay un loop corriendo
            _loop = asyncio.get_running_loop()
            # Si llegamos aquí, hay un loop - no podemos usar run_until_complete
            # En notebooks, esto causará un error
            raise RuntimeError(
                "Este método no puede ejecutarse en un event loop activo (ej. Jupyter). "
                "Usar 'await processor._extract_text_from_pdf_async(path)' en su lugar."
            )
        except RuntimeError as e:
            if "no running event loop" in str(e).lower() or "no current event loop" in str(e).lower():
                # No hay loop, crear uno nuevo
                result = asyncio.run(ExtractorRegistry.extract(pdf_path))
            else:
                # Otro RuntimeError (probablemente el que nosotros lanzamos)
                raise
        
        if not result.success:
            raise Exception(f"Error extracting PDF: {result.error}")
        
        return result.full_text
    
    async def _extract_text_from_pdf_async(self, pdf_path: Path) -> str:
        """
        Versión async del extractor de texto.
        Usar esta versión en notebooks y código async.
        """
        from app.services.extractors import ExtractorRegistry
        
        result = await ExtractorRegistry.extract(pdf_path)
        
        if not result.success:
            raise Exception(f"Error extracting PDF: {result.error}")
        
        return result.full_text
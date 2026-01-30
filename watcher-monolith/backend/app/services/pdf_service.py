"""
Servicio para procesar archivos PDF
---------------------------------
Convierte PDFs a texto y gestiona los archivos procesados.
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
import logging
from datetime import datetime
import json
import aiofiles
import asyncio

import PyPDF2
from tqdm import tqdm

from app.core.config import settings

logger = logging.getLogger(__name__)

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
        Extrae texto de un PDF (operación sincrónica).
        """
        logger.debug(f"Extrayendo texto de {pdf_path}")
        with open(pdf_path, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                text += page_text + "\n\n"
                logger.debug(f"Página {i+1}: {len(page_text)} caracteres")
                
            return text
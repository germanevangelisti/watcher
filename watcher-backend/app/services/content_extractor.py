"""
Servicio para extraer y consolidar contenido de boletines

DEPRECADO: Este módulo se mantiene por compatibilidad.
Usar ExtractorRegistry con detect_sections=True en su lugar.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
import logging
import json
import aiofiles
from datetime import datetime
import warnings

logger = logging.getLogger(__name__)

# Deprecation warning
warnings.warn(
    "content_extractor.ContentExtractor está deprecado. "
    "Usar ExtractorRegistry.extract(path, detect_sections=True) en su lugar.",
    DeprecationWarning,
    stacklevel=2
)

class ContentExtractor:
    """Extrae y consolida contenido de boletines."""
    
    def __init__(self, min_section_chars: int = 500):
        """
        Inicializa el extractor.
        
        Args:
            min_section_chars: Tamaño mínimo para considerar una sección completa
        """
        self.min_section_chars = min_section_chars
    
    async def extract_from_pdf(self, pdf_path: Path) -> List[Dict]:
        """
        Extrae contenido de un PDF y lo organiza en secciones lógicas.
        DEPRECADO: Usar ExtractorRegistry.extract(path, detect_sections=True)
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            Lista de secciones con su contenido y metadatos
        """
        from app.services.extractors import ExtractorRegistry
        
        # Usar el registry para extraer con detección de secciones
        result = await ExtractorRegistry.extract(pdf_path, detect_sections=True)
        
        if not result.success:
            logger.error(f"Error extracting PDF: {result.error}")
            return []
        
        # Convertir secciones del nuevo formato al legacy
        sections = []
        for section in result.sections:
            sections.append({
                "content": section.content,
                "metadata": {
                    "boletin": pdf_path.stem,
                    "start_page": section.start_page,
                    "end_page": section.end_page,
                    "section_type": section.section_type.value,
                    **section.metadata
                }
            })
        
        return sections
    
    def _detect_section_type(self, text: str) -> str:
        """
        Detecta el tipo de sección basado en patrones en el texto.
        """
        # Patrones para diferentes tipos de secciones
        patterns = {
            "licitacion": r"(?i)licitaci[oó]n|concurso|adjudicaci[oó]n",
            "nombramiento": r"(?i)nombr[ea]|design[ea]|contrata",
            "resolucion": r"(?i)resoluci[oó]n|decreto|disposici[oó]n",
            "subsidio": r"(?i)subsidio|beneficio|ayuda|asistencia",
            "presupuesto": r"(?i)presupuesto|gasto|inversi[oó]n|fondos"
        }
        
        for section_type, pattern in patterns.items():
            if re.search(pattern, text[:1000]):  # Solo buscar en el inicio
                return section_type
        
        return "general"


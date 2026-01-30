"""
Servicio para extraer y consolidar contenido de boletines
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
import logging
import json
import aiofiles
from datetime import datetime

from PyPDF2 import PdfReader
from tqdm import tqdm

logger = logging.getLogger(__name__)

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
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            Lista de secciones con su contenido y metadatos
        """
        # Extraer texto por páginas
        pdf_reader = PdfReader(pdf_path)
        sections = []
        current_section = {
            "content": "",
            "metadata": {
                "boletin": pdf_path.stem,
                "start_page": 1,
                "end_page": 1,
                "section_type": "unknown"
            }
        }
        
        for i, page in enumerate(pdf_reader.pages, start=1):
            text = page.extract_text()
            if not text:
                continue
                
            # Detectar tipo de sección basado en patrones
            section_type = self._detect_section_type(text)
            
            # Si cambia el tipo de sección o el contenido es muy largo,
            # guardar la sección actual y empezar una nueva
            if (section_type != current_section["metadata"]["section_type"] and 
                len(current_section["content"]) >= self.min_section_chars):
                sections.append(current_section)
                current_section = {
                    "content": text,
                    "metadata": {
                        "boletin": pdf_path.stem,
                        "start_page": i,
                        "end_page": i,
                        "section_type": section_type
                    }
                }
            else:
                current_section["content"] += "\n" + text
                current_section["metadata"]["end_page"] = i
        
        # Agregar última sección
        if len(current_section["content"]) >= self.min_section_chars:
            sections.append(current_section)
        
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


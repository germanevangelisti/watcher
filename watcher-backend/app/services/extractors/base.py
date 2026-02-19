"""
Interfaz base para extractores de PDF.
Épica 2: Extracción - Tarea 2.1
"""

from abc import ABC, abstractmethod
from pathlib import Path
import re
import logging

from app.schemas.extraction import (
    ExtractedContent,
    ExtractionMethod,
    SectionType,
    ContentSection
)

logger = logging.getLogger(__name__)


class PDFExtractor(ABC):
    """
    Interfaz base abstracta para extractores de PDF.
    
    Todos los extractores concretos deben implementar esta interfaz
    para garantizar una API consistente independientemente del método
    de extracción utilizado.
    """

    @property
    @abstractmethod
    def method(self) -> ExtractionMethod:
        """Retorna el método de extracción utilizado por este extractor."""
        pass

    @abstractmethod
    async def extract(
        self,
        file_path: Path,
        detect_sections: bool = False,
        **kwargs
    ) -> ExtractedContent:
        """
        Extrae contenido de un archivo PDF.
        
        Args:
            file_path: Ruta al archivo PDF
            detect_sections: Si True, intenta detectar secciones lógicas
            **kwargs: Argumentos adicionales específicos del extractor
            
        Returns:
            ExtractedContent con el contenido extraído
        """
        pass

    def _detect_section_type(self, text: str) -> SectionType:
        """
        Detecta el tipo de sección basado en patrones en el texto.
        
        Este método es compartido por todos los extractores para garantizar
        detección consistente de secciones.
        
        Args:
            text: Texto de la sección a analizar
            
        Returns:
            SectionType detectado
        """
        # Patrones para diferentes tipos de secciones
        patterns = {
            SectionType.LICITACION: r"(?i)licitaci[oó]n|concurso|adjudicaci[oó]n",
            SectionType.NOMBRAMIENTO: r"(?i)nombr[ea]|design[ea]|contrata",
            SectionType.RESOLUCION: r"(?i)resoluci[oó]n|decreto|disposici[oó]n",
            SectionType.SUBSIDIO: r"(?i)subsidio|beneficio|ayuda|asistencia",
            SectionType.PRESUPUESTO: r"(?i)presupuesto|gasto|inversi[oó]n|fondos"
        }
        
        # Buscar solo en el inicio del texto (primeros 1000 caracteres)
        search_text = text[:1000]
        
        for section_type, pattern in patterns.items():
            if re.search(pattern, search_text):
                return section_type
        
        return SectionType.GENERAL

    def _segment_into_sections(
        self,
        full_text: str,
        pages_text: list,
        min_section_chars: int = 500
    ) -> list[ContentSection]:
        """
        Segmenta el texto completo en secciones lógicas.
        
        Args:
            full_text: Texto completo del documento
            pages_text: Lista de textos por página (para tracking de páginas)
            min_section_chars: Tamaño mínimo para considerar una sección
            
        Returns:
            Lista de ContentSection
        """
        sections = []
        
        # Si el texto es muy corto, retornar una sola sección general
        if len(full_text) < min_section_chars:
            return [
                ContentSection(
                    section_type=SectionType.GENERAL,
                    content=full_text,
                    start_page=1,
                    end_page=len(pages_text) if pages_text else 1,
                    metadata={}
                )
            ]
        
        # Dividir por páginas y agrupar por tipo de sección
        current_section = {
            "content": "",
            "type": SectionType.UNKNOWN,
            "start_page": 1,
            "end_page": 1
        }
        
        for i, page_text in enumerate(pages_text, start=1):
            if not page_text or not page_text.strip():
                continue
                
            # Detectar tipo de sección
            section_type = self._detect_section_type(page_text)
            
            # Si cambia el tipo de sección y tenemos contenido suficiente,
            # guardar la sección actual y empezar una nueva
            if (section_type != current_section["type"] and 
                len(current_section["content"]) >= min_section_chars):
                
                sections.append(
                    ContentSection(
                        section_type=current_section["type"],
                        content=current_section["content"],
                        start_page=current_section["start_page"],
                        end_page=current_section["end_page"],
                        metadata={}
                    )
                )
                
                current_section = {
                    "content": page_text,
                    "type": section_type,
                    "start_page": i,
                    "end_page": i
                }
            else:
                # Agregar a la sección actual
                if not current_section["content"]:
                    current_section["type"] = section_type
                    current_section["start_page"] = i
                
                current_section["content"] += "\n" + page_text
                current_section["end_page"] = i
        
        # Agregar la última sección si tiene contenido suficiente
        if len(current_section["content"]) >= min_section_chars:
            sections.append(
                ContentSection(
                    section_type=current_section["type"],
                    content=current_section["content"],
                    start_page=current_section["start_page"],
                    end_page=current_section["end_page"],
                    metadata={}
                )
            )
        
        # Si no se detectaron secciones, retornar una sección general
        if not sections:
            sections.append(
                ContentSection(
                    section_type=SectionType.GENERAL,
                    content=full_text,
                    start_page=1,
                    end_page=len(pages_text) if pages_text else 1,
                    metadata={}
                )
            )
        
        logger.debug(f"Detected {len(sections)} sections")
        return sections

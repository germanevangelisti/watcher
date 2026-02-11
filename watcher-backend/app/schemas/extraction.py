"""
Schemas unificados para extracción de contenido de documentos PDF.
Épica 2: Extracción - Tarea 2.3
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ExtractionMethod(str, Enum):
    """Métodos de extracción de PDF disponibles."""
    PYPDF2 = "pypdf2"
    PDFPLUMBER = "pdfplumber"


class SectionType(str, Enum):
    """Tipos de secciones detectables en documentos."""
    LICITACION = "licitacion"
    NOMBRAMIENTO = "nombramiento"
    RESOLUCION = "resolucion"
    SUBSIDIO = "subsidio"
    PRESUPUESTO = "presupuesto"
    GENERAL = "general"
    UNKNOWN = "unknown"


class PageContent(BaseModel):
    """Contenido de una página individual del documento."""
    page_number: int = Field(..., description="Número de página (1-indexed)")
    text: str = Field(..., description="Texto extraído de la página")
    char_count: int = Field(..., description="Cantidad de caracteres en la página")

    class Config:
        json_schema_extra = {
            "example": {
                "page_number": 1,
                "text": "BOLETIN OFICIAL...",
                "char_count": 1523
            }
        }


class ContentSection(BaseModel):
    """Sección lógica del documento con tipo y metadata."""
    section_type: SectionType = Field(..., description="Tipo de sección detectada")
    content: str = Field(..., description="Contenido de texto de la sección")
    start_page: int = Field(..., description="Página de inicio de la sección")
    end_page: int = Field(..., description="Página de fin de la sección")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata adicional de la sección")

    class Config:
        json_schema_extra = {
            "example": {
                "section_type": "licitacion",
                "content": "Licitación pública...",
                "start_page": 3,
                "end_page": 5,
                "metadata": {"organismo": "Ministerio de Obras Públicas"}
            }
        }


class ExtractionStats(BaseModel):
    """Estadísticas del proceso de extracción."""
    total_chars: int = Field(..., description="Total de caracteres extraídos")
    total_pages: int = Field(..., description="Total de páginas procesadas")
    total_tokens: Optional[int] = Field(None, description="Total de tokens (si se calculó)")
    extraction_method: ExtractionMethod = Field(..., description="Método utilizado para la extracción")
    extraction_duration_ms: Optional[float] = Field(None, description="Duración de la extracción en milisegundos")

    class Config:
        json_schema_extra = {
            "example": {
                "total_chars": 15234,
                "total_pages": 10,
                "total_tokens": 3500,
                "extraction_method": "pdfplumber",
                "extraction_duration_ms": 450.5
            }
        }


class ExtractedContent(BaseModel):
    """
    Modelo unificado de contenido extraído de un documento PDF.
    
    Este modelo es retornado por todos los extractores de PDF del sistema,
    garantizando una interfaz consistente independientemente del método de extracción.
    """
    success: bool = Field(..., description="Indica si la extracción fue exitosa")
    source_path: str = Field(..., description="Ruta del archivo fuente")
    full_text: str = Field(..., description="Texto completo extraído del documento")
    pages: List[PageContent] = Field(..., description="Contenido por página")
    sections: List[ContentSection] = Field(default_factory=list, description="Secciones lógicas detectadas")
    stats: ExtractionStats = Field(..., description="Estadísticas de la extracción")
    extracted_at: datetime = Field(..., description="Timestamp de la extracción")
    error: Optional[str] = Field(None, description="Mensaje de error si success=False")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata adicional del documento")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "source_path": "/path/to/boletin.pdf",
                "full_text": "BOLETIN OFICIAL...",
                "pages": [
                    {
                        "page_number": 1,
                        "text": "BOLETIN OFICIAL...",
                        "char_count": 1523
                    }
                ],
                "sections": [
                    {
                        "section_type": "licitacion",
                        "content": "Licitación pública...",
                        "start_page": 1,
                        "end_page": 2,
                        "metadata": {}
                    }
                ],
                "stats": {
                    "total_chars": 15234,
                    "total_pages": 10,
                    "total_tokens": 3500,
                    "extraction_method": "pdfplumber",
                    "extraction_duration_ms": 450.5
                },
                "extracted_at": "2026-02-10T12:00:00",
                "error": None,
                "metadata": {"filename": "boletin.pdf"}
            }
        }

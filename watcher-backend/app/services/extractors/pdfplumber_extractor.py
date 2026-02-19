"""
Extractor de PDF usando pdfplumber.
Épica 2: Extracción - Tarea 2.1

Migrado desde dslab_analyzer.py y document_intelligence/agent.py
"""

import time
import logging
from pathlib import Path
from datetime import datetime

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    pdfplumber = None

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    tiktoken = None

from app.schemas.extraction import (
    ExtractedContent,
    ExtractionMethod,
    PageContent,
    ExtractionStats
)
from .base import PDFExtractor

logger = logging.getLogger(__name__)


class PdfPlumberExtractor(PDFExtractor):
    """
    Extractor de PDF usando la biblioteca pdfplumber.
    
    pdfplumber ofrece mejor manejo de PDFs complejos con tablas,
    layouts de múltiples columnas y formatos especiales.
    Es más lento que PyPDF2 pero produce mejor output en documentos complejos.
    """

    def __init__(self, calculate_tokens: bool = True):
        """
        Inicializa el extractor pdfplumber.
        
        Args:
            calculate_tokens: Si True, calcula tokens usando tiktoken
        
        Raises:
            ImportError: Si pdfplumber no está instalado
        """
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError(
                "pdfplumber no está disponible. "
                "Instalar con: pip install pdfplumber"
            )
        
        self.calculate_tokens = calculate_tokens and TIKTOKEN_AVAILABLE
        if self.calculate_tokens:
            try:
                self.encoding = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning(f"No se pudo inicializar tiktoken: {e}")
                self.calculate_tokens = False
                self.encoding = None
        else:
            self.encoding = None

    @property
    def method(self) -> ExtractionMethod:
        """Retorna el método de extracción."""
        return ExtractionMethod.PDFPLUMBER

    async def extract(
        self,
        file_path: Path,
        detect_sections: bool = False,
        **kwargs
    ) -> ExtractedContent:
        """
        Extrae contenido de un PDF usando pdfplumber.
        
        Args:
            file_path: Ruta al archivo PDF
            detect_sections: Si True, detecta secciones lógicas
            **kwargs: Argumentos adicionales (ignorados)
            
        Returns:
            ExtractedContent con el contenido extraído
        """
        start_time = time.time()
        file_path = Path(file_path).resolve()

        # Validar que el archivo existe
        if not file_path.exists():
            return ExtractedContent(
                success=False,
                source_path=str(file_path),
                full_text="",
                pages=[],
                stats=ExtractionStats(
                    total_chars=0,
                    total_pages=0,
                    extraction_method=self.method,
                    extraction_duration_ms=0
                ),
                extracted_at=datetime.utcnow(),
                error=f"File not found: {file_path}"
            )

        try:
            # Abrir y leer el PDF
            with pdfplumber.open(file_path) as pdf:
                num_pages = len(pdf.pages)
                
                logger.debug(f"Extracting {num_pages} pages from {file_path.name}")
                
                # Extraer texto de todas las páginas
                pages_content = []
                pages_text_list = []
                
                for i, page in enumerate(pdf.pages, start=1):
                    try:
                        # pdfplumber puede extraer texto más complejo
                        page_text = page.extract_text()
                        
                        if page_text:
                            pages_text_list.append(page_text)
                            pages_content.append(
                                PageContent(
                                    page_number=i,
                                    text=page_text,
                                    char_count=len(page_text)
                                )
                            )
                        else:
                            # Página vacía o sin texto extraíble
                            pages_text_list.append("")
                            pages_content.append(
                                PageContent(
                                    page_number=i,
                                    text="",
                                    char_count=0
                                )
                            )
                    except Exception as page_error:
                        logger.warning(
                            f"Error extracting page {i} from {file_path.name}: {page_error}"
                        )
                        pages_text_list.append("")
                        pages_content.append(
                            PageContent(
                                page_number=i,
                                text="",
                                char_count=0
                            )
                        )
                
                # Concatenar todo el texto
                full_text = "\n\n".join(pages_text_list)
                
                # Calcular tokens si está habilitado
                total_tokens = None
                if self.calculate_tokens and self.encoding and full_text:
                    try:
                        tokens = self.encoding.encode(full_text)
                        total_tokens = len(tokens)
                    except Exception as e:
                        logger.warning(f"Error calculating tokens: {e}")
                
                # Detectar secciones si está habilitado
                sections = []
                if detect_sections:
                    sections = self._segment_into_sections(
                        full_text,
                        pages_text_list
                    )
                
                # Calcular duración
                duration_ms = (time.time() - start_time) * 1000
                
                # Construir resultado
                return ExtractedContent(
                    success=True,
                    source_path=str(file_path),
                    full_text=full_text,
                    pages=pages_content,
                    sections=sections,
                    stats=ExtractionStats(
                        total_chars=len(full_text),
                        total_pages=num_pages,
                        total_tokens=total_tokens,
                        extraction_method=self.method,
                        extraction_duration_ms=duration_ms
                    ),
                    extracted_at=datetime.utcnow(),
                    metadata={
                        "filename": file_path.name,
                        "file_size_bytes": file_path.stat().st_size,
                        "pages_with_text": sum(1 for p in pages_text_list if p.strip())
                    }
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Error extracting PDF with pdfplumber: {e}", exc_info=True)
            
            return ExtractedContent(
                success=False,
                source_path=str(file_path),
                full_text="",
                pages=[],
                stats=ExtractionStats(
                    total_chars=0,
                    total_pages=0,
                    extraction_method=self.method,
                    extraction_duration_ms=duration_ms
                ),
                extracted_at=datetime.utcnow(),
                error=str(e),
                metadata={
                    "filename": file_path.name if file_path.exists() else "unknown"
                }
            )

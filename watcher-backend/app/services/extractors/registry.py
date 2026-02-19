"""
Registry de extractores de PDF con Strategy Pattern.
Épica 2: Extracción - Tarea 2.2

Proporciona un punto de acceso unificado para todos los extractores.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional

from app.schemas.extraction import ExtractedContent
from .base import PDFExtractor
from .pypdf2_extractor import PyPDF2Extractor
from .pdfplumber_extractor import PdfPlumberExtractor, PDFPLUMBER_AVAILABLE

logger = logging.getLogger(__name__)


class ExtractorRegistry:
    """
    Registry central de extractores de PDF con Strategy Pattern.
    
    Permite seleccionar dinámicamente el extractor a utilizar y
    proporciona una interfaz unificada para la extracción de contenido.
    """

    _extractors: Dict[str, PDFExtractor] = {}
    _default: str = "pdfplumber"  # pdfplumber produce mejor output
    _initialized: bool = False

    @classmethod
    def _initialize(cls):
        """Inicializa el registry con los extractores disponibles."""
        if cls._initialized:
            return

        logger.info("Inicializando ExtractorRegistry...")

        # Registrar PyPDF2 (siempre disponible)
        try:
            cls._extractors["pypdf2"] = PyPDF2Extractor(calculate_tokens=True)
            logger.info("✅ PyPDF2Extractor registrado")
        except Exception as e:
            logger.error(f"❌ Error registrando PyPDF2Extractor: {e}")

        # Registrar pdfplumber (si está disponible)
        if PDFPLUMBER_AVAILABLE:
            try:
                cls._extractors["pdfplumber"] = PdfPlumberExtractor(calculate_tokens=True)
                logger.info("✅ PdfPlumberExtractor registrado")
            except Exception as e:
                logger.error(f"❌ Error registrando PdfPlumberExtractor: {e}")
        else:
            logger.warning("⚠️  pdfplumber no disponible - solo se usará PyPDF2")
            # Si pdfplumber no está disponible, usar pypdf2 como default
            cls._default = "pypdf2"

        # Leer configuración del environment
        env_default = os.getenv("PDF_EXTRACTOR", "").lower()
        if env_default in cls._extractors:
            cls._default = env_default
            logger.info(f"Default extractor configurado via env: {cls._default}")
        elif env_default:
            logger.warning(
                f"PDF_EXTRACTOR={env_default} no es válido. "
                f"Usando default: {cls._default}"
            )

        cls._initialized = True
        logger.info(
            f"ExtractorRegistry inicializado. "
            f"Extractores disponibles: {list(cls._extractors.keys())}, "
            f"Default: {cls._default}"
        )

    @classmethod
    def register(cls, name: str, extractor: PDFExtractor) -> None:
        """
        Registra un nuevo extractor.
        
        Args:
            name: Nombre del extractor
            extractor: Instancia del extractor
        """
        cls._initialize()
        cls._extractors[name] = extractor
        logger.info(f"Extractor '{name}' registrado manualmente")

    @classmethod
    def get(cls, name: Optional[str] = None) -> PDFExtractor:
        """
        Obtiene un extractor por nombre.
        
        Args:
            name: Nombre del extractor. Si es None, usa el default.
            
        Returns:
            PDFExtractor correspondiente
            
        Raises:
            ValueError: Si el extractor no existe
        """
        cls._initialize()

        extractor_name = name or cls._default

        if extractor_name not in cls._extractors:
            available = list(cls._extractors.keys())
            raise ValueError(
                f"Extractor '{extractor_name}' no encontrado. "
                f"Disponibles: {available}"
            )

        return cls._extractors[extractor_name]

    @classmethod
    def get_default(cls) -> str:
        """Retorna el nombre del extractor por defecto."""
        cls._initialize()
        return cls._default

    @classmethod
    def set_default(cls, name: str) -> None:
        """
        Cambia el extractor por defecto.
        
        Args:
            name: Nombre del extractor a usar como default
            
        Raises:
            ValueError: Si el extractor no existe
        """
        cls._initialize()

        if name not in cls._extractors:
            available = list(cls._extractors.keys())
            raise ValueError(
                f"No se puede establecer '{name}' como default. "
                f"Disponibles: {available}"
            )

        cls._default = name
        logger.info(f"Default extractor cambiado a: {name}")

    @classmethod
    def list_extractors(cls) -> list[str]:
        """Lista los nombres de todos los extractores disponibles."""
        cls._initialize()
        return list(cls._extractors.keys())

    @classmethod
    async def extract(
        cls,
        file_path: Path,
        method: Optional[str] = None,
        detect_sections: bool = False,
        **kwargs
    ) -> ExtractedContent:
        """
        Extrae contenido de un PDF usando el extractor especificado.
        
        Este es el método principal para extraer contenido. Si no se
        especifica un método, se usa el extractor por defecto.
        
        Args:
            file_path: Ruta al archivo PDF
            method: Nombre del extractor a usar (None = default)
            detect_sections: Si True, detecta secciones lógicas
            **kwargs: Argumentos adicionales para el extractor
            
        Returns:
            ExtractedContent con el contenido extraído
            
        Example:
            # Usar extractor por defecto
            content = await ExtractorRegistry.extract(Path("doc.pdf"))
            
            # Usar PyPDF2 específicamente
            content = await ExtractorRegistry.extract(
                Path("doc.pdf"),
                method="pypdf2"
            )
            
            # Con detección de secciones
            content = await ExtractorRegistry.extract(
                Path("doc.pdf"),
                detect_sections=True
            )
        """
        extractor = cls.get(method)
        logger.debug(
            f"Extrayendo {file_path.name} con {extractor.method.value}"
        )

        return await extractor.extract(
            file_path,
            detect_sections=detect_sections,
            **kwargs
        )

    @classmethod
    def reset(cls) -> None:
        """Resetea el registry (útil para testing)."""
        cls._extractors.clear()
        cls._initialized = False
        logger.info("ExtractorRegistry reseteado")


# Función helper para uso simple
async def extract_pdf(
    file_path: Path,
    method: Optional[str] = None,
    detect_sections: bool = False,
    **kwargs
) -> ExtractedContent:
    """
    Función helper para extraer contenido de un PDF.
    
    Args:
        file_path: Ruta al archivo PDF
        method: Método de extracción ("pypdf2" o "pdfplumber")
        detect_sections: Si True, detecta secciones lógicas
        **kwargs: Argumentos adicionales
        
    Returns:
        ExtractedContent con el contenido extraído
        
    Example:
        from app.services.extractors.registry import extract_pdf
        
        content = await extract_pdf(Path("boletin.pdf"))
        print(f"Extraídas {content.stats.total_pages} páginas")
    """
    return await ExtractorRegistry.extract(
        file_path,
        method=method,
        detect_sections=detect_sections,
        **kwargs
    )

"""
Módulo de extractores unificados de PDF.
Épica 2: Extracción

Este módulo proporciona una interfaz unificada para extraer contenido
de documentos PDF usando diferentes bibliotecas (PyPDF2, pdfplumber).
"""

from .base import PDFExtractor
from .pypdf2_extractor import PyPDF2Extractor
from .pdfplumber_extractor import PdfPlumberExtractor
from .registry import ExtractorRegistry, extract_pdf

__all__ = [
    "PDFExtractor",
    "PyPDF2Extractor",
    "PdfPlumberExtractor",
    "ExtractorRegistry",
    "extract_pdf",
]

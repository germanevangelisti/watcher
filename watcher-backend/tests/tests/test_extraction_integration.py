"""
Tests de integración para el sistema de extracción unificado.
Épica 2: Extracción - Tarea 2.2
"""

import pytest
from pathlib import Path
import asyncio

from watcher_monolith.backend.app.services.extractors import (
    ExtractorRegistry,
    extract_pdf
)
from watcher_monolith.backend.app.schemas.extraction import (
    ExtractionMethod,
    SectionType
)


class TestExtractorRegistry:
    """Tests de integración del ExtractorRegistry."""

    def test_registry_initialization(self):
        """Test que el registry se inicializa correctamente."""
        extractors = ExtractorRegistry.list_extractors()
        assert len(extractors) >= 1  # Al menos PyPDF2
        assert "pypdf2" in extractors
        
        # pdfplumber puede o no estar disponible
        if "pdfplumber" in extractors:
            assert ExtractorRegistry.get_default() == "pdfplumber"
        else:
            assert ExtractorRegistry.get_default() == "pypdf2"

    def test_get_extractor(self):
        """Test obtener extractores específicos."""
        pypdf2 = ExtractorRegistry.get("pypdf2")
        assert pypdf2 is not None
        assert pypdf2.method == ExtractionMethod.PYPDF2
        
        # Test default
        default = ExtractorRegistry.get()
        assert default is not None

    def test_get_nonexistent_extractor(self):
        """Test que falla al obtener extractor inexistente."""
        with pytest.raises(ValueError):
            ExtractorRegistry.get("nonexistent")

    def test_set_default(self):
        """Test cambiar extractor por defecto."""
        original = ExtractorRegistry.get_default()
        
        # Cambiar a pypdf2
        ExtractorRegistry.set_default("pypdf2")
        assert ExtractorRegistry.get_default() == "pypdf2"
        
        # Restaurar original
        ExtractorRegistry.set_default(original)
        assert ExtractorRegistry.get_default() == original

    def test_set_invalid_default(self):
        """Test que falla al establecer default inválido."""
        with pytest.raises(ValueError):
            ExtractorRegistry.set_default("invalid")

    @pytest.mark.asyncio
    async def test_extract_with_default(self, tmp_path):
        """Test extracción con extractor por defecto."""
        # Crear PDF de prueba
        pdf_path = tmp_path / "test.pdf"
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.drawString(100, 750, "Test Document")
        c.drawString(100, 730, "Integration test for ExtractorRegistry")
        c.showPage()
        c.save()
        
        # Extraer con default
        result = await ExtractorRegistry.extract(pdf_path)
        
        assert result.success is True
        assert result.stats.total_pages == 1
        assert len(result.full_text) > 0
        assert "test" in result.full_text.lower() or "integration" in result.full_text.lower()

    @pytest.mark.asyncio
    async def test_extract_with_specific_method(self, tmp_path):
        """Test extracción especificando método."""
        pdf_path = tmp_path / "test.pdf"
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.drawString(100, 750, "PyPDF2 Test")
        c.showPage()
        c.save()
        
        # Extraer con PyPDF2
        result = await ExtractorRegistry.extract(pdf_path, method="pypdf2")
        
        assert result.success is True
        assert result.stats.extraction_method == ExtractionMethod.PYPDF2

    @pytest.mark.asyncio
    async def test_extract_with_sections(self, tmp_path):
        """Test extracción con detección de secciones."""
        pdf_path = tmp_path / "test_sections.pdf"
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        
        # Página 1: Licitación
        c.drawString(100, 750, "LICITACION PUBLICA 2025")
        c.drawString(100, 730, "Se convoca a licitación...")
        c.showPage()
        
        # Página 2: Resolución
        c.drawString(100, 750, "RESOLUCION 123/2025")
        c.drawString(100, 730, "Se resuelve...")
        c.showPage()
        
        c.save()
        
        # Extraer con secciones
        result = await ExtractorRegistry.extract(pdf_path, detect_sections=True)
        
        assert result.success is True
        assert len(result.sections) > 0
        
        # Verificar que se detectaron tipos de sección
        section_types = [s.section_type for s in result.sections]
        has_specific_types = any(
            t in [SectionType.LICITACION, SectionType.RESOLUCION, SectionType.GENERAL] 
            for t in section_types
        )
        assert has_specific_types

    @pytest.mark.asyncio
    async def test_extract_helper_function(self, tmp_path):
        """Test función helper extract_pdf."""
        pdf_path = tmp_path / "helper_test.pdf"
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.drawString(100, 750, "Helper function test")
        c.showPage()
        c.save()
        
        # Usar helper
        result = await extract_pdf(pdf_path)
        
        assert result.success is True
        assert result.stats.total_pages == 1


class TestCompatibilityWrappers:
    """Tests para los wrappers de compatibilidad."""

    def test_pdf_processor_import(self):
        """Test que PDFProcessor sigue siendo importable."""
        from watcher_monolith.backend.app.services.pdf_service import PDFProcessor
        
        processor = PDFProcessor()
        assert processor is not None

    def test_document_processor_import(self):
        """Test que DocumentProcessor sigue siendo importable."""
        from watcher_monolith.backend.app.services.document_processor import DocumentProcessor
        
        processor = DocumentProcessor()
        assert processor is not None

    def test_content_extractor_import(self):
        """Test que ContentExtractor sigue siendo importable."""
        from watcher_monolith.backend.app.services.content_extractor import ContentExtractor
        
        extractor = ContentExtractor()
        assert extractor is not None

    @pytest.mark.asyncio
    async def test_pdf_processor_extract(self, tmp_path):
        """Test que PDFProcessor._extract_text_from_pdf funciona con registry."""
        from watcher_monolith.backend.app.services.pdf_service import PDFProcessor
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        pdf_path = tmp_path / "compat_test.pdf"
        
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.drawString(100, 750, "Compatibility test")
        c.showPage()
        c.save()
        
        processor = PDFProcessor()
        
        # El método ahora debe usar el registry internamente
        text = processor._extract_text_from_pdf(pdf_path)
        
        assert len(text) > 0
        assert "compatibility" in text.lower() or "test" in text.lower()

    def test_document_processor_extract(self, tmp_path):
        """Test que DocumentProcessor.extract_text_from_pdf funciona con registry."""
        from watcher_monolith.backend.app.services.document_processor import DocumentProcessor
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        pdf_path = tmp_path / "doc_compat_test.pdf"
        
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.drawString(100, 750, "Document processor compatibility test")
        c.showPage()
        c.save()
        
        processor = DocumentProcessor()
        result = processor.extract_text_from_pdf(str(pdf_path))
        
        # Verificar formato legacy
        assert result["success"] is True
        assert "num_pages" in result
        assert "full_text" in result
        assert "pages" in result
        assert result["num_pages"] == 1


class TestEndToEnd:
    """Tests end-to-end del sistema de extracción."""

    @pytest.mark.asyncio
    async def test_full_extraction_pipeline(self, tmp_path):
        """Test pipeline completo de extracción."""
        # Crear PDF con contenido variado
        pdf_path = tmp_path / "complete_test.pdf"
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        
        # Página 1: Licitación
        c.drawString(100, 750, "BOLETIN OFICIAL DE CORDOBA")
        c.drawString(100, 730, "Licitación Pública N° 2025-001")
        c.drawString(100, 710, "Objeto: Construcción de puente")
        c.drawString(100, 690, "Presupuesto estimado: $10.000.000")
        c.showPage()
        
        # Página 2: Nombramiento
        c.drawString(100, 750, "DECRETO 456/2025")
        c.drawString(100, 730, "Se designa a Juan Pérez como Director General")
        c.drawString(100, 710, "del Ministerio de Obras Públicas")
        c.showPage()
        
        # Página 3: Resolución
        c.drawString(100, 750, "RESOLUCION 789/2025")
        c.drawString(100, 730, "Se resuelve aprobar el presupuesto")
        c.drawString(100, 710, "para el ejercicio fiscal 2025")
        c.showPage()
        
        c.save()
        
        # Extraer con secciones
        result = await ExtractorRegistry.extract(pdf_path, detect_sections=True)
        
        # Verificaciones
        assert result.success is True
        assert result.stats.total_pages == 3
        assert len(result.pages) == 3
        assert len(result.sections) > 0
        
        # Verificar que se detectaron múltiples tipos de sección
        section_types = {s.section_type for s in result.sections}
        assert len(section_types) >= 1
        
        # Verificar metadata
        assert result.metadata["filename"] == "complete_test.pdf"
        
        # Verificar contenido
        full_text_lower = result.full_text.lower()
        assert "licitación" in full_text_lower or "licitacion" in full_text_lower
        assert "decreto" in full_text_lower
        assert "resolución" in full_text_lower or "resolucion" in full_text_lower

"""
Tests para los extractores de PDF unificados.
Épica 2: Extracción - Tarea 2.1
"""

import pytest
from pathlib import Path

from watcher_monolith.backend.app.services.extractors import (
    PyPDF2Extractor,
    PdfPlumberExtractor
)
from watcher_monolith.backend.app.schemas.extraction import (
    ExtractionMethod,
    SectionType
)


# Path to test PDF (will be created if needed)
TEST_PDF_DIR = Path(__file__).parent / "fixtures" / "pdfs"


class TestPyPDF2Extractor:
    """Tests para PyPDF2Extractor."""

    @pytest.fixture
    def extractor(self):
        """Fixture que retorna un extractor PyPDF2."""
        return PyPDF2Extractor(calculate_tokens=True)

    def test_extractor_method(self, extractor):
        """Test que el método es correcto."""
        assert extractor.method == ExtractionMethod.PYPDF2

    @pytest.mark.asyncio
    async def test_extract_nonexistent_file(self, extractor):
        """Test extracción de archivo no existente."""
        result = await extractor.extract(Path("/nonexistent/file.pdf"))
        
        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()
        assert result.stats.total_pages == 0
        assert result.stats.total_chars == 0
        assert result.stats.extraction_method == ExtractionMethod.PYPDF2

    @pytest.mark.asyncio
    async def test_extract_basic_pdf(self, extractor, tmp_path):
        """Test extracción básica de PDF."""
        # Crear un PDF simple de prueba
        pdf_path = tmp_path / "test.pdf"
        
        # Crear un PDF simple con PyPDF2
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import io
        
        # Crear contenido con reportlab
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, "Test Document")
        c.drawString(100, 730, "This is a test PDF for extraction.")
        c.showPage()
        c.save()
        
        # Guardar el PDF
        buffer.seek(0)
        with open(pdf_path, 'wb') as f:
            f.write(buffer.read())
        
        # Extraer
        result = await extractor.extract(pdf_path)
        
        assert result.success is True
        assert result.error is None
        assert result.stats.total_pages == 1
        assert result.stats.total_chars > 0
        assert len(result.pages) == 1
        assert result.pages[0].page_number == 1
        assert result.stats.extraction_method == ExtractionMethod.PYPDF2

    @pytest.mark.asyncio
    async def test_extract_with_sections(self, extractor, tmp_path):
        """Test extracción con detección de secciones."""
        # Crear un PDF con contenido que active detección de secciones
        pdf_path = tmp_path / "test_sections.pdf"
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import io
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Página 1: Licitación
        c.drawString(100, 750, "LICITACION PUBLICA N 123")
        c.drawString(100, 730, "Se convoca a licitación pública...")
        c.showPage()
        
        # Página 2: Resolución
        c.drawString(100, 750, "RESOLUCION 456/2025")
        c.drawString(100, 730, "Se resuelve designar...")
        c.showPage()
        
        c.save()
        buffer.seek(0)
        
        with open(pdf_path, 'wb') as f:
            f.write(buffer.read())
        
        # Extraer con detección de secciones
        result = await extractor.extract(pdf_path, detect_sections=True)
        
        assert result.success is True
        assert result.stats.total_pages == 2
        assert len(result.sections) > 0
        
        # Verificar que se detectaron tipos de sección
        section_types = [s.section_type for s in result.sections]
        assert any(t in [SectionType.LICITACION, SectionType.GENERAL] for t in section_types)


class TestPdfPlumberExtractor:
    """Tests para PdfPlumberExtractor."""

    @pytest.fixture
    def extractor(self):
        """Fixture que retorna un extractor pdfplumber."""
        try:
            return PdfPlumberExtractor(calculate_tokens=True)
        except ImportError:
            pytest.skip("pdfplumber no está disponible")

    def test_extractor_method(self, extractor):
        """Test que el método es correcto."""
        assert extractor.method == ExtractionMethod.PDFPLUMBER

    @pytest.mark.asyncio
    async def test_extract_nonexistent_file(self, extractor):
        """Test extracción de archivo no existente."""
        result = await extractor.extract(Path("/nonexistent/file.pdf"))
        
        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()
        assert result.stats.total_pages == 0
        assert result.stats.extraction_method == ExtractionMethod.PDFPLUMBER

    @pytest.mark.asyncio
    async def test_extract_basic_pdf(self, extractor, tmp_path):
        """Test extracción básica de PDF."""
        # Crear un PDF simple
        pdf_path = tmp_path / "test.pdf"
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.drawString(100, 750, "Test Document")
        c.drawString(100, 730, "This is a test PDF for pdfplumber extraction.")
        c.showPage()
        c.save()
        
        # Extraer
        result = await extractor.extract(pdf_path)
        
        assert result.success is True
        assert result.error is None
        assert result.stats.total_pages == 1
        assert result.stats.total_chars > 0
        assert len(result.pages) == 1
        assert result.stats.extraction_method == ExtractionMethod.PDFPLUMBER

    @pytest.mark.asyncio
    async def test_extract_with_sections(self, extractor, tmp_path):
        """Test extracción con detección de secciones."""
        pdf_path = tmp_path / "test_sections.pdf"
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        
        # Página 1
        c.drawString(100, 750, "DECRETO 789/2025")
        c.drawString(100, 730, "Se decreta lo siguiente...")
        c.showPage()
        
        # Página 2
        c.drawString(100, 750, "NOMBRAMIENTO")
        c.drawString(100, 730, "Se nombra a Juan Pérez...")
        c.showPage()
        
        c.save()
        
        # Extraer con secciones
        result = await extractor.extract(pdf_path, detect_sections=True)
        
        assert result.success is True
        assert result.stats.total_pages == 2
        assert len(result.sections) > 0


class TestExtractorComparison:
    """Tests que comparan ambos extractores."""

    @pytest.fixture
    def pypdf2_extractor(self):
        return PyPDF2Extractor(calculate_tokens=False)

    @pytest.fixture
    def pdfplumber_extractor(self):
        try:
            return PdfPlumberExtractor(calculate_tokens=False)
        except ImportError:
            pytest.skip("pdfplumber no está disponible")

    @pytest.mark.asyncio
    async def test_both_extractors_same_pdf(
        self, 
        pypdf2_extractor, 
        pdfplumber_extractor, 
        tmp_path
    ):
        """Test que ambos extractores producen resultados similares."""
        # Crear PDF de prueba
        pdf_path = tmp_path / "comparison.pdf"
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.drawString(100, 750, "Comparison Test")
        c.drawString(100, 730, "Both extractors should extract this text.")
        c.showPage()
        c.save()
        
        # Extraer con ambos
        result_pypdf2 = await pypdf2_extractor.extract(pdf_path)
        result_pdfplumber = await pdfplumber_extractor.extract(pdf_path)
        
        # Ambos deben tener éxito
        assert result_pypdf2.success is True
        assert result_pdfplumber.success is True
        
        # Misma cantidad de páginas
        assert result_pypdf2.stats.total_pages == result_pdfplumber.stats.total_pages
        
        # Ambos deben tener contenido
        assert len(result_pypdf2.full_text) > 0
        assert len(result_pdfplumber.full_text) > 0
        
        # Métodos correctos
        assert result_pypdf2.stats.extraction_method == ExtractionMethod.PYPDF2
        assert result_pdfplumber.stats.extraction_method == ExtractionMethod.PDFPLUMBER


class TestSectionDetection:
    """Tests específicos para detección de secciones."""

    @pytest.fixture
    def extractor(self):
        return PyPDF2Extractor()

    def test_detect_licitacion(self, extractor):
        """Test detección de sección de licitación."""
        text = "LICITACIÓN PÚBLICA N° 123/2025\nSe convoca a licitación..."
        section_type = extractor._detect_section_type(text)
        assert section_type == SectionType.LICITACION

    def test_detect_resolucion(self, extractor):
        """Test detección de sección de resolución."""
        text = "RESOLUCIÓN 456/2025\nArtículo 1°..."
        section_type = extractor._detect_section_type(text)
        assert section_type == SectionType.RESOLUCION

    def test_detect_nombramiento(self, extractor):
        """Test detección de sección de nombramiento."""
        text = "Se designa a Juan Pérez como Director..."
        section_type = extractor._detect_section_type(text)
        assert section_type == SectionType.NOMBRAMIENTO

    def test_detect_subsidio(self, extractor):
        """Test detección de sección de subsidio."""
        text = "SUBSIDIO HABITACIONAL\nSe otorga beneficio..."
        section_type = extractor._detect_section_type(text)
        assert section_type == SectionType.SUBSIDIO

    def test_detect_presupuesto(self, extractor):
        """Test detección de sección de presupuesto."""
        text = "PRESUPUESTO 2025\nInversión total..."
        section_type = extractor._detect_section_type(text)
        assert section_type == SectionType.PRESUPUESTO

    def test_detect_general(self, extractor):
        """Test detección de sección general (default)."""
        text = "Contenido general sin palabras clave específicas."
        section_type = extractor._detect_section_type(text)
        assert section_type == SectionType.GENERAL

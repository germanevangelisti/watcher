"""
Tests para los schemas de extracción de contenido.
Épica 2: Extracción - Tarea 2.3
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from watcher_monolith.backend.app.schemas.extraction import (
    ExtractionMethod,
    SectionType,
    PageContent,
    ContentSection,
    ExtractionStats,
    ExtractedContent
)


class TestExtractionMethod:
    """Tests para el enum ExtractionMethod."""

    def test_valid_methods(self):
        """Test que los métodos válidos se pueden crear."""
        assert ExtractionMethod.PYPDF2 == "pypdf2"
        assert ExtractionMethod.PDFPLUMBER == "pdfplumber"

    def test_enum_values(self):
        """Test que los valores del enum son correctos."""
        methods = [m.value for m in ExtractionMethod]
        assert "pypdf2" in methods
        assert "pdfplumber" in methods


class TestSectionType:
    """Tests para el enum SectionType."""

    def test_valid_section_types(self):
        """Test que los tipos de sección válidos se pueden crear."""
        assert SectionType.LICITACION == "licitacion"
        assert SectionType.NOMBRAMIENTO == "nombramiento"
        assert SectionType.RESOLUCION == "resolucion"
        assert SectionType.SUBSIDIO == "subsidio"
        assert SectionType.PRESUPUESTO == "presupuesto"
        assert SectionType.GENERAL == "general"
        assert SectionType.UNKNOWN == "unknown"

    def test_enum_values(self):
        """Test que todos los tipos están presentes."""
        types = [t.value for t in SectionType]
        expected = ["licitacion", "nombramiento", "resolucion", "subsidio", "presupuesto", "general", "unknown"]
        for expected_type in expected:
            assert expected_type in types


class TestPageContent:
    """Tests para el modelo PageContent."""

    def test_valid_page_content(self):
        """Test creación de PageContent válido."""
        page = PageContent(
            page_number=1,
            text="Contenido de la página",
            char_count=22
        )
        assert page.page_number == 1
        assert page.text == "Contenido de la página"
        assert page.char_count == 22

    def test_page_content_serialization(self):
        """Test serialización a dict."""
        page = PageContent(
            page_number=5,
            text="Texto de prueba",
            char_count=15
        )
        data = page.model_dump()
        assert data["page_number"] == 5
        assert data["text"] == "Texto de prueba"
        assert data["char_count"] == 15

    def test_page_content_from_dict(self):
        """Test deserialización desde dict."""
        data = {
            "page_number": 3,
            "text": "Página 3",
            "char_count": 8
        }
        page = PageContent(**data)
        assert page.page_number == 3
        assert page.text == "Página 3"

    def test_missing_required_fields(self):
        """Test que falla si faltan campos requeridos."""
        with pytest.raises(ValidationError):
            PageContent(page_number=1)  # Missing text and char_count


class TestContentSection:
    """Tests para el modelo ContentSection."""

    def test_valid_content_section(self):
        """Test creación de ContentSection válido."""
        section = ContentSection(
            section_type=SectionType.LICITACION,
            content="Contenido de licitación",
            start_page=1,
            end_page=3,
            metadata={"organismo": "Test"}
        )
        assert section.section_type == SectionType.LICITACION
        assert section.content == "Contenido de licitación"
        assert section.start_page == 1
        assert section.end_page == 3
        assert section.metadata["organismo"] == "Test"

    def test_default_metadata(self):
        """Test que metadata tiene default vacío."""
        section = ContentSection(
            section_type=SectionType.GENERAL,
            content="Contenido general",
            start_page=1,
            end_page=1
        )
        assert section.metadata == {}

    def test_section_serialization(self):
        """Test serialización a dict."""
        section = ContentSection(
            section_type=SectionType.RESOLUCION,
            content="Resolución 123",
            start_page=2,
            end_page=4
        )
        data = section.model_dump()
        assert data["section_type"] == "resolucion"
        assert data["content"] == "Resolución 123"


class TestExtractionStats:
    """Tests para el modelo ExtractionStats."""

    def test_valid_extraction_stats(self):
        """Test creación de ExtractionStats válido."""
        stats = ExtractionStats(
            total_chars=10000,
            total_pages=5,
            total_tokens=2500,
            extraction_method=ExtractionMethod.PDFPLUMBER,
            extraction_duration_ms=123.45
        )
        assert stats.total_chars == 10000
        assert stats.total_pages == 5
        assert stats.total_tokens == 2500
        assert stats.extraction_method == ExtractionMethod.PDFPLUMBER
        assert stats.extraction_duration_ms == 123.45

    def test_optional_fields(self):
        """Test que campos opcionales pueden ser None."""
        stats = ExtractionStats(
            total_chars=5000,
            total_pages=3,
            extraction_method=ExtractionMethod.PYPDF2
        )
        assert stats.total_tokens is None
        assert stats.extraction_duration_ms is None

    def test_stats_serialization(self):
        """Test serialización a dict."""
        stats = ExtractionStats(
            total_chars=1000,
            total_pages=2,
            extraction_method=ExtractionMethod.PYPDF2
        )
        data = stats.model_dump()
        assert data["total_chars"] == 1000
        assert data["extraction_method"] == "pypdf2"


class TestExtractedContent:
    """Tests para el modelo principal ExtractedContent."""

    def test_valid_extracted_content(self):
        """Test creación de ExtractedContent válido."""
        now = datetime.utcnow()
        content = ExtractedContent(
            success=True,
            source_path="/path/to/doc.pdf",
            full_text="Texto completo del documento",
            pages=[
                PageContent(page_number=1, text="Página 1", char_count=8)
            ],
            sections=[
                ContentSection(
                    section_type=SectionType.GENERAL,
                    content="Sección 1",
                    start_page=1,
                    end_page=1
                )
            ],
            stats=ExtractionStats(
                total_chars=100,
                total_pages=1,
                extraction_method=ExtractionMethod.PYPDF2
            ),
            extracted_at=now
        )
        assert content.success is True
        assert content.source_path == "/path/to/doc.pdf"
        assert len(content.pages) == 1
        assert len(content.sections) == 1

    def test_default_empty_sections(self):
        """Test que sections tiene default vacío."""
        now = datetime.utcnow()
        content = ExtractedContent(
            success=True,
            source_path="/path/to/doc.pdf",
            full_text="Texto",
            pages=[PageContent(page_number=1, text="Text", char_count=4)],
            stats=ExtractionStats(
                total_chars=4,
                total_pages=1,
                extraction_method=ExtractionMethod.PYPDF2
            ),
            extracted_at=now
        )
        assert content.sections == []

    def test_default_metadata(self):
        """Test que metadata tiene default vacío."""
        now = datetime.utcnow()
        content = ExtractedContent(
            success=True,
            source_path="/path/to/doc.pdf",
            full_text="Texto",
            pages=[PageContent(page_number=1, text="Text", char_count=4)],
            stats=ExtractionStats(
                total_chars=4,
                total_pages=1,
                extraction_method=ExtractionMethod.PYPDF2
            ),
            extracted_at=now
        )
        assert content.metadata == {}

    def test_error_case(self):
        """Test caso de error en extracción."""
        now = datetime.utcnow()
        content = ExtractedContent(
            success=False,
            source_path="/path/to/bad.pdf",
            full_text="",
            pages=[],
            stats=ExtractionStats(
                total_chars=0,
                total_pages=0,
                extraction_method=ExtractionMethod.PYPDF2
            ),
            extracted_at=now,
            error="File not found"
        )
        assert content.success is False
        assert content.error == "File not found"
        assert content.full_text == ""
        assert len(content.pages) == 0

    def test_complete_example(self):
        """Test con ejemplo completo."""
        now = datetime.utcnow()
        content = ExtractedContent(
            success=True,
            source_path="/boletines/2025/01/20250115_1_Secc.pdf",
            full_text="BOLETIN OFICIAL\nContenido del boletín...",
            pages=[
                PageContent(page_number=1, text="BOLETIN OFICIAL", char_count=15),
                PageContent(page_number=2, text="Contenido del boletín...", char_count=24)
            ],
            sections=[
                ContentSection(
                    section_type=SectionType.LICITACION,
                    content="Licitación pública nro 123",
                    start_page=1,
                    end_page=1,
                    metadata={"numero": "123"}
                ),
                ContentSection(
                    section_type=SectionType.NOMBRAMIENTO,
                    content="Designación de funcionario",
                    start_page=2,
                    end_page=2,
                    metadata={"cargo": "Director"}
                )
            ],
            stats=ExtractionStats(
                total_chars=39,
                total_pages=2,
                total_tokens=12,
                extraction_method=ExtractionMethod.PDFPLUMBER,
                extraction_duration_ms=234.56
            ),
            extracted_at=now,
            metadata={
                "filename": "20250115_1_Secc.pdf",
                "boletin_date": "2025-01-15",
                "section": "1"
            }
        )

        # Verificaciones
        assert content.success is True
        assert len(content.pages) == 2
        assert len(content.sections) == 2
        assert content.stats.total_pages == 2
        assert content.metadata["filename"] == "20250115_1_Secc.pdf"

        # Serialización
        data = content.model_dump()
        assert data["success"] is True
        assert len(data["pages"]) == 2
        assert data["stats"]["extraction_method"] == "pdfplumber"

    def test_json_serialization(self):
        """Test serialización a JSON."""
        now = datetime.utcnow()
        content = ExtractedContent(
            success=True,
            source_path="/test.pdf",
            full_text="Test",
            pages=[PageContent(page_number=1, text="Test", char_count=4)],
            stats=ExtractionStats(
                total_chars=4,
                total_pages=1,
                extraction_method=ExtractionMethod.PYPDF2
            ),
            extracted_at=now
        )
        json_str = content.model_dump_json()
        assert isinstance(json_str, str)
        assert "test.pdf" in json_str
        assert "pypdf2" in json_str

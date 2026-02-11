"""
Unit tests for DIA (Data Integration Adapters) layer.

Tests adapters and document schema normalization.
"""

import pytest
from datetime import date, datetime
from pathlib import Path
import sys

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(backend_path))

from app.adapters.base_adapter import (
    BaseAdapter,
    AdapterResult,
    DocumentSchema,
    SourceType,
    DocumentCategory
)
from app.adapters.sca_prov import ProvincialAdapter, create_provincial_adapter


# ============================================================================
# Document Schema Tests
# ============================================================================

@pytest.mark.dia
def test_document_schema_creation():
    """Test DocumentSchema creation with required fields."""
    schema = DocumentSchema(
        source_type=SourceType.PROVINCIAL,
        document_id="test_123",
        filename="test.pdf",
        category=DocumentCategory.BOLETIN,
        document_date=date(2026, 1, 1)
    )
    
    assert schema.source_type == SourceType.PROVINCIAL
    assert schema.document_id == "test_123"
    assert schema.filename == "test.pdf"
    assert schema.category == DocumentCategory.BOLETIN
    assert schema.document_date == date(2026, 1, 1)
    assert schema.extraction_status == "pending"  # Default


@pytest.mark.dia
def test_document_schema_to_dict(sample_document_schema):
    """Test DocumentSchema serialization to dict."""
    schema_dict = sample_document_schema.to_dict()
    
    assert isinstance(schema_dict, dict)
    assert schema_dict["source_type"] == "provincial"
    assert schema_dict["document_id"] == "prov_20260101_1"
    assert schema_dict["filename"] == "20260101_1_Secc.pdf"
    assert schema_dict["category"] == "boletin"
    assert "2026-01-01" in schema_dict["document_date"]
    assert schema_dict["jurisdiction_id"] == 1


@pytest.mark.dia
def test_document_schema_with_metadata():
    """Test DocumentSchema with custom metadata."""
    metadata = {
        "test_field": "test_value",
        "number": 123,
        "nested": {"key": "value"}
    }
    
    schema = DocumentSchema(
        source_type=SourceType.MUNICIPAL,
        document_id="test",
        filename="test.pdf",
        category=DocumentCategory.CONTRATO,
        document_date=date(2026, 1, 1),
        metadata=metadata
    )
    
    assert schema.metadata == metadata
    assert schema.metadata["test_field"] == "test_value"
    assert schema.metadata["nested"]["key"] == "value"


# ============================================================================
# Provincial Adapter Tests
# ============================================================================

@pytest.mark.dia
def test_provincial_adapter_init():
    """Test ProvincialAdapter initialization."""
    adapter = ProvincialAdapter()
    
    assert adapter.source_type == SourceType.PROVINCIAL
    assert adapter.default_jurisdiction_id == 1
    assert adapter.default_jurisdiction_name == "Provincia de Córdoba"
    assert adapter.stats["total_processed"] == 0


@pytest.mark.dia
@pytest.mark.asyncio
async def test_provincial_adapter_adapt_document(sample_bulletin_data):
    """Test document transformation to DocumentSchema."""
    adapter = create_provincial_adapter()
    
    result = await adapter.adapt_document(sample_bulletin_data)
    
    assert result.success is True
    assert result.document is not None
    assert result.document.source_type == SourceType.PROVINCIAL
    assert result.document.filename == "20260101_1_Secc.pdf"
    assert result.document.category == DocumentCategory.BOLETIN
    assert result.document.jurisdiction_id == 1


@pytest.mark.dia
@pytest.mark.asyncio
async def test_provincial_adapter_adapt_document_missing_filename():
    """Test adapter with missing required field."""
    adapter = create_provincial_adapter()
    
    result = await adapter.adapt_document({
        "date": "2026-01-01"
        # Missing filename
    })
    
    assert result.success is False
    assert result.error is not None
    assert "filename" in result.error.lower()


@pytest.mark.dia
@pytest.mark.asyncio
async def test_provincial_adapter_parse_date_from_string():
    """Test date parsing from ISO string."""
    adapter = create_provincial_adapter()
    
    data = {
        "filename": "test.pdf",
        "date": "2026-01-15",
        "section": "1"
    }
    
    result = await adapter.adapt_document(data)
    
    assert result.success is True
    assert result.document.document_date == date(2026, 1, 15)


@pytest.mark.dia
@pytest.mark.asyncio
async def test_provincial_adapter_parse_date_from_filename():
    """Test date parsing from filename when date field missing."""
    adapter = create_provincial_adapter()
    
    data = {
        "filename": "20260120_1_Secc.pdf",
        "section": "1"
    }
    
    result = await adapter.adapt_document(data)
    
    assert result.success is True
    assert result.document.document_date == date(2026, 1, 20)


@pytest.mark.dia
@pytest.mark.asyncio
async def test_provincial_adapter_parse_section_from_data():
    """Test section parsing from data."""
    adapter = create_provincial_adapter()
    
    data = {
        "filename": "20260101_3_Secc.pdf",
        "date": "2026-01-01",
        "section": 3
    }
    
    result = await adapter.adapt_document(data)
    
    assert result.success is True
    assert result.document.section == "3"


@pytest.mark.dia
@pytest.mark.asyncio
async def test_provincial_adapter_parse_section_from_filename():
    """Test section parsing from filename."""
    adapter = create_provincial_adapter()
    
    data = {
        "filename": "20260101_4_Secc.pdf",
        "date": "2026-01-01"
    }
    
    result = await adapter.adapt_document(data)
    
    assert result.success is True
    assert result.document.section == "4"


@pytest.mark.dia
def test_provincial_adapter_validation(sample_document_schema):
    """Test document validation."""
    adapter = create_provincial_adapter()
    
    # Valid document
    assert adapter.validate_document(sample_document_schema) is True
    
    # Invalid document - missing required field
    invalid_schema = DocumentSchema(
        source_type=SourceType.PROVINCIAL,
        document_id="",  # Empty ID
        filename="test.pdf",
        category=DocumentCategory.BOLETIN,
        document_date=date(2026, 1, 1)
    )
    assert adapter.validate_document(invalid_schema) is False


@pytest.mark.dia
@pytest.mark.asyncio
async def test_provincial_adapter_batch(sample_bulletin_data):
    """Test batch processing of documents."""
    adapter = create_provincial_adapter()
    
    # Create multiple bulletins
    bulletins = [
        {**sample_bulletin_data, "filename": f"2026010{i}_1_Secc.pdf"}
        for i in range(1, 4)
    ]
    
    results = await adapter.adapt_batch(bulletins)
    
    assert len(results) == 3
    assert all(r.success for r in results)
    assert adapter.stats["total_processed"] == 3
    assert adapter.stats["successful"] == 3


@pytest.mark.dia
@pytest.mark.asyncio
async def test_provincial_adapter_generate_title():
    """Test automatic title generation."""
    adapter = create_provincial_adapter()
    
    data = {
        "filename": "20260101_1_Secc.pdf",
        "date": "2026-01-01",
        "section": 1
    }
    
    result = await adapter.adapt_document(data)
    
    assert result.success is True
    assert "Boletín Oficial de Córdoba" in result.document.title
    assert "01/01/2026" in result.document.title
    assert "Sección 1" in result.document.title


@pytest.mark.dia
def test_adapter_stats_tracking():
    """Test adapter statistics tracking."""
    adapter = create_provincial_adapter()
    
    # Simulate successful adaptation
    result = AdapterResult(
        success=True,
        document=DocumentSchema(
            source_type=SourceType.PROVINCIAL,
            document_id="test",
            filename="test.pdf",
            category=DocumentCategory.BOLETIN,
            document_date=date(2026, 1, 1)
        )
    )
    adapter._update_stats(result)
    
    stats = adapter.get_stats()
    assert stats["total_processed"] == 1
    assert stats["successful"] == 1
    assert stats["failed"] == 0
    
    # Simulate failed adaptation
    result_failed = AdapterResult(
        success=False,
        error="Test error",
        warnings=["Warning 1", "Warning 2"]
    )
    adapter._update_stats(result_failed)
    
    stats = adapter.get_stats()
    assert stats["total_processed"] == 2
    assert stats["successful"] == 1
    assert stats["failed"] == 1
    assert stats["warnings"] == 2


@pytest.mark.dia
def test_adapter_reset_stats():
    """Test resetting adapter statistics."""
    adapter = create_provincial_adapter()
    
    # Add stats
    result = AdapterResult(success=True, document=None)
    adapter._update_stats(result)
    
    assert adapter.get_stats()["successful"] == 1
    
    # Reset
    adapter.reset_stats()
    
    stats = adapter.get_stats()
    assert stats["total_processed"] == 0
    assert stats["successful"] == 0
    assert stats["failed"] == 0

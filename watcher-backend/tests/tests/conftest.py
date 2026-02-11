"""
Pytest configuration and shared fixtures for Watcher Agent tests.
"""

import pytest
import sys
from pathlib import Path
from datetime import date, datetime
from typing import Dict, Any
from unittest.mock import MagicMock, AsyncMock

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(backend_path))


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def mock_async_session():
    """Mock async database session."""
    from unittest.mock import AsyncMock
    session = AsyncMock()
    return session


# ============================================================================
# Scraper Fixtures
# ============================================================================

@pytest.fixture
def sample_scraper_config():
    """Sample scraper configuration."""
    from app.scrapers.base_scraper import ScraperConfig, ScraperType
    
    return ScraperConfig(
        scraper_type=ScraperType.PROVINCIAL,
        base_url="https://test.example.com",
        output_dir=Path("/tmp/test_boletines"),
        rate_limit_delay=0.1,  # Fast for testing
        max_retries=2,
        timeout=5.0,
        skip_weekends=True,
        sections=[1, 2, 3]
    )


@pytest.fixture
def sample_scraper_result():
    """Sample scraper result."""
    from app.scrapers.base_scraper import ScraperResult
    
    return ScraperResult(
        filename="20260101_1_Secc.pdf",
        status="downloaded",
        size=1024000,
        path="2026/01/20260101_1_Secc.pdf",
        url="https://test.example.com/file.pdf",
        metadata={"date": "2026-01-01", "section": 1}
    )


# ============================================================================
# Adapter Fixtures
# ============================================================================

@pytest.fixture
def sample_bulletin_data():
    """Sample bulletin raw data for adapter testing."""
    return {
        "filename": "20260101_1_Secc.pdf",
        "date": "2026-01-01",
        "section": "1",
        "content": "Contenido de prueba del boletín oficial. DECRETO 123/2026. "
                  "La empresa TEST SA recibe un subsidio de $1.000.000.",
        "size": 1024000,
        "file_path": "/tmp/test/20260101_1_Secc.pdf"
    }


@pytest.fixture
def sample_document_schema():
    """Sample DocumentSchema for testing."""
    from app.adapters.base_adapter import DocumentSchema, SourceType, DocumentCategory
    
    return DocumentSchema(
        source_type=SourceType.PROVINCIAL,
        document_id="prov_20260101_1",
        filename="20260101_1_Secc.pdf",
        category=DocumentCategory.BOLETIN,
        document_date=date(2026, 1, 1),
        ingestion_date=datetime(2026, 1, 1, 10, 0, 0),
        title="Boletín Oficial de Córdoba - 01/01/2026 - Sección 1",
        content="Contenido de prueba",
        jurisdiction_id=1,
        jurisdiction_name="Provincia de Córdoba",
        section="1",
        file_path="2026/01/20260101_1_Secc.pdf",
        file_size=1024000,
        extraction_status="completed"
    )


# ============================================================================
# Embedding Service Fixtures
# ============================================================================

@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    service = MagicMock()
    service.collection = MagicMock()
    service.collection_name = "test_collection"
    service.add_document = AsyncMock(return_value={
        "success": True,
        "document_id": "test_1",
        "chunks_created": 3
    })
    service.search = AsyncMock(return_value=[
        {
            "id": "test_1_chunk_0",
            "document": "Test document content",
            "metadata": {"test": True},
            "distance": 0.5
        }
    ])
    service.get_stats = MagicMock(return_value={
        "embeddings_created": 10,
        "documents_added": 3,
        "searches_performed": 5
    })
    return service


@pytest.fixture
def sample_text_for_chunking():
    """Sample text for chunking tests."""
    return """
    Este es un texto de prueba para testing de chunking.
    Contiene múltiples oraciones y párrafos.
    
    El objetivo es verificar que el chunking funciona correctamente.
    Debe respetar los límites de oraciones cuando sea posible.
    
    Este es el tercer párrafo del texto de prueba.
    Contiene información adicional para los tests.
    """ * 10  # Repetir para hacer el texto más largo


# ============================================================================
# Agent Fixtures
# ============================================================================

@pytest.fixture
def mock_kba_agent():
    """Mock Knowledge Base Agent."""
    from agents.kba_agent import KnowledgeBaseAgent
    agent = KnowledgeBaseAgent()
    return agent


@pytest.fixture
def mock_raga_agent():
    """Mock RAG Agent."""
    from agents.raga_agent import RAGAgent
    agent = RAGAgent()
    # Mock embedding service
    agent.embedding_service = MagicMock()
    return agent


@pytest.fixture
def sample_agent_task():
    """Sample agent task."""
    class MockTask:
        def __init__(self, task_type: str, parameters: Dict[str, Any]):
            self.task_type = task_type
            self.parameters = parameters
    
    return MockTask


# ============================================================================
# Output Fixtures
# ============================================================================

@pytest.fixture
def sample_alert_data():
    """Sample alert data."""
    return {
        "title": "Test Alert",
        "message": "This is a test alert",
        "priority": "high",
        "category": "test",
        "metadata": {"test": True}
    }


@pytest.fixture
def sample_report_data():
    """Sample report data."""
    return {
        "period": "Test Period",
        "total_documents": 100,
        "high_risk_count": 5,
        "total_amount": 1000000,
        "key_findings": [
            "Finding 1",
            "Finding 2",
            "Finding 3"
        ],
        "recommendations": [
            "Recommendation 1",
            "Recommendation 2"
        ]
    }


# ============================================================================
# HTTP Client Fixtures
# ============================================================================

@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing scrapers."""
    import httpx
    from unittest.mock import PropertyMock
    
    # Create mock response with proper attribute access
    mock_response = MagicMock()
    type(mock_response).status_code = PropertyMock(return_value=200)
    type(mock_response).headers = PropertyMock(return_value={"Content-Type": "application/pdf"})
    type(mock_response).content = PropertyMock(return_value=b"PDF content" * 1000)
    
    # Create async context manager that returns the client
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    
    # Make it work as async context manager
    async_context = AsyncMock()
    async_context.__aenter__ = AsyncMock(return_value=mock_client)
    async_context.__aexit__ = AsyncMock(return_value=None)
    
    return async_context


# ============================================================================
# File System Fixtures
# ============================================================================

@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary output directory for tests."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a sample PDF file for testing."""
    pdf_path = tmp_path / "sample.pdf"
    # Create a minimal PDF-like file
    pdf_path.write_bytes(b"%PDF-1.4\n" + b"test content" * 1000)
    return pdf_path


# ============================================================================
# Database Model Fixtures
# ============================================================================

@pytest.fixture
def sample_boletin_model():
    """Sample Boletin database model."""
    from app.db.models import Boletin
    
    return Boletin(
        id=1,
        filename="20260101_1_Secc.pdf",
        date=date(2026, 1, 1),
        section="1",
        fuente="test",
        contenido="Test content",
        status="completed",
        jurisdiccion_id=1,
        metadata={"test": True}
    )


# ============================================================================
# Pytest Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "pds: mark test as PDS layer test")
    config.addinivalue_line("markers", "dia: mark test as DIA layer test")
    config.addinivalue_line("markers", "kaa: mark test as KAA layer test")
    config.addinivalue_line("markers", "oex: mark test as OEx layer test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# ============================================================================
# Helper Functions
# ============================================================================

@pytest.fixture
def assert_scraper_stats():
    """Helper to assert scraper statistics."""
    def _assert(stats: Dict[str, Any], expected: Dict[str, Any]):
        for key, value in expected.items():
            assert key in stats, f"Key '{key}' not in stats"
            assert stats[key] == value, f"Expected {key}={value}, got {stats[key]}"
    return _assert


@pytest.fixture
def assert_adapter_result():
    """Helper to assert adapter results."""
    def _assert(result, success: bool = True, has_document: bool = True):
        assert hasattr(result, 'success'), "Result missing 'success' attribute"
        assert result.success == success, f"Expected success={success}, got {result.success}"
        
        if has_document and success:
            assert result.document is not None, "Expected document in result"
        
        if not success:
            assert result.error is not None, "Expected error message in failed result"
    
    return _assert

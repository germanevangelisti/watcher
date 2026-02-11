"""
Tests for Pipeline Service - End-to-end document processing
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
from pathlib import Path

# Import the service
import sys
project_root = Path(__file__).parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(project_root))

from app.services.pipeline_service import PipelineService, get_pipeline_service
from app.schemas.pipeline import PipelineOptions, PipelineStage
from app.db.models import Base


@pytest.fixture
def test_db():
    """Create an in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create tables
    Base.metadata.create_all(engine)
    
    yield session
    
    session.close()


@pytest.fixture
def test_file():
    """Create a temporary test file."""
    content = """
    DECRETO PROVINCIAL 456/2024
    
    ARTÍCULO 1: Se establece un subsidio para pequeñas empresas.
    El monto total asignado es de $10.000.000.
    
    ARTÍCULO 2: Las empresas deberán presentar la documentación antes del 31/12/2024.
    
    RESOLUCIÓN ADMINISTRATIVA
    
    Se aprueba la licitación para la construcción de una nueva escuela.
    Presupuesto estimado: $50.000.000.
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        Path(temp_path).unlink()
    except Exception:
        pass


def test_pipeline_service_initialization(test_db):
    """Test PipelineService can be initialized."""
    service = PipelineService(test_db)
    assert service is not None
    assert service.db == test_db


def test_get_pipeline_service_factory(test_db):
    """Test the get_pipeline_service factory function."""
    service = get_pipeline_service(test_db)
    
    assert service is not None
    assert isinstance(service, PipelineService)
    assert service.db == test_db


@pytest.mark.asyncio
async def test_pipeline_options_defaults():
    """Test PipelineOptions default values."""
    options = PipelineOptions()
    
    assert options.chunk_size == 1000
    assert options.chunk_overlap == 200
    assert options.skip_cleaning is False
    assert options.skip_enrichment is False
    assert options.use_triple_indexing is True


@pytest.mark.asyncio
async def test_pipeline_options_custom():
    """Test PipelineOptions with custom values."""
    options = PipelineOptions(
        chunk_size=500,
        chunk_overlap=100,
        skip_cleaning=True
    )
    
    assert options.chunk_size == 500
    assert options.chunk_overlap == 100
    assert options.skip_cleaning is True


@pytest.mark.asyncio
async def test_batch_processing_empty_list(test_db):
    """Test batch processing with empty file list."""
    service = PipelineService(test_db)
    
    results = await service.process_batch([])
    
    assert len(results) == 0


# Note: Full end-to-end pipeline tests would require:
# - Mock ExtractorRegistry
# - Mock embedding service
# - Mock all dependencies
# These would be integration tests rather than unit tests

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

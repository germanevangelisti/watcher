"""
Tests for FTS (Full-Text Search) Service using SQLite FTS5
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Import the service
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(project_root))

from app.services.fts_service import FTSService, get_fts_service
from app.db.models import Base, ChunkRecord


@pytest.fixture
def test_db():
    """Create an in-memory test database with FTS5."""
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create tables
    Base.metadata.create_all(engine)
    
    # Create FTS5 table and triggers manually (since Alembic won't run)
    session.execute(text("""
        CREATE VIRTUAL TABLE chunk_records_fts USING fts5(
            text,
            document_id UNINDEXED,
            chunk_index UNINDEXED,
            section_type UNINDEXED,
            content=chunk_records,
            content_rowid=id
        )
    """))
    
    session.execute(text("""
        CREATE TRIGGER chunk_records_fts_insert AFTER INSERT ON chunk_records
        BEGIN
            INSERT INTO chunk_records_fts(rowid, text, document_id, chunk_index, section_type)
            VALUES (new.id, new.text, new.document_id, new.chunk_index, new.section_type);
        END
    """))
    
    session.execute(text("""
        CREATE TRIGGER chunk_records_fts_delete AFTER DELETE ON chunk_records
        BEGIN
            INSERT INTO chunk_records_fts(chunk_records_fts, rowid, text, document_id, chunk_index, section_type)
            VALUES ('delete', old.id, old.text, old.document_id, old.chunk_index, old.section_type);
        END
    """))
    
    session.execute(text("""
        CREATE TRIGGER chunk_records_fts_update AFTER UPDATE ON chunk_records
        BEGIN
            INSERT INTO chunk_records_fts(chunk_records_fts, rowid, text, document_id, chunk_index, section_type)
            VALUES ('delete', old.id, old.text, old.document_id, old.chunk_index, old.section_type);
            INSERT INTO chunk_records_fts(rowid, text, document_id, chunk_index, section_type)
            VALUES (new.id, new.text, new.document_id, new.chunk_index, new.section_type);
        END
    """))
    
    session.commit()
    
    yield session
    
    session.close()


@pytest.fixture
def sample_chunks(test_db):
    """Create sample chunks for testing."""
    chunks = [
        ChunkRecord(
            document_id="doc1",
            chunk_index=0,
            chunk_hash="hash1",
            text="El Ministerio de Salud emitió un decreto sobre vacunación obligatoria.",
            num_chars=70,
            section_type="decreto",
            language="es",
            has_amounts=False,
            created_at=datetime.utcnow()
        ),
        ChunkRecord(
            document_id="doc1",
            chunk_index=1,
            chunk_hash="hash2",
            text="La licitación pública para la construcción del hospital tiene un presupuesto de $50 millones.",
            num_chars=95,
            section_type="licitacion",
            language="es",
            has_amounts=True,
            created_at=datetime.utcnow()
        ),
        ChunkRecord(
            document_id="doc2",
            chunk_index=0,
            chunk_hash="hash3",
            text="Resolución administrativa sobre contrataciones directas en el sector público.",
            num_chars=80,
            section_type="resolucion",
            language="es",
            has_amounts=False,
            created_at=datetime.utcnow()
        ),
        ChunkRecord(
            document_id="doc2",
            chunk_index=1,
            chunk_hash="hash4",
            text="Nuevo decreto establece normas para la importación de medicamentos.",
            num_chars=70,
            section_type="decreto",
            language="es",
            has_amounts=False,
            created_at=datetime.utcnow()
        ),
        ChunkRecord(
            document_id="doc3",
            chunk_index=0,
            chunk_hash="hash5",
            text="Subsidio estatal para pequeñas empresas afectadas por la pandemia.",
            num_chars=65,
            section_type="subsidio",
            language="es",
            has_amounts=False,
            created_at=datetime.utcnow()
        ),
    ]
    
    for chunk in chunks:
        test_db.add(chunk)
    
    test_db.commit()
    
    return chunks


def test_fts_service_initialization(test_db):
    """Test FTS service can be initialized."""
    service = FTSService(test_db)
    assert service is not None
    assert service.db == test_db


def test_search_bm25_basic(test_db, sample_chunks):
    """Test basic BM25 search functionality."""
    service = FTSService(test_db)
    
    # Search for "decreto"
    results = service.search_bm25("decreto", top_k=10)
    
    assert len(results) == 2  # Should find 2 chunks with "decreto"
    assert all(r.bm25_score > 0 for r in results)
    assert all("decreto" in r.text.lower() for r in results)


def test_search_bm25_spanish_query(test_db, sample_chunks):
    """Test BM25 search with Spanish query."""
    service = FTSService(test_db)
    
    # Search for "vacunación obligatoria"
    results = service.search_bm25("vacunación obligatoria", top_k=5)
    
    assert len(results) >= 1
    assert "vacunación" in results[0].text.lower()


def test_search_bm25_with_filters(test_db, sample_chunks):
    """Test BM25 search with metadata filters."""
    service = FTSService(test_db)
    
    # Search for "decreto" but only in doc2
    results = service.search_bm25(
        "decreto",
        top_k=10,
        filters={"document_id": "doc2"}
    )
    
    assert len(results) == 1
    assert results[0].document_id == "doc2"


def test_search_bm25_section_filter(test_db, sample_chunks):
    """Test BM25 search with section_type filter."""
    service = FTSService(test_db)
    
    # Search in licitaciones only
    results = service.search_bm25(
        "hospital",
        top_k=10,
        filters={"section_type": "licitacion"}
    )
    
    assert len(results) == 1
    assert results[0].section_type == "licitacion"


def test_search_bm25_empty_query(test_db, sample_chunks):
    """Test BM25 search with empty query returns no results."""
    service = FTSService(test_db)
    
    results = service.search_bm25("", top_k=10)
    assert len(results) == 0
    
    results = service.search_bm25("   ", top_k=10)
    assert len(results) == 0


def test_search_bm25_no_results(test_db, sample_chunks):
    """Test BM25 search with query that has no matches."""
    service = FTSService(test_db)
    
    results = service.search_bm25("xyzabc123nonexistent", top_k=10)
    assert len(results) == 0


def test_search_bm25_top_k_limit(test_db, sample_chunks):
    """Test BM25 search respects top_k limit."""
    service = FTSService(test_db)
    
    # Search for common word, limit to 2
    results = service.search_bm25("decreto", top_k=1)
    assert len(results) == 1


def test_fts_trigger_insert(test_db):
    """Test that INSERT trigger keeps FTS5 in sync."""
    service = FTSService(test_db)
    
    # Add a new chunk
    new_chunk = ChunkRecord(
        document_id="doc_test",
        chunk_index=0,
        chunk_hash="hash_test",
        text="Este es un texto de prueba para el trigger de inserción.",
        num_chars=60,
        section_type="general",
        created_at=datetime.utcnow()
    )
    test_db.add(new_chunk)
    test_db.commit()
    
    # Search should find it immediately
    results = service.search_bm25("trigger inserción", top_k=5)
    assert len(results) >= 1
    assert any("trigger" in r.text.lower() for r in results)


def test_fts_trigger_delete(test_db, sample_chunks):
    """Test that DELETE trigger keeps FTS5 in sync."""
    service = FTSService(test_db)
    
    # Search before delete
    results_before = service.search_bm25("vacunación", top_k=5)
    assert len(results_before) >= 1
    
    # Delete the chunk
    chunk_to_delete = test_db.query(ChunkRecord).filter(
        ChunkRecord.text.contains("vacunación")
    ).first()
    test_db.delete(chunk_to_delete)
    test_db.commit()
    
    # Search after delete
    results_after = service.search_bm25("vacunación", top_k=5)
    assert len(results_after) == len(results_before) - 1


def test_fts_trigger_update(test_db, sample_chunks):
    """Test that UPDATE trigger keeps FTS5 in sync."""
    service = FTSService(test_db)
    
    # Find and update a chunk
    chunk = test_db.query(ChunkRecord).filter(
        ChunkRecord.text.contains("Ministerio")
    ).first()
    
    _old_text = chunk.text
    chunk.text = "Texto completamente actualizado con palabras únicas xyz123"
    test_db.commit()
    
    # Old text should not be found
    results_old = service.search_bm25("Ministerio", top_k=5)
    assert not any(r.chunk_id == chunk.id for r in results_old)
    
    # New text should be found
    results_new = service.search_bm25("xyz123", top_k=5)
    assert len(results_new) >= 1
    assert any(r.chunk_id == chunk.id for r in results_new)


def test_get_index_stats(test_db, sample_chunks):
    """Test getting FTS5 index statistics."""
    service = FTSService(test_db)
    
    stats = service.get_index_stats()
    
    assert stats["total_chunks"] == 5
    assert stats["source_chunks"] == 5
    assert stats["in_sync"] is True
    assert "by_section" in stats
    assert len(stats["by_section"]) > 0


def test_rebuild_index(test_db, sample_chunks):
    """Test rebuilding FTS5 index."""
    service = FTSService(test_db)
    
    result = service.rebuild_index()
    
    assert result["success"] is True
    assert "stats" in result
    assert result["stats"]["total_chunks"] == 5


def test_optimize_index(test_db, sample_chunks):
    """Test optimizing FTS5 index."""
    service = FTSService(test_db)
    
    result = service.optimize_index()
    
    assert result["success"] is True
    assert "message" in result


def test_test_query(test_db, sample_chunks):
    """Test the test_query method for validating queries."""
    service = FTSService(test_db)
    
    # Valid query
    result = service.test_query("decreto")
    assert result["valid"] is True
    
    # Another valid query
    result = service.test_query("hospital licitación")
    assert result["valid"] is True


def test_get_fts_service_factory(test_db):
    """Test the get_fts_service factory function."""
    service = get_fts_service(test_db)
    
    assert service is not None
    assert isinstance(service, FTSService)
    assert service.db == test_db


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

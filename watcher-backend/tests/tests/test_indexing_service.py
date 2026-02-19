"""
Tests for IndexingService - Triple indexing orchestration
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import the service
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(project_root))

from app.services.indexing_service import IndexingService, get_indexing_service
from app.services.embedding_service import EMBEDDING_MODEL, EMBEDDING_DIM
from app.services.chunking_service import ChunkResult
from app.db.models import Base, ChunkRecord


@pytest.fixture
def test_db():
    """Create an in-memory test database with all tables."""
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create tables
    Base.metadata.create_all(engine)
    
    # Create FTS5 table and triggers
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
    
    session.commit()
    
    yield session
    
    session.close()


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service for testing."""
    
    class MockEmbeddingService:
        def __init__(self):
            self.collection = MockCollection()
            self.google_model = EMBEDDING_MODEL
        
        async def generate_embedding(self, text):
            # Return a fake embedding
            return [0.1] * EMBEDDING_DIM
    
    class MockCollection:
        def __init__(self):
            self.data = {}
        
        def add(self, documents, ids, metadatas, embeddings):
            for i, doc_id in enumerate(ids):
                self.data[doc_id] = {
                    "document": documents[i],
                    "metadata": metadatas[i],
                    "embedding": embeddings[i]
                }
        
        def get(self, where=None):
            if where and "document_id" in where:
                doc_id = where["document_id"]
                matching = [k for k in self.data.keys() if self.data[k]["metadata"].get("document_id") == doc_id]
                return {"ids": matching}
            return {"ids": list(self.data.keys())}
        
        def delete(self, ids):
            for doc_id in ids:
                if doc_id in self.data:
                    del self.data[doc_id]
    
    return MockEmbeddingService()


def test_indexing_service_initialization(test_db, mock_embedding_service):
    """Test IndexingService can be initialized."""
    service = IndexingService(test_db, mock_embedding_service)
    assert service is not None
    assert service.db == test_db
    assert service.embedding_service == mock_embedding_service


@pytest.mark.asyncio
async def test_index_single_chunk(test_db, mock_embedding_service):
    """Test indexing a single chunk in all three stores."""
    service = IndexingService(test_db, mock_embedding_service)
    
    chunk = ChunkResult(
        text="Este es un texto de prueba para el chunk único.",
        chunk_index=0,
        start_char=0,
        end_char=50,
        num_chars=50
    )
    
    success, chunk_record, error = await service.index_chunk(
        document_id="test_doc_1",
        chunk_result=chunk,
        metadata={"test": "metadata"}
    )
    
    assert success is True
    assert chunk_record is not None
    assert error is None
    assert chunk_record.document_id == "test_doc_1"
    assert chunk_record.chunk_index == 0
    assert chunk_record.indexed_at is not None
    
    # Verify in SQLite
    db_chunk = test_db.query(ChunkRecord).filter(ChunkRecord.document_id == "test_doc_1").first()
    assert db_chunk is not None
    assert db_chunk.text == chunk.text
    
    # Verify in FTS5
    fts_result = test_db.execute(text("SELECT COUNT(*) FROM chunk_records_fts WHERE document_id = 'test_doc_1'"))
    fts_count = fts_result.scalar()
    assert fts_count == 1
    
    # Verify in ChromaDB (mock)
    chromadb_ids = mock_embedding_service.collection.get(where={"document_id": "test_doc_1"})
    assert len(chromadb_ids["ids"]) == 1


@pytest.mark.asyncio
async def test_index_multiple_chunks(test_db, mock_embedding_service):
    """Test indexing multiple chunks of a document."""
    service = IndexingService(test_db, mock_embedding_service)
    
    chunks = [
        ChunkResult(text=f"Chunk {i} con texto de prueba.", chunk_index=i, start_char=i*50, end_char=(i+1)*50, num_chars=50)
        for i in range(3)
    ]
    
    result = await service.index_document(
        document_id="test_doc_multi",
        chunks=chunks,
        metadata={"source": "test"}
    )
    
    assert result.success is True
    assert result.chunks_indexed == 3
    assert result.error is None
    
    # Verify all in SQLite
    db_chunks = test_db.query(ChunkRecord).filter(ChunkRecord.document_id == "test_doc_multi").all()
    assert len(db_chunks) == 3
    
    # Verify all in FTS5
    fts_result = test_db.execute(text("SELECT COUNT(*) FROM chunk_records_fts WHERE document_id = 'test_doc_multi'"))
    fts_count = fts_result.scalar()
    assert fts_count == 3
    
    # Verify all in ChromaDB
    chromadb_ids = mock_embedding_service.collection.get(where={"document_id": "test_doc_multi"})
    assert len(chromadb_ids["ids"]) == 3


@pytest.mark.asyncio
async def test_rollback_on_failure(test_db, mock_embedding_service):
    """Test that rollback happens when indexing fails."""
    
    # Create a failing embedding service
    class FailingEmbeddingService:
        def __init__(self):
            self.collection = mock_embedding_service.collection
            self.google_model = EMBEDDING_MODEL
        
        async def generate_embedding(self, text):
            # Fail on second chunk
            if "Chunk 1" in text:
                raise Exception("Simulated embedding failure")
            return [0.1] * EMBEDDING_DIM
    
    failing_service = FailingEmbeddingService()
    service = IndexingService(test_db, failing_service)
    
    chunks = [
        ChunkResult(text=f"Chunk {i} texto.", chunk_index=i, start_char=0, end_char=20, num_chars=20)
        for i in range(3)
    ]
    
    result = await service.index_document(
        document_id="test_doc_fail",
        chunks=chunks
    )
    
    assert result.success is False
    assert result.error is not None
    assert result.rollback_applied is True
    
    # Verify nothing in SQLite (rollback successful)
    db_chunks = test_db.query(ChunkRecord).filter(ChunkRecord.document_id == "test_doc_fail").all()
    assert len(db_chunks) == 0
    
    # Verify nothing in FTS5
    fts_result = test_db.execute(text("SELECT COUNT(*) FROM chunk_records_fts WHERE document_id = 'test_doc_fail'"))
    fts_count = fts_result.scalar()
    assert fts_count == 0


@pytest.mark.asyncio
async def test_verify_triple_index(test_db, mock_embedding_service):
    """Test verification of triple index consistency."""
    service = IndexingService(test_db, mock_embedding_service)
    
    # Index a document
    chunks = [
        ChunkResult(text=f"Chunk {i}", chunk_index=i, start_char=0, end_char=10, num_chars=10)
        for i in range(2)
    ]
    
    await service.index_document(
        document_id="test_doc_verify",
        chunks=chunks
    )
    
    # Verify it's consistent
    verification = await service.verify_triple_index("test_doc_verify")
    
    assert verification["consistent"] is True
    assert verification["sql_chunks"] == 2
    assert verification["fts_chunks"] == 2
    assert verification["chromadb_chunks"] == 2


@pytest.mark.asyncio
async def test_verify_triple_index_inconsistent(test_db, mock_embedding_service):
    """Test verification detects inconsistencies."""
    service = IndexingService(test_db, mock_embedding_service)
    
    # Index a document
    chunks = [
        ChunkResult(text=f"Chunk {i}", chunk_index=i, start_char=0, end_char=10, num_chars=10)
        for i in range(2)
    ]
    
    await service.index_document(
        document_id="test_doc_inconsistent",
        chunks=chunks
    )
    
    # Manually delete from ChromaDB to create inconsistency
    mock_embedding_service.collection.delete(["test_doc_inconsistent_chunk_0"])
    
    # Verify detects inconsistency
    verification = await service.verify_triple_index("test_doc_inconsistent")
    
    assert verification["consistent"] is False
    assert verification["sql_chunks"] == 2
    assert verification["chromadb_chunks"] == 1  # One deleted


@pytest.mark.asyncio
async def test_repair_index(test_db, mock_embedding_service):
    """Test repairing inconsistent indices."""
    service = IndexingService(test_db, mock_embedding_service)
    
    # Index a document
    chunks = [
        ChunkResult(text=f"Chunk {i}", chunk_index=i, start_char=0, end_char=10, num_chars=10)
        for i in range(3)
    ]
    
    await service.index_document(
        document_id="test_doc_repair",
        chunks=chunks
    )
    
    # Create inconsistency by deleting from ChromaDB
    mock_embedding_service.collection.data.clear()
    
    # Verify inconsistency
    verification_before = await service.verify_triple_index("test_doc_repair")
    assert verification_before["consistent"] is False
    
    # Repair
    repair_result = await service.repair_index("test_doc_repair")
    
    assert repair_result["success"] is True
    assert repair_result["chunks_repaired"] == 3
    
    # Verify consistency after repair
    verification_after = await service.verify_triple_index("test_doc_repair")
    assert verification_after["consistent"] is True


def test_get_indexing_service_factory(test_db):
    """Test the get_indexing_service factory function."""
    service = get_indexing_service(test_db)
    
    assert service is not None
    assert isinstance(service, IndexingService)
    assert service.db == test_db


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])

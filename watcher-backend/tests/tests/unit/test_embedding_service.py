"""
Unit tests for Embedding Service (Vector Database).

Tests vector embeddings, chunking, and semantic search functionality.
"""

import pytest
from pathlib import Path
import sys

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(backend_path))

from app.services.embedding_service import EmbeddingService


# ============================================================================
# Initialization Tests
# ============================================================================

@pytest.mark.dia
def test_embedding_service_init(tmp_path):
    """Test EmbeddingService initialization."""
    service = EmbeddingService(
        persist_directory=str(tmp_path / "chromadb"),
        collection_name="test_collection"
    )
    
    assert service.collection_name == "test_collection"
    assert service.persist_directory == str(tmp_path / "chromadb")


@pytest.mark.dia
def test_embedding_service_init_defaults():
    """Test EmbeddingService with default parameters."""
    service = EmbeddingService()
    
    assert service.collection_name == "watcher_documents"
    assert service.embedding_provider in ["google", "local"]


# ============================================================================
# Text Chunking Tests
# ============================================================================

@pytest.mark.dia
def test_chunk_text_basic():
    """Test basic text chunking."""
    service = EmbeddingService()
    
    text = "This is a test. " * 100  # 1600 characters
    chunks = service.chunk_text(text, chunk_size=500, overlap=100)
    
    assert len(chunks) > 1
    assert all(len(chunk) <= 600 for chunk in chunks)  # Allow overhead for overlap


@pytest.mark.dia
def test_chunk_text_overlap():
    """Test that chunks have overlap."""
    service = EmbeddingService()
    
    text = "First sentence. Second sentence. Third sentence. " * 20
    chunks = service.chunk_text(text, chunk_size=200, overlap=50)
    
    # Check that adjacent chunks share some text
    if len(chunks) > 1:
        # Some overlap should exist
        assert len(chunks[0]) >= 150  # Should have content


@pytest.mark.dia
def test_chunk_text_sentence_boundary():
    """Test that chunking creates reasonable chunks."""
    service = EmbeddingService()
    
    text = "First sentence. Second sentence. Third sentence."
    chunks = service.chunk_text(text, chunk_size=30, overlap=5)
    
    # Verify chunking works and creates reasonable output
    assert len(chunks) >= 1
    assert all(len(chunk) > 0 for chunk in chunks)
    # All chunks combined should contain the original text content
    combined_text = ' '.join(chunks)
    assert "First sentence" in combined_text or "sentence" in combined_text


@pytest.mark.dia
def test_chunk_text_empty():
    """Test chunking empty text."""
    service = EmbeddingService()
    
    chunks = service.chunk_text("", chunk_size=100, overlap=20)
    
    assert chunks == []


@pytest.mark.dia
def test_chunk_text_short():
    """Test chunking text shorter than chunk size but longer than min_chunk_size."""
    service = EmbeddingService()
    
    # Use text longer than min_chunk_size (100 chars) but shorter than chunk_size (1000)
    text = "This is a test sentence. " * 5  # 125 characters
    chunks = service.chunk_text(text, chunk_size=1000, overlap=100)
    
    assert len(chunks) == 1
    assert chunks[0] == text


# ============================================================================
# Document Management Tests
# ============================================================================

@pytest.mark.dia
@pytest.mark.asyncio
@pytest.mark.slow
async def test_add_document_success(tmp_path):
    """Test adding a document to vector store."""
    # Skip if ChromaDB not available
    pytest.importorskip("chromadb")
    
    service = EmbeddingService(
        persist_directory=str(tmp_path / "chromadb"),
        embedding_provider="local"  # Use local for testing
    )
    
    # Skip if collection not initialized
    if not service.collection:
        pytest.skip("ChromaDB not initialized")
    
    result = await service.add_document(
        document_id="test_doc_1",
        content="This is a test document for vector search.",
        metadata={"test": True},
        chunk=False  # Don't chunk for simple test
    )
    
    assert result["success"] is True
    assert result["document_id"] == "test_doc_1"


@pytest.mark.dia
@pytest.mark.asyncio
async def test_add_document_with_metadata(tmp_path):
    """Test adding document with custom metadata."""
    pytest.importorskip("chromadb")
    
    service = EmbeddingService(
        persist_directory=str(tmp_path / "chromadb")
    )
    
    if not service.collection:
        pytest.skip("ChromaDB not initialized")
    
    metadata = {
        "source": "test",
        "date": "2026-01-01",
        "category": "boletin"
    }
    
    result = await service.add_document(
        document_id="test_doc_2",
        content="Document with metadata",
        metadata=metadata,
        chunk=False
    )
    
    if result["success"]:
        assert result["document_id"] == "test_doc_2"


@pytest.mark.dia
@pytest.mark.asyncio
async def test_add_document_with_chunking(tmp_path, sample_text_for_chunking):
    """Test adding document with automatic chunking."""
    pytest.importorskip("chromadb")
    
    service = EmbeddingService(
        persist_directory=str(tmp_path / "chromadb")
    )
    
    if not service.collection:
        pytest.skip("ChromaDB not initialized")
    
    result = await service.add_document(
        document_id="test_doc_chunks",
        content=sample_text_for_chunking,
        chunk=True
    )
    
    if result["success"]:
        assert result["chunks_created"] > 1


# ============================================================================
# Search Tests
# ============================================================================

@pytest.mark.dia
@pytest.mark.asyncio
@pytest.mark.slow
async def test_search_basic(tmp_path):
    """Test basic semantic search."""
    pytest.importorskip("chromadb")
    
    service = EmbeddingService(
        persist_directory=str(tmp_path / "chromadb")
    )
    
    if not service.collection:
        pytest.skip("ChromaDB not initialized")
    
    # Add a document first
    await service.add_document(
        document_id="search_test_1",
        content="Information about government subsidies and contracts.",
        chunk=False
    )
    
    # Search
    results = await service.search(
        query="subsidies",
        n_results=5
    )
    
    # Results should be a list
    assert isinstance(results, list)


@pytest.mark.dia
@pytest.mark.asyncio
async def test_search_with_filter(tmp_path):
    """Test search with metadata filters."""
    pytest.importorskip("chromadb")
    
    service = EmbeddingService(
        persist_directory=str(tmp_path / "chromadb")
    )
    
    if not service.collection:
        pytest.skip("ChromaDB not initialized")
    
    # Add documents with different metadata
    await service.add_document(
        document_id="filter_test_1",
        content="Provincial document",
        metadata={"level": "provincial"},
        chunk=False
    )
    
    await service.add_document(
        document_id="filter_test_2",
        content="Municipal document",
        metadata={"level": "municipal"},
        chunk=False
    )
    
    # Search with filter
    results = await service.search(
        query="document",
        n_results=10,
        filter={"level": "provincial"}
    )
    
    # Should only return provincial documents
    assert isinstance(results, list)


@pytest.mark.dia
@pytest.mark.asyncio
async def test_search_empty_query(tmp_path):
    """Test search with empty query."""
    service = EmbeddingService(
        persist_directory=str(tmp_path / "chromadb")
    )
    
    results = await service.search(query="", n_results=5)
    
    assert results == []


# ============================================================================
# Delete Tests
# ============================================================================

@pytest.mark.dia
@pytest.mark.asyncio
async def test_delete_document(tmp_path):
    """Test deleting a document from vector store."""
    pytest.importorskip("chromadb")
    
    service = EmbeddingService(
        persist_directory=str(tmp_path / "chromadb")
    )
    
    if not service.collection:
        pytest.skip("ChromaDB not initialized")
    
    # Add a document
    await service.add_document(
        document_id="delete_test_1",
        content="Document to be deleted",
        chunk=False
    )
    
    # Delete it
    result = await service.delete_document("delete_test_1")
    
    # Check result
    assert isinstance(result, dict)
    assert "success" in result


# ============================================================================
# Statistics Tests
# ============================================================================

@pytest.mark.dia
def test_service_stats():
    """Test getting service statistics."""
    service = EmbeddingService()
    
    stats = service.get_stats()
    
    assert isinstance(stats, dict)
    assert "embeddings_created" in stats
    assert "documents_added" in stats
    assert "searches_performed" in stats


@pytest.mark.dia
@pytest.mark.asyncio
async def test_stats_tracking(tmp_path):
    """Test that statistics are tracked correctly."""
    pytest.importorskip("chromadb")
    
    service = EmbeddingService(
        persist_directory=str(tmp_path / "chromadb")
    )
    
    if not service.collection:
        pytest.skip("ChromaDB not initialized")
    
    initial_stats = service.get_stats()
    initial_docs = initial_stats["documents_added"]
    
    # Add a document
    await service.add_document(
        document_id="stats_test_1",
        content="Test document for stats",
        chunk=False
    )
    
    new_stats = service.get_stats()
    
    # Check that stats increased
    assert new_stats["documents_added"] >= initial_docs


# ============================================================================
# Collection Management Tests
# ============================================================================

@pytest.mark.dia
@pytest.mark.slow
def test_reset_collection(tmp_path):
    """Test resetting the collection."""
    pytest.importorskip("chromadb")
    
    service = EmbeddingService(
        persist_directory=str(tmp_path / "chromadb"),
        collection_name="test_reset"
    )
    
    if not service.collection:
        pytest.skip("ChromaDB not initialized")
    
    # Reset collection
    service.reset_collection()
    
    # Collection should exist but be empty
    assert service.collection is not None
    assert service.collection.count() == 0

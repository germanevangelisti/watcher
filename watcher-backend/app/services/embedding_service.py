"""
Embedding Service - Vector embeddings for semantic search

This service handles:
- Text cleaning and normalization
- Text chunking and preprocessing
- Generating embeddings using Google text-embedding-004
- Integration with ChromaDB for vector storage
- Semantic search capabilities
"""

import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
import os

logger = logging.getLogger(__name__)

# Import TextCleaner
try:
    from .text_cleaner import TextCleaner
    TEXT_CLEANER_AVAILABLE = True
except ImportError:
    logger.warning("TextCleaner not available")
    TEXT_CLEANER_AVAILABLE = False

# Import ChunkingService
try:
    from .chunking_service import ChunkingService, ChunkingConfig
    CHUNKING_SERVICE_AVAILABLE = True
except ImportError:
    logger.warning("ChunkingService not available")
    CHUNKING_SERVICE_AVAILABLE = False

# Try to import ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    logger.warning("ChromaDB not installed. Install with: pip install chromadb")
    CHROMADB_AVAILABLE = False

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    logger.warning("Google Generative AI not installed. Install with: pip install google-generativeai")
    GOOGLE_AI_AVAILABLE = False


EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIM = 3072


class GoogleEmbeddingFunction:
    """ChromaDB-compatible embedding function using Google gemini-embedding-001."""

    def __init__(self, api_key: str, model: str = EMBEDDING_MODEL):
        # genai.configure() is called once at app startup in main.py
        self.model = model

    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        embeddings = []
        batch_size = 100

        for i in range(0, len(input), batch_size):
            batch = input[i:i + batch_size]
            for text in batch:
                try:
                    result = genai.embed_content(
                        model=self.model,
                        content=text,
                        task_type="retrieval_document"
                    )
                    embeddings.append(result['embedding'])
                except Exception as e:
                    logger.error(f"Error generating embedding: {e}")
                    embeddings.append([0.0] * EMBEDDING_DIM)

        return embeddings


class EmbeddingService:
    """
    Service for generating and managing document embeddings.
    
    Supports multiple embedding providers:
    - Google AI (text-embedding-004) - default
    - Local models (sentence-transformers)
    """
    
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "watcher_documents",
        embedding_provider: str = "google",  # "google" or "local"
        google_api_key: Optional[str] = None,
        enable_text_cleaning: bool = True
    ):
        """
        Initialize embedding service.
        
        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of the collection
            embedding_provider: "google" or "local"
            google_api_key: Optional Google API key
            enable_text_cleaning: Whether to enable text cleaning (default: True)
        """
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider
        self.enable_text_cleaning = enable_text_cleaning
        
        # Initialize TextCleaner
        self.text_cleaner = None
        if enable_text_cleaning and TEXT_CLEANER_AVAILABLE:
            self.text_cleaner = TextCleaner()
            logger.info("Text cleaning enabled")
        elif enable_text_cleaning:
            logger.warning("Text cleaning requested but TextCleaner not available")
        
        # Initialize ChunkingService
        if not CHUNKING_SERVICE_AVAILABLE:
            raise ImportError("ChunkingService is required. Ensure chunking_service.py is available.")
        
        self.chunking_service = ChunkingService()
        logger.info("ChunkingService initialized")
        
        # Set up persist directory
        if persist_directory is None:
            persist_directory = str(Path.home() / ".watcher" / "chromadb")
        
        self.persist_directory = persist_directory
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding function
        self.embedding_fn = None
        self.google_model = EMBEDDING_MODEL

        if embedding_provider == "google":
            api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
            if api_key and GOOGLE_AI_AVAILABLE:
                self.embedding_fn = GoogleEmbeddingFunction(api_key, self.google_model)
                logger.info(f"Google AI embeddings enabled with model {self.google_model}")
            else:
                logger.warning("Google API key not found. Falling back to local embeddings.")
                self.embedding_provider = "local"

        # Initialize ChromaDB client
        self.client = None
        self.collection = None
        
        if CHROMADB_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                
                # Get or create collection WITH embedding function
                collection_kwargs = {
                    "name": collection_name,
                    "metadata": {
                        "description": f"Watcher Agent - Google {EMBEDDING_MODEL}",
                        "model": self.google_model,
                        "dimensions": EMBEDDING_DIM,
                    },
                }
                if self.embedding_fn:
                    collection_kwargs["embedding_function"] = self.embedding_fn

                self.collection = self.client.get_or_create_collection(**collection_kwargs)
                
                logger.info(f"ChromaDB initialized at {self.persist_directory}")
                logger.info(f"Collection '{collection_name}' ready with {self.collection.count()} documents")
            
            except Exception as e:
                logger.error(f"Error initializing ChromaDB: {e}")
                self.client = None
        else:
            logger.warning("ChromaDB not available. Vector search features disabled.")
        
        self.stats = {
            "embeddings_created": 0,
            "documents_added": 0,
            "searches_performed": 0,
            "errors": 0
        }
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[str]:
        """
        Split text into overlapping chunks using ChunkingService.
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        config = ChunkingConfig(
            chunk_size=chunk_size,
            chunk_overlap=overlap
        )
        chunk_results = self.chunking_service.chunk(text, config)
        return [cr.text for cr in chunk_results]
    
    async def generate_embedding(
        self,
        text: str
    ) -> Optional[List[float]]:
        """
        Generate embedding for a text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if failed
        """
        if not text or not text.strip():
            return None
        
        try:
            if self.embedding_provider == "google" and GOOGLE_AI_AVAILABLE:
                # Google's text-embedding-004 produces 768-dimensional vectors
                result = genai.embed_content(
                    model=self.google_model,
                    content=text,
                    task_type="retrieval_document"
                )
                embedding = result['embedding']
                self.stats["embeddings_created"] += 1
                return embedding
            
            else:
                # For local embeddings, we would use sentence-transformers
                # For now, return None to indicate not implemented
                logger.warning("Local embeddings not yet implemented")
                return None
        
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            self.stats["errors"] += 1
            return None
    
    async def add_document(
        self,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk: bool = True,
        db_session = None,
        persist_chunks: bool = True,
        use_triple_indexing: bool = True
    ) -> Dict[str, Any]:
        """
        Add a document to the vector store.
        
        Args:
            document_id: Unique document identifier
            content: Document content
            metadata: Optional metadata
            chunk: Whether to chunk the document
            db_session: Optional SQLAlchemy session for persisting ChunkRecords
            persist_chunks: Whether to persist chunks to database (requires db_session)
            use_triple_indexing: Use new IndexingService for atomic triple indexing (recommended)
            
        Returns:
            Result dict with success status
        """
        if not self.collection:
            return {
                "success": False,
                "error": "ChromaDB not initialized"
            }
        
        if not content:
            return {
                "success": False,
                "error": "No content provided"
            }
        
        # Use new triple indexing service if available and requested
        if use_triple_indexing and persist_chunks and db_session:
            try:
                from .indexing_service import get_indexing_service
                
                # Clean text before chunking
                cleaned_content = content
                if self.text_cleaner and self.enable_text_cleaning:
                    logger.info(f"Cleaning text for document {document_id}")
                    cleaned_content = self.text_cleaner.clean(content)
                    logger.info(f"Text cleaned: {len(content)} -> {len(cleaned_content)} chars")
                
                # Chunk the content
                chunk_results = []
                if chunk:
                    chunk_results = self.chunking_service.chunk(cleaned_content)
                else:
                    from .chunking_service import ChunkResult
                    chunk_results = [ChunkResult(
                        text=cleaned_content,
                        chunk_index=0,
                        start_char=0,
                        end_char=len(cleaned_content),
                        num_chars=len(cleaned_content)
                    )]
                
                # Use IndexingService for triple indexing
                indexing_service = get_indexing_service(db_session)
                boletin_id = metadata.get("boletin_id") if metadata else None
                
                result = await indexing_service.index_document(
                    document_id,
                    chunk_results,
                    metadata,
                    boletin_id
                )
                
                if result.success:
                    self.stats["documents_added"] += 1
                    self.stats["embeddings_created"] += result.chunks_indexed
                    logger.info(f"✓ Triple-indexed document {document_id} with {result.chunks_indexed} chunks")
                else:
                    logger.error(f"Error triple-indexing document {document_id}: {result.error}")
                
                return {
                    "success": result.success,
                    "document_id": document_id,
                    "chunks_created": result.chunks_indexed,
                    "error": result.error,
                    "triple_indexed": True
                }
            
            except Exception as e:
                logger.error(f"Error using triple indexing: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                    "triple_indexed": False
                }
        
        # Fallback: simple direct indexing without db persistence
        logger.info(f"Adding document {document_id} without triple indexing")
        
        try:
            # Clean text if enabled
            cleaned_content = content
            if self.text_cleaner and self.enable_text_cleaning:
                cleaned_content = self.text_cleaner.clean(content)
            
            # Generate chunks
            chunks_to_add = []
            if chunk:
                chunks_to_add = self.chunk_text(cleaned_content)
            else:
                chunks_to_add = [cleaned_content]
            
            if not chunks_to_add:
                return {
                    "success": False,
                    "error": "No chunks generated (text may be too short)"
                }
            
            # Add to ChromaDB
            chunk_ids = [f"{document_id}_{i}" for i in range(len(chunks_to_add))]
            chunk_metadatas = []
            for i in range(len(chunks_to_add)):
                chunk_meta = {
                    "document_id": document_id,
                    "chunk_index": i,
                    **(metadata or {})
                }
                chunk_metadatas.append(chunk_meta)
            
            self.collection.add(
                ids=chunk_ids,
                documents=chunks_to_add,
                metadatas=chunk_metadatas
            )
            
            self.stats["documents_added"] += 1
            self.stats["embeddings_created"] += len(chunks_to_add)
            
            logger.info(f"✓ Added document {document_id} with {len(chunks_to_add)} chunks (simple mode)")
            
            return {
                "success": True,
                "document_id": document_id,
                "chunks_created": len(chunks_to_add),
                "triple_indexed": False
            }
        
        except Exception as e:
            logger.error(f"Error adding document: {e}", exc_info=True)
            self.stats["errors"] += 1
            return {
                "success": False,
                "error": str(e),
                "triple_indexed": False
            }
    
    async def search(
        self,
        query: str,
        n_results: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search.
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter: Optional metadata filter
            
        Returns:
            List of matching documents with scores
        """
        if not self.collection:
            logger.warning("ChromaDB not initialized")
            return []
        
        if not query:
            return []
        
        try:
            # Perform search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter
            )
            
            self.stats["searches_performed"] += 1
            
            # Format results
            formatted_results = []
            
            if results and 'ids' in results and results['ids']:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        "id": results['ids'][0][i],
                        "document": results['documents'][0][i] if 'documents' in results else None,
                        "metadata": results['metadatas'][0][i] if 'metadatas' in results else None,
                        "distance": results['distances'][0][i] if 'distances' in results else None,
                    })
            
            logger.info(f"Search for '{query}' returned {len(formatted_results)} results")
            
            return formatted_results
        
        except Exception as e:
            logger.error(f"Error performing search: {e}", exc_info=True)
            self.stats["errors"] += 1
            return []
    
    async def delete_document(
        self,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Delete a document and all its chunks from vector store.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Result dict
        """
        if not self.collection:
            return {
                "success": False,
                "error": "ChromaDB not initialized"
            }
        
        try:
            # Find all chunks for this document
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if results and 'ids' in results and results['ids']:
                self.collection.delete(ids=results['ids'])
                
                logger.info(f"Deleted document {document_id} with {len(results['ids'])} chunks")
                
                return {
                    "success": True,
                    "document_id": document_id,
                    "chunks_deleted": len(results['ids'])
                }
            else:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found"
                }
        
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            self.stats["errors"] += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        stats = self.stats.copy()
        
        if self.collection:
            stats["total_documents"] = self.collection.count()
        
        return stats
    
    def reset_collection(self):
        """Reset the collection (delete all data)."""
        if self.client and self.collection:
            self.client.delete_collection(self.collection_name)
            collection_kwargs = {
                "name": self.collection_name,
                "metadata": {
                    "description": f"Watcher Agent - Google {EMBEDDING_MODEL}",
                    "model": self.google_model,
                    "dimensions": EMBEDDING_DIM,
                },
            }
            if self.embedding_fn:
                collection_kwargs["embedding_function"] = self.embedding_fn

            self.collection = self.client.create_collection(**collection_kwargs)
            logger.info(f"Collection '{self.collection_name}' reset")


# Global instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service instance."""
    global _embedding_service
    
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    
    return _embedding_service

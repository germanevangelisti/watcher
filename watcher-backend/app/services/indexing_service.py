"""
Indexing Service - Orchestrates triple indexing across ChromaDB, SQLite, and FTS5

This service ensures that every chunk is atomically indexed in three places:
1. ChromaDB (vector embeddings for semantic search)
2. SQLite chunk_records (relational metadata)
3. SQLite FTS5 (full-text search via automatic triggers)

Key responsibilities:
- Coordinate triple indexing with rollback on failure
- Verify index consistency across all three stores
- Repair inconsistencies when detected
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Import services
try:
    from .embedding_service import EmbeddingService, get_embedding_service, EMBEDDING_MODEL, EMBEDDING_DIM
    EMBEDDING_SERVICE_AVAILABLE = True
except ImportError:
    logger.warning("EmbeddingService not available")
    EMBEDDING_SERVICE_AVAILABLE = False

try:
    from .chunking_service import ChunkResult
    CHUNKING_SERVICE_AVAILABLE = True
except ImportError:
    logger.warning("ChunkingService not available")
    CHUNKING_SERVICE_AVAILABLE = False

try:
    from .chunk_enricher import get_chunk_enricher
    CHUNK_ENRICHER_AVAILABLE = True
except ImportError:
    logger.warning("ChunkEnricher not available")
    CHUNK_ENRICHER_AVAILABLE = False

try:
    from ..db.models import ChunkRecord
    CHUNK_RECORD_AVAILABLE = True
except ImportError:
    logger.warning("ChunkRecord model not available")
    CHUNK_RECORD_AVAILABLE = False


class IndexingResult:
    """Result from indexing operation."""
    
    def __init__(
        self,
        success: bool,
        chunks_indexed: int = 0,
        error: Optional[str] = None,
        rollback_applied: bool = False
    ):
        self.success = success
        self.chunks_indexed = chunks_indexed
        self.error = error
        self.rollback_applied = rollback_applied
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "chunks_indexed": self.chunks_indexed,
            "error": self.error,
            "rollback_applied": self.rollback_applied
        }


class IndexingService:
    """
    Service for orchestrating triple indexing across ChromaDB, SQLite, and FTS5.
    
    Ensures atomic indexing with rollback on failure.
    """
    
    def __init__(self, db_session: Session, embedding_service: Optional[EmbeddingService] = None):
        """
        Initialize indexing service.
        
        Args:
            db_session: SQLAlchemy session
            embedding_service: Optional EmbeddingService instance (will create if not provided)
        """
        self.db = db_session
        
        # Get or create embedding service
        if embedding_service is None and EMBEDDING_SERVICE_AVAILABLE:
            self.embedding_service = get_embedding_service()
        else:
            self.embedding_service = embedding_service
        
        # Get chunk enricher
        self.enricher = None
        if CHUNK_ENRICHER_AVAILABLE:
            self.enricher = get_chunk_enricher()
    
    async def index_chunk(
        self,
        document_id: str,
        chunk_result: 'ChunkResult',
        metadata: Optional[Dict[str, Any]] = None,
        boletin_id: Optional[int] = None
    ) -> Tuple[bool, Optional[ChunkRecord], Optional[str]]:
        """
        Index a single chunk in all three locations atomically.
        
        Process:
        1. Create ChunkRecord in SQLite (triggers FTS5 insert automatically)
        2. Generate embedding
        3. Insert in ChromaDB
        4. Update indexed_at timestamp
        
        Args:
            document_id: Unique document identifier
            chunk_result: ChunkResult with chunk data
            metadata: Optional metadata for the chunk
            boletin_id: Optional boletin ID for foreign key
        
        Returns:
            Tuple of (success, chunk_record, error_message)
        """
        if not CHUNK_RECORD_AVAILABLE:
            return False, None, "ChunkRecord model not available"
        
        chunk_record = None
        chromadb_id = None
        
        try:
            # Step 1: Enrich chunk metadata
            context = {
                "boletin_id": boletin_id,
                "start_char": chunk_result.start_char,
                "end_char": chunk_result.end_char,
            }
            
            enriched = {}
            if self.enricher:
                enriched = self.enricher.enrich(
                    chunk_result.text,
                    chunk_result.chunk_index,
                    document_id,
                    context
                )
            else:
                # Basic enrichment if enricher not available
                import hashlib
                enriched = {
                    "text": chunk_result.text,
                    "chunk_index": chunk_result.chunk_index,
                    "chunk_hash": hashlib.sha256(chunk_result.text.encode()).hexdigest(),
                    "num_chars": chunk_result.num_chars,
                    "start_char": chunk_result.start_char,
                    "end_char": chunk_result.end_char,
                    "boletin_id": boletin_id,
                }
            
            # Step 2: Create ChunkRecord in SQLite
            # This automatically triggers FTS5 insert via database trigger
            chunk_record = ChunkRecord(
                document_id=document_id,
                boletin_id=enriched.get("boletin_id"),
                chunk_index=enriched["chunk_index"],
                chunk_hash=enriched.get("chunk_hash"),
                text=enriched["text"],
                num_chars=enriched["num_chars"],
                start_char=enriched.get("start_char"),
                end_char=enriched.get("end_char"),
                section_type=enriched.get("section_type"),
                topic=enriched.get("topic"),
                language=enriched.get("language", "es"),
                has_tables=enriched.get("has_tables", False),
                has_amounts=enriched.get("has_amounts", False),
                entities_json=enriched.get("entities_json"),
                embedding_model=EMBEDDING_MODEL,
                embedding_dimensions=EMBEDDING_DIM,
            )
            
            self.db.add(chunk_record)
            self.db.flush()  # Get the ID without committing
            
            logger.debug(f"Created ChunkRecord {chunk_record.id} for {document_id} chunk {chunk_result.chunk_index}")
            
            # Step 3: Generate embedding
            if not self.embedding_service:
                raise Exception("EmbeddingService not available")
            
            embedding = await self.embedding_service.generate_embedding(chunk_result.text)
            if not embedding:
                raise Exception("Failed to generate embedding")
            
            # Step 4: Insert in ChromaDB
            chromadb_id = f"{document_id}_chunk_{chunk_result.chunk_index}"
            
            chunk_metadata = {
                "document_id": document_id,
                "chunk_index": chunk_result.chunk_index,
                "chunk_id": chunk_record.id,
                **(metadata or {})
            }
            
            self.embedding_service.collection.add(
                documents=[chunk_result.text],
                ids=[chromadb_id],
                metadatas=[chunk_metadata],
                embeddings=[embedding]
            )
            
            logger.debug(f"Added chunk to ChromaDB with ID {chromadb_id}")
            
            # Step 5: Update indexed_at timestamp
            chunk_record.indexed_at = datetime.utcnow()
            
            # Commit SQLite transaction
            self.db.commit()
            
            logger.info(f"✓ Triple-indexed chunk {chunk_result.chunk_index} of {document_id}")
            
            return True, chunk_record, None
        
        except Exception as e:
            logger.error(f"Error indexing chunk: {e}", exc_info=True)
            
            # Rollback SQLite
            self.db.rollback()
            
            # Rollback ChromaDB if it was added
            if chromadb_id and self.embedding_service and self.embedding_service.collection:
                try:
                    self.embedding_service.collection.delete(ids=[chromadb_id])
                    logger.info(f"Rolled back ChromaDB entry {chromadb_id}")
                except Exception as rollback_err:
                    logger.error(f"Error rolling back ChromaDB: {rollback_err}")
            
            return False, None, str(e)
    
    async def index_document(
        self,
        document_id: str,
        chunks: List['ChunkResult'],
        metadata: Optional[Dict[str, Any]] = None,
        boletin_id: Optional[int] = None
    ) -> IndexingResult:
        """
        Index all chunks of a document with rollback on failure.
        
        If any chunk fails, all previously indexed chunks are rolled back.
        
        Args:
            document_id: Unique document identifier
            chunks: List of ChunkResult objects
            metadata: Optional metadata to attach to chunks
            boletin_id: Optional boletin ID for foreign key
        
        Returns:
            IndexingResult with success status and statistics
        """
        indexed_chunks = []
        indexed_chromadb_ids = []
        
        try:
            for i, chunk in enumerate(chunks):
                success, chunk_record, error = await self.index_chunk(
                    document_id,
                    chunk,
                    metadata,
                    boletin_id
                )
                
                if not success:
                    raise Exception(f"Failed to index chunk {i}: {error}")
                
                indexed_chunks.append(chunk_record)
                indexed_chromadb_ids.append(f"{document_id}_chunk_{chunk.chunk_index}")
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Indexed {i + 1}/{len(chunks)} chunks for {document_id}")
            
            logger.info(f"✓ Successfully indexed {len(chunks)} chunks for document {document_id}")
            
            return IndexingResult(
                success=True,
                chunks_indexed=len(chunks)
            )
        
        except Exception as e:
            logger.error(f"Error during document indexing, rolling back: {e}", exc_info=True)
            
            # Rollback all indexed chunks
            rollback_count = 0
            
            # Rollback SQLite chunks
            for chunk_record in indexed_chunks:
                try:
                    self.db.delete(chunk_record)
                    rollback_count += 1
                except Exception as rollback_err:
                    logger.error(f"Error rolling back ChunkRecord {chunk_record.id}: {rollback_err}")
            
            try:
                self.db.commit()
            except Exception as commit_err:
                logger.error(f"Error committing rollback: {commit_err}")
                self.db.rollback()
            
            # Rollback ChromaDB entries
            if indexed_chromadb_ids and self.embedding_service and self.embedding_service.collection:
                try:
                    self.embedding_service.collection.delete(ids=indexed_chromadb_ids)
                    logger.info(f"Rolled back {len(indexed_chromadb_ids)} ChromaDB entries")
                except Exception as rollback_err:
                    logger.error(f"Error rolling back ChromaDB: {rollback_err}")
            
            return IndexingResult(
                success=False,
                chunks_indexed=0,
                error=str(e),
                rollback_applied=True
            )
    
    async def verify_triple_index(self, document_id: str) -> Dict[str, Any]:
        """
        Verify that a document is consistently indexed in all three stores.
        
        Checks:
        1. ChunkRecords exist in SQLite
        2. Corresponding entries exist in FTS5
        3. Corresponding entries exist in ChromaDB
        
        Args:
            document_id: Document to verify
        
        Returns:
            Dict with verification results
        """
        try:
            # 1. Get chunks from SQLite
            sql_chunks = self.db.query(ChunkRecord).filter(
                ChunkRecord.document_id == document_id
            ).all()
            
            sql_count = len(sql_chunks)
            
            # 2. Count in FTS5
            fts_sql = text("""
                SELECT COUNT(*) 
                FROM chunk_records_fts AS fts
                JOIN chunk_records AS c ON c.id = fts.rowid
                WHERE c.document_id = :document_id
            """)
            result = self.db.execute(fts_sql, {"document_id": document_id})
            fts_count = result.scalar()
            
            # 3. Count in ChromaDB
            chromadb_count = 0
            if self.embedding_service and self.embedding_service.collection:
                results = self.embedding_service.collection.get(
                    where={"document_id": document_id}
                )
                chromadb_count = len(results['ids']) if results and 'ids' in results else 0
            
            # Check consistency
            is_consistent = (sql_count == fts_count == chromadb_count)
            
            return {
                "document_id": document_id,
                "consistent": is_consistent,
                "sql_chunks": sql_count,
                "fts_chunks": fts_count,
                "chromadb_chunks": chromadb_count,
                "message": "✓ All indices in sync" if is_consistent else "✗ Indices out of sync"
            }
        
        except Exception as e:
            logger.error(f"Error verifying triple index: {e}", exc_info=True)
            return {
                "document_id": document_id,
                "consistent": False,
                "error": str(e)
            }
    
    async def repair_index(self, document_id: str) -> Dict[str, Any]:
        """
        Attempt to repair inconsistencies in the triple index for a document.
        
        Strategy:
        1. Use SQLite ChunkRecords as source of truth
        2. Rebuild FTS5 entries for this document
        3. Rebuild ChromaDB entries for this document
        
        Args:
            document_id: Document to repair
        
        Returns:
            Dict with repair results
        """
        try:
            # Get chunks from SQLite (source of truth)
            sql_chunks = self.db.query(ChunkRecord).filter(
                ChunkRecord.document_id == document_id
            ).order_by(ChunkRecord.chunk_index).all()
            
            if not sql_chunks:
                return {
                    "success": False,
                    "error": f"No chunks found for document {document_id} in SQLite"
                }
            
            logger.info(f"Repairing index for {document_id} ({len(sql_chunks)} chunks)")
            
            # Clear existing ChromaDB entries
            if self.embedding_service and self.embedding_service.collection:
                try:
                    existing = self.embedding_service.collection.get(
                        where={"document_id": document_id}
                    )
                    if existing and existing['ids']:
                        self.embedding_service.collection.delete(ids=existing['ids'])
                        logger.info(f"Cleared {len(existing['ids'])} ChromaDB entries")
                except Exception as e:
                    logger.warning(f"Error clearing ChromaDB: {e}")
            
            # Rebuild FTS5 (delete and re-insert)
            # FTS5 is auto-synced via triggers, so we just need to trigger an update
            for chunk in sql_chunks:
                # Force trigger by updating a field
                chunk.updated_at = datetime.utcnow()
            self.db.commit()
            
            # Rebuild ChromaDB entries
            repaired_count = 0
            for chunk in sql_chunks:
                try:
                    # Generate embedding
                    embedding = await self.embedding_service.generate_embedding(chunk.text)
                    if not embedding:
                        logger.warning(f"Failed to generate embedding for chunk {chunk.id}")
                        continue
                    
                    # Add to ChromaDB
                    chromadb_id = f"{document_id}_chunk_{chunk.chunk_index}"
                    self.embedding_service.collection.add(
                        documents=[chunk.text],
                        ids=[chromadb_id],
                        metadatas=[{
                            "document_id": document_id,
                            "chunk_index": chunk.chunk_index,
                            "chunk_id": chunk.id
                        }],
                        embeddings=[embedding]
                    )
                    
                    # Update indexed_at
                    chunk.indexed_at = datetime.utcnow()
                    repaired_count += 1
                
                except Exception as e:
                    logger.error(f"Error repairing chunk {chunk.id}: {e}")
            
            self.db.commit()
            
            # Verify repair
            verification = await self.verify_triple_index(document_id)
            
            return {
                "success": verification['consistent'],
                "chunks_repaired": repaired_count,
                "verification": verification
            }
        
        except Exception as e:
            logger.error(f"Error repairing index: {e}", exc_info=True)
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }


def get_indexing_service(db_session: Session) -> IndexingService:
    """
    Get IndexingService instance.
    
    Args:
        db_session: SQLAlchemy session
    
    Returns:
        IndexingService instance
    """
    return IndexingService(db_session)

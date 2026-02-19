"""
PPA - Persistent Storage Adapter

Unified persistence layer that handles both:
- SQL Database (SQLite) for structured data
- Vector Database (ChromaDB) for embeddings and semantic search

This adapter provides a single interface for all storage operations.
"""

import logging
from typing import Dict, List, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .base_adapter import DocumentSchema, SourceType
from app.db.models import Boletin

logger = logging.getLogger(__name__)


class PersistenceAdapter:
    """
    Unified persistence adapter for SQL and Vector databases.
    
    Provides methods to:
    - Save documents to SQL database
    - Generate and store embeddings in Vector DB
    - Query documents by various criteria
    - Perform semantic search
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Initialize persistence adapter.
        
        Args:
            db_session: Optional SQLAlchemy async session
        """
        self.db_session = db_session
        
        # Initialize embedding service for vector operations
        try:
            from app.services.embedding_service import get_embedding_service
            self.embedding_service = get_embedding_service()
            logger.info("Embedding service initialized in PPA")
        except Exception as e:
            logger.warning(f"Could not initialize embedding service: {e}")
            self.embedding_service = None
        
        self.stats = {
            "documents_saved": 0,
            "embeddings_created": 0,
            "queries_executed": 0,
            "errors": 0
        }
    
    async def save_document(
        self,
        document: DocumentSchema,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Save a document to SQL database.
        
        Args:
            document: Normalized document to save
            db: Optional database session
            
        Returns:
            Dict with save result including database ID
        """
        session = db or self.db_session
        
        if not session:
            logger.error("No database session available")
            return {
                "success": False,
                "error": "No database session"
            }
        
        try:
            # For now, only handle boletines (provincial bulletins)
            # In future, extend to handle all document types
            
            if document.source_type == SourceType.PROVINCIAL and document.category.value == "boletin":
                # Check if document already exists
                result = await session.execute(
                    select(Boletin).where(Boletin.filename == document.filename)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing document
                    existing.contenido = document.content
                    existing.status = document.extraction_status
                    existing.jurisdiccion_id = document.jurisdiction_id
                    
                    if document.metadata:
                        # Merge metadata
                        existing_meta = existing.metadata or {}
                        existing_meta.update(document.metadata)
                        existing.metadata = existing_meta
                    
                    await session.commit()
                    await session.refresh(existing)
                    
                    self.stats["documents_saved"] += 1
                    
                    return {
                        "success": True,
                        "id": existing.id,
                        "action": "updated",
                        "document_id": document.document_id
                    }
                else:
                    # Create new document
                    boletin = Boletin(
                        filename=document.filename,
                        date=document.document_date,
                        section=document.section or "1",
                        fuente=document.metadata.get('source', 'unknown'),
                        contenido=document.content,
                        status=document.extraction_status or "pending",
                        jurisdiccion_id=document.jurisdiction_id or 1,
                        metadata=document.metadata
                    )
                    
                    session.add(boletin)
                    await session.commit()
                    await session.refresh(boletin)
                    
                    self.stats["documents_saved"] += 1
                    
                    return {
                        "success": True,
                        "id": boletin.id,
                        "action": "created",
                        "document_id": document.document_id
                    }
            else:
                # For other document types, we'll implement specific handlers
                logger.warning(f"Document type {document.category} not yet supported for persistence")
                return {
                    "success": False,
                    "error": f"Document type {document.category} not yet supported"
                }
        
        except Exception as e:
            logger.error(f"Error saving document: {e}", exc_info=True)
            self.stats["errors"] += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    async def save_batch(
        self,
        documents: List[DocumentSchema],
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Save multiple documents in batch.
        
        Args:
            documents: List of documents to save
            db: Optional database session
            
        Returns:
            List of save results
        """
        results = []
        
        for document in documents:
            result = await self.save_document(document, db)
            results.append(result)
        
        successful = sum(1 for r in results if r.get('success'))
        logger.info(f"Saved batch: {successful}/{len(documents)} successful")
        
        return results
    
    async def get_document_by_id(
        self,
        document_id: int,
        db: Optional[AsyncSession] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by its database ID.
        
        Args:
            document_id: Database ID
            db: Optional database session
            
        Returns:
            Document data as dict or None
        """
        session = db or self.db_session
        
        if not session:
            return None
        
        try:
            result = await session.execute(
                select(Boletin).where(Boletin.id == document_id)
            )
            boletin = result.scalar_one_or_none()
            
            if not boletin:
                return None
            
            self.stats["queries_executed"] += 1
            
            return {
                "id": boletin.id,
                "filename": boletin.filename,
                "date": boletin.date,
                "section": boletin.section,
                "content": boletin.contenido,
                "status": boletin.status,
                "jurisdiction_id": boletin.jurisdiccion_id,
                "metadata": boletin.metadata
            }
        
        except Exception as e:
            logger.error(f"Error retrieving document: {e}")
            self.stats["errors"] += 1
            return None
    
    async def query_documents(
        self,
        filters: Dict[str, Any],
        db: Optional[AsyncSession] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query documents with filters.
        
        Args:
            filters: Dict with filter criteria (e.g., {'status': 'completed', 'jurisdiction_id': 1})
            db: Optional database session
            limit: Maximum number of results
            
        Returns:
            List of matching documents
        """
        session = db or self.db_session
        
        if not session:
            return []
        
        try:
            query = select(Boletin)
            
            # Apply filters
            if 'status' in filters:
                query = query.where(Boletin.status == filters['status'])
            
            if 'jurisdiction_id' in filters:
                query = query.where(Boletin.jurisdiccion_id == filters['jurisdiction_id'])
            
            if 'date_from' in filters:
                query = query.where(Boletin.date >= filters['date_from'])
            
            if 'date_to' in filters:
                query = query.where(Boletin.date <= filters['date_to'])
            
            query = query.limit(limit)
            
            result = await session.execute(query)
            boletines = result.scalars().all()
            
            self.stats["queries_executed"] += 1
            
            return [
                {
                    "id": b.id,
                    "filename": b.filename,
                    "date": b.date,
                    "section": b.section,
                    "status": b.status,
                    "jurisdiction_id": b.jurisdiccion_id,
                    "metadata": b.metadata
                }
                for b in boletines
            ]
        
        except Exception as e:
            logger.error(f"Error querying documents: {e}")
            self.stats["errors"] += 1
            return []
    
    async def create_embedding(
        self,
        document_id: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create and store an embedding for a document.
        
        Args:
            document_id: Database ID of document
            content: Text content to embed
            metadata: Optional metadata to store with embedding
            
        Returns:
            Result dict
        """
        if not self.embedding_service:
            return {
                "success": False,
                "error": "Embedding service not available"
            }
        
        try:
            result = await self.embedding_service.add_document(
                document_id=str(document_id),
                content=content,
                metadata=metadata,
                chunk=True
            )
            
            if result.get("success"):
                self.stats["embeddings_created"] += result.get("chunks_created", 0)
            
            return result
        
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            self.stats["errors"] += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using embeddings.
        
        Args:
            query: Search query
            limit: Maximum results
            filters: Optional filters
            
        Returns:
            List of matching documents with similarity scores
        """
        if not self.embedding_service:
            logger.warning("Embedding service not available for semantic search")
            return []
        
        try:
            results = await self.embedding_service.search(
                query=query,
                n_results=limit,
                filter=filters
            )
            
            self.stats["queries_executed"] += 1
            
            return results
        
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            self.stats["errors"] += 1
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get persistence statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "documents_saved": 0,
            "embeddings_created": 0,
            "queries_executed": 0,
            "errors": 0
        }


def create_persistence_adapter(db_session: Optional[AsyncSession] = None) -> PersistenceAdapter:
    """Create a persistence adapter instance."""
    return PersistenceAdapter(db_session)

"""
Retrieval Service - Orchestrates multiple search techniques

Provides unified interface for:
- Semantic search (vector similarity via ChromaDB)
- Keyword search (BM25 via SQLite FTS5)
- Hybrid search (RRF fusion of semantic + keyword)
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.embedding_service import get_embedding_service
from app.services.fts_service import get_fts_service
from app.services.reranker_service import get_reranker_service

logger = logging.getLogger(__name__)


class SearchResult:
    """Unified search result from any technique."""
    
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        chunk_index: int,
        text: str,
        score: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.chunk_index = chunk_index
        self.text = text
        self.score = score  # Normalized [0, 1], higher = better
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "score": self.score,
            "metadata": self.metadata
        }


class RetrievalService:
    """
    Service for document retrieval using multiple techniques.
    
    Supports:
    - Semantic search via embeddings
    - Keyword search via BM25
    - Hybrid search with RRF fusion
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize retrieval service.
        
        Args:
            db_session: SQLAlchemy session (required for keyword search)
        """
        self.db_session = db_session
        self.embedding_service = get_embedding_service()
        self.fts_service = get_fts_service(db_session) if db_session else None
    
    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Semantic search using vector embeddings.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional ChromaDB metadata filters
        
        Returns:
            List of SearchResult ordered by semantic similarity
        """
        try:
            raw_results = await self.embedding_service.search(
                query=query,
                n_results=top_k,
                filter=filters
            )
            
            results = []
            for i, result in enumerate(raw_results):
                distance = result.get('distance', 0.0)
                # Convert distance to score [0, 1], lower distance = higher score
                score = max(0.0, min(1.0, 1.0 - (distance / 2.0)))
                
                metadata = result.get('metadata', {})
                document_id = metadata.get('document_id', '')
                chunk_index = metadata.get('chunk_index', i)
                chunk_id = f"{document_id}_{chunk_index}"
                
                results.append(SearchResult(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    chunk_index=chunk_index,
                    text=result.get('document', ''),
                    score=score,
                    metadata=metadata
                ))
            
            return results
        
        except Exception as e:
            logger.error(f"Error in semantic search: {e}", exc_info=True)
            return []
    
    def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Keyword search using BM25 (SQLite FTS5).
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional filters (document_id, section_type, etc.)
        
        Returns:
            List of SearchResult ordered by BM25 score
        """
        if not self.fts_service:
            logger.warning("FTS service not initialized (no db_session)")
            return []
        
        try:
            fts_results = self.fts_service.search_bm25(
                query=query,
                top_k=top_k,
                filters=filters
            )
            
            # Normalize BM25 scores to [0, 1]
            results = []
            if fts_results:
                max_score = max(r.bm25_score for r in fts_results)
                min_score = min(r.bm25_score for r in fts_results)
                score_range = max_score - min_score if max_score > min_score else 1.0
                
                for result in fts_results:
                    normalized_score = (result.bm25_score - min_score) / score_range if score_range > 0 else 1.0
                    
                    chunk_id = f"{result.document_id}_{result.chunk_index}"
                    
                    results.append(SearchResult(
                        chunk_id=chunk_id,
                        document_id=result.document_id,
                        chunk_index=result.chunk_index,
                        text=result.text,
                        score=normalized_score,
                        metadata={
                            "document_id": result.document_id,
                            "chunk_index": result.chunk_index,
                            "section_type": result.section_type
                        }
                    ))
            
            return results
        
        except Exception as e:
            logger.error(f"Error in keyword search: {e}", exc_info=True)
            return []
    
    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        semantic_filters: Optional[Dict[str, Any]] = None,
        keyword_filters: Optional[Dict[str, Any]] = None,
        rrf_k: int = 60,
        rerank: bool = False,
        rerank_strategy: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Hybrid search combining semantic + keyword with RRF fusion.
        
        Args:
            query: Search query
            top_k: Final number of results to return
            semantic_filters: Filters for semantic search
            keyword_filters: Filters for keyword search
            rrf_k: RRF constant (default 60)
            rerank: Whether to apply re-ranking (default False)
            rerank_strategy: Reranker strategy ("google", "cross-encoder", "noop", or None for auto)
        
        Returns:
            List of SearchResult ordered by fused RRF score (or re-ranked score)
        """
        # Retrieve more results from each method for better fusion
        retrieve_k = max(top_k * 2, 20)
        
        try:
            # Execute both searches in parallel
            semantic_task = self.semantic_search(query, retrieve_k, semantic_filters)
            keyword_task = asyncio.to_thread(
                self.keyword_search, query, retrieve_k, keyword_filters
            )
            
            semantic_results, keyword_results = await asyncio.gather(
                semantic_task, keyword_task
            )
            
            # Apply RRF fusion
            fused_results = self.rrf_fusion(
                [semantic_results, keyword_results],
                k=rrf_k
            )
            
            # Apply re-ranking if requested
            if rerank:
                # Re-rank top 20, return top_k
                rerank_input = fused_results[:min(20, len(fused_results))]
                reranked_results = await self.apply_reranking(
                    query, rerank_input, top_k, rerank_strategy
                )
                return reranked_results
            
            # Return top_k without re-ranking
            return fused_results[:top_k]
        
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}", exc_info=True)
            return []
    
    async def apply_reranking(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 5,
        strategy: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Apply re-ranking to search results.
        
        Args:
            query: Original search query
            results: List of search results to re-rank
            top_k: Number of top results to return
            strategy: Reranker strategy (None for auto-select)
        
        Returns:
            Re-ranked list of top_k results
        """
        try:
            reranker = get_reranker_service(strategy)
            
            # Run re-ranking in thread pool (may be CPU-intensive)
            reranked = await asyncio.to_thread(
                reranker.rerank, query, results, top_k
            )
            
            return reranked
        
        except Exception as e:
            logger.error(f"Error applying re-ranking: {e}", exc_info=True)
            # Fallback: return top_k without re-ranking
            return results[:top_k]
    
    def rrf_fusion(
        self,
        result_lists: List[List[SearchResult]],
        k: int = 60
    ) -> List[SearchResult]:
        """
        Reciprocal Rank Fusion - fuses multiple ranked lists.
        
        Formula: score(d) = Σ 1/(k + rank_i(d))
        
        Args:
            result_lists: List of ranked result lists from different methods
            k: RRF constant (default 60, standard value)
        
        Returns:
            Single fused and re-ranked list
        """
        # Build ranking map: chunk_id -> list of ranks
        rankings: Dict[str, List[int]] = {}
        all_results: Dict[str, SearchResult] = {}
        
        for result_list in result_lists:
            for rank, result in enumerate(result_list):
                chunk_id = result.chunk_id
                
                if chunk_id not in rankings:
                    rankings[chunk_id] = []
                    all_results[chunk_id] = result
                
                rankings[chunk_id].append(rank)
        
        # Calculate RRF scores
        rrf_scores: Dict[str, float] = {}
        for chunk_id, rank_list in rankings.items():
            score = sum(1.0 / (k + rank + 1) for rank in rank_list)
            rrf_scores[chunk_id] = score
        
        # Sort by RRF score (descending)
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: -x[1])
        
        # Build final result list with RRF scores
        fused_results = []
        for chunk_id, rrf_score in sorted_ids:
            result = all_results[chunk_id]
            # Update score to RRF score (already in descending order)
            # Normalize RRF score to [0, 1] range for consistency
            result.score = rrf_score
            fused_results.append(result)
        
        # Normalize scores to [0, 1]
        if fused_results:
            max_score = fused_results[0].score
            min_score = fused_results[-1].score
            score_range = max_score - min_score if max_score > min_score else 1.0
            
            for result in fused_results:
                result.score = (result.score - min_score) / score_range if score_range > 0 else 1.0
        
        return fused_results


def get_retrieval_service(db_session: Optional[Session] = None) -> RetrievalService:
    """
    Get a retrieval service instance.
    
    Args:
        db_session: SQLAlchemy session (required for keyword/hybrid search)
    
    Returns:
        RetrievalService instance
    """
    return RetrievalService(db_session)

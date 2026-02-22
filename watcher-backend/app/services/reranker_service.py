"""
Reranker Service - Post-processing re-ranking of search results

Provides pluggable re-ranking strategies:
- Google-based re-ranking (using Gemini for relevance scoring)
- Cross-encoder re-ranking (local model, requires sentence-transformers)
- Noop re-ranker (pass-through, no re-ranking)
"""

import logging
import os
from typing import List, Optional, Protocol
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Try to import Google AI
try:
    import google.generativeai as genai
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    logger.warning("Google Generative AI not available for re-ranking")
    GOOGLE_AI_AVAILABLE = False

# Try to import sentence-transformers for cross-encoder
try:
    from sentence_transformers import CrossEncoder
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.info("sentence-transformers not available (optional for re-ranking)")
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class SearchResultProtocol(Protocol):
    """Protocol for search result objects."""
    chunk_id: str
    text: str
    score: float


class BaseReranker(ABC):
    """Base class for re-ranking strategies."""
    
    @abstractmethod
    def rerank(
        self,
        query: str,
        results: List[SearchResultProtocol],
        top_k: int = 5
    ) -> List[SearchResultProtocol]:
        """
        Re-rank search results based on query relevance.
        
        Args:
            query: Original search query
            results: List of search results to re-rank
            top_k: Number of top results to return
        
        Returns:
            Re-ranked list of results (top_k items)
        """
        pass


class NoopReranker(BaseReranker):
    """No-op reranker - returns results unchanged."""
    
    def rerank(
        self,
        query: str,
        results: List[SearchResultProtocol],
        top_k: int = 5
    ) -> List[SearchResultProtocol]:
        """Return top_k results without re-ranking."""
        return results[:top_k]


class GoogleReranker(BaseReranker):
    """
    Google-based re-ranker using Gemini for relevance scoring.
    
    Uses Google Gemini to score each result's relevance to the query.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        """
        Initialize Google re-ranker.
        
        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            model: Gemini model to use for scoring
        """
        if not GOOGLE_AI_AVAILABLE:
            raise ImportError("Google Generative AI not available. Install: pip install google-generativeai")
        
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key required for GoogleReranker")
        
        # genai.configure() is called once at app startup in main.py
        self.model_name = model
    
    def rerank(
        self,
        query: str,
        results: List[SearchResultProtocol],
        top_k: int = 5
    ) -> List[SearchResultProtocol]:
        """
        Re-rank results using Google Gemini relevance scoring.
        
        For each result, asks Gemini to score relevance on 0-10 scale.
        """
        if not results:
            return []
        
        try:
            model = genai.GenerativeModel(self.model_name)
            
            # Score each result
            scored_results = []
            for result in results:
                # Create prompt for relevance scoring
                prompt = f"""Score the relevance of this text to the query on a scale of 0-10.
Return ONLY a number between 0 and 10.

Query: {query}

Text: {result.text[:500]}...

Relevance score (0-10):"""
                
                try:
                    response = model.generate_content(prompt)
                    score_text = response.text.strip()
                    
                    # Try to parse score
                    relevance_score = float(score_text)
                    relevance_score = max(0.0, min(10.0, relevance_score))  # Clamp to [0, 10]
                    
                    # Normalize to [0, 1]
                    result.score = relevance_score / 10.0
                    scored_results.append(result)
                
                except Exception as e:
                    logger.warning(f"Error scoring result {result.chunk_id}: {e}")
                    # Keep original score on error
                    scored_results.append(result)
            
            # Sort by new relevance score (descending)
            scored_results.sort(key=lambda x: -x.score)
            
            logger.info(f"Google re-ranked {len(results)} results -> returning top {top_k}")
            return scored_results[:top_k]
        
        except Exception as e:
            logger.error(f"Error in Google re-ranking: {e}", exc_info=True)
            # Fallback: return original results
            return results[:top_k]


class CrossEncoderReranker(BaseReranker):
    """
    Local cross-encoder re-ranker.
    
    Uses sentence-transformers cross-encoder model for relevance scoring.
    Model: cross-encoder/ms-marco-MiniLM-L-6-v2
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize cross-encoder re-ranker.
        
        Args:
            model_name: HuggingFace model name
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        
        self.model = CrossEncoder(model_name)
        logger.info(f"Loaded cross-encoder model: {model_name}")
    
    def rerank(
        self,
        query: str,
        results: List[SearchResultProtocol],
        top_k: int = 5
    ) -> List[SearchResultProtocol]:
        """
        Re-rank results using cross-encoder model.
        
        Cross-encoders jointly encode query and document for better relevance.
        """
        if not results:
            return []
        
        try:
            # Create query-document pairs
            pairs = [(query, result.text) for result in results]
            
            # Predict relevance scores
            scores = self.model.predict(pairs)
            
            # Update result scores
            for i, result in enumerate(results):
                result.score = float(scores[i])
            
            # Sort by score (descending)
            results.sort(key=lambda x: -x.score)
            
            logger.info(f"Cross-encoder re-ranked {len(results)} results -> returning top {top_k}")
            return results[:top_k]
        
        except Exception as e:
            logger.error(f"Error in cross-encoder re-ranking: {e}", exc_info=True)
            return results[:top_k]


class RerankerService:
    """
    Service for re-ranking search results.
    
    Automatically selects best available strategy:
    1. Google re-ranker (if Google API key available)
    2. Cross-encoder (if sentence-transformers installed)
    3. Noop (fallback)
    """
    
    def __init__(self, strategy: Optional[str] = None):
        """
        Initialize reranker service.
        
        Args:
            strategy: Reranker strategy ("google", "cross-encoder", "noop", or None for auto)
        """
        self.strategy_name = strategy
        self.reranker = self._create_reranker(strategy)
    
    def _create_reranker(self, strategy: Optional[str]) -> BaseReranker:
        """Create reranker based on strategy and availability."""
        
        # If strategy specified, use it
        if strategy == "noop":
            logger.info("Using noop reranker (no re-ranking)")
            return NoopReranker()
        
        elif strategy == "google":
            if GOOGLE_AI_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
                logger.info("Using Google reranker")
                return GoogleReranker()
            else:
                logger.warning("Google reranker requested but not available, using noop")
                return NoopReranker()
        
        elif strategy == "cross-encoder":
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                logger.info("Using cross-encoder reranker")
                return CrossEncoderReranker()
            else:
                logger.warning("Cross-encoder requested but not available, using noop")
                return NoopReranker()
        
        # Auto-select best available
        elif strategy is None:
            if GOOGLE_AI_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
                logger.info("Auto-selected Google reranker")
                return GoogleReranker()
            elif SENTENCE_TRANSFORMERS_AVAILABLE:
                logger.info("Auto-selected cross-encoder reranker")
                return CrossEncoderReranker()
            else:
                logger.info("No reranker available, using noop")
                return NoopReranker()
        
        else:
            logger.warning(f"Unknown strategy '{strategy}', using noop")
            return NoopReranker()
    
    def rerank(
        self,
        query: str,
        results: List[SearchResultProtocol],
        top_k: int = 5
    ) -> List[SearchResultProtocol]:
        """
        Re-rank search results.
        
        Args:
            query: Original search query
            results: List of search results to re-rank
            top_k: Number of top results to return (default 5)
        
        Returns:
            Re-ranked list of top_k results
        """
        return self.reranker.rerank(query, results, top_k)


def get_reranker_service(strategy: Optional[str] = None) -> RerankerService:
    """
    Get a reranker service instance.
    
    Args:
        strategy: Reranker strategy ("google", "cross-encoder", "noop", or None for auto)
    
    Returns:
        RerankerService instance
    """
    return RerankerService(strategy)

"""
Full-Text Search Service using SQLite FTS5

This service handles keyword-based search using BM25 algorithm via SQLite FTS5.
Works in conjunction with vector-based semantic search for hybrid retrieval.
"""

import logging
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class FTSSearchResult:
    """Result from FTS5 BM25 search."""
    
    def __init__(
        self,
        chunk_id: int,
        document_id: str,
        chunk_index: int,
        text: str,
        section_type: Optional[str],
        bm25_score: float
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.chunk_index = chunk_index
        self.text = text
        self.section_type = section_type
        self.bm25_score = bm25_score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "section_type": self.section_type,
            "bm25_score": self.bm25_score
        }


class FTSService:
    """Service for full-text search using SQLite FTS5 with BM25."""
    
    def __init__(self, db_session: Session):
        """
        Initialize FTS service.
        
        Args:
            db_session: SQLAlchemy session
        """
        self.db = db_session
    
    def search_bm25(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[FTSSearchResult]:
        """
        Perform BM25 full-text search using FTS5.
        
        Args:
            query: Search query (supports FTS5 query syntax)
            top_k: Number of results to return
            filters: Optional filters (document_id, section_type, topic, language, 
                    has_tables, has_amounts, boletin_id, year, month)
        
        Returns:
            List of FTSSearchResult ordered by BM25 score (descending)
        """
        if not query or not query.strip():
            return []
        
        try:
            # Build WHERE clause for filters
            where_clauses = []
            params = {"query": query, "limit": top_k}
            
            if filters:
                # Identity filters
                if filters.get("document_id"):
                    where_clauses.append("c.document_id = :document_id")
                    params["document_id"] = filters["document_id"]
                
                if filters.get("boletin_id") is not None:
                    where_clauses.append("c.boletin_id = :boletin_id")
                    params["boletin_id"] = filters["boletin_id"]
                
                # Section filter
                if filters.get("section_type"):
                    where_clauses.append("c.section_type = :section_type")
                    params["section_type"] = filters["section_type"]
                
                # Enriched metadata filters
                if filters.get("topic"):
                    where_clauses.append("c.topic = :topic")
                    params["topic"] = filters["topic"]
                
                if filters.get("language"):
                    where_clauses.append("c.language = :language")
                    params["language"] = filters["language"]
                
                if filters.get("has_tables") is not None:
                    where_clauses.append("c.has_tables = :has_tables")
                    params["has_tables"] = 1 if filters["has_tables"] else 0
                
                if filters.get("has_amounts") is not None:
                    where_clauses.append("c.has_amounts = :has_amounts")
                    params["has_amounts"] = 1 if filters["has_amounts"] else 0
                
                # Date filters (require parsing from boletin metadata)
                # Note: This assumes there's a way to get date from document_id or boletin
                # For now, we skip year/month filters in FTS5 as they need more complex JOIN
                # They can be added later if boletines table is joined
            
            where_sql = ""
            if where_clauses:
                where_sql = " AND " + " AND ".join(where_clauses)
            
            # FTS5 query with BM25 scoring
            # bm25(chunk_records_fts) returns BM25 score (negative, lower = better match)
            # We multiply by -1 to get positive scores (higher = better)
            sql = text(f"""
                SELECT 
                    c.id,
                    c.document_id,
                    c.chunk_index,
                    c.text,
                    c.section_type,
                    -bm25(chunk_records_fts) as bm25_score
                FROM chunk_records_fts
                JOIN chunk_records AS c ON c.id = chunk_records_fts.rowid
                WHERE chunk_records_fts MATCH :query{where_sql}
                ORDER BY bm25(chunk_records_fts)
                LIMIT :limit
            """)
            
            result = self.db.execute(sql, params)
            rows = result.fetchall()
            
            results = []
            for row in rows:
                results.append(FTSSearchResult(
                    chunk_id=row[0],
                    document_id=row[1],
                    chunk_index=row[2],
                    text=row[3],
                    section_type=row[4],
                    bm25_score=row[5]
                ))
            
            logger.info(f"FTS5 search for '{query}' returned {len(results)} results")
            return results
        
        except Exception as e:
            logger.error(f"Error performing FTS5 search: {e}", exc_info=True)
            return []
    
    def rebuild_index(self) -> Dict[str, Any]:
        """
        Rebuild the entire FTS5 index from chunk_records table.
        
        Useful after bulk inserts or to fix index corruption.
        
        Returns:
            Dict with status and statistics
        """
        try:
            # Check if FTS5 table exists
            check_sql = text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='chunk_records_fts'
            """)
            result = self.db.execute(check_sql)
            if not result.fetchone():
                return {
                    "success": False,
                    "error": "FTS5 table chunk_records_fts does not exist"
                }
            
            # Use FTS5 rebuild command
            # This efficiently rebuilds the index
            rebuild_sql = text("INSERT INTO chunk_records_fts(chunk_records_fts) VALUES('rebuild')")
            self.db.execute(rebuild_sql)
            self.db.commit()
            
            # Get statistics
            stats = self.get_index_stats()
            
            logger.info(f"FTS5 index rebuilt successfully. Total chunks: {stats.get('total_chunks', 0)}")
            
            return {
                "success": True,
                "message": "FTS5 index rebuilt successfully",
                "stats": stats
            }
        
        except Exception as e:
            logger.error(f"Error rebuilding FTS5 index: {e}", exc_info=True)
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def optimize_index(self) -> Dict[str, Any]:
        """
        Optimize the FTS5 index for better performance.
        
        This merges index segments to reduce fragmentation.
        Should be run periodically after many inserts/deletes.
        
        Returns:
            Dict with status
        """
        try:
            optimize_sql = text("INSERT INTO chunk_records_fts(chunk_records_fts) VALUES('optimize')")
            self.db.execute(optimize_sql)
            self.db.commit()
            
            logger.info("FTS5 index optimized successfully")
            
            return {
                "success": True,
                "message": "FTS5 index optimized successfully"
            }
        
        except Exception as e:
            logger.error(f"Error optimizing FTS5 index: {e}", exc_info=True)
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the FTS5 index.
        
        Returns:
            Dict with statistics
        """
        try:
            # Count total chunks in FTS5 index
            count_sql = text("SELECT COUNT(*) FROM chunk_records_fts")
            result = self.db.execute(count_sql)
            total_chunks = result.scalar()
            
            # Count chunks in source table
            source_count_sql = text("SELECT COUNT(*) FROM chunk_records")
            result = self.db.execute(source_count_sql)
            source_chunks = result.scalar()
            
            # Get section type distribution from FTS5
            section_sql = text("""
                SELECT c.section_type, COUNT(*) as count
                FROM chunk_records_fts AS fts
                JOIN chunk_records AS c ON c.id = fts.rowid
                WHERE c.section_type IS NOT NULL
                GROUP BY c.section_type
                ORDER BY count DESC
            """)
            result = self.db.execute(section_sql)
            sections = {row[0]: row[1] for row in result.fetchall()}
            
            return {
                "total_chunks": total_chunks,
                "source_chunks": source_chunks,
                "in_sync": total_chunks == source_chunks,
                "by_section": sections
            }
        
        except Exception as e:
            logger.error(f"Error getting FTS5 stats: {e}", exc_info=True)
            return {
                "total_chunks": 0,
                "error": str(e)
            }
    
    def test_query(self, query: str) -> Dict[str, Any]:
        """
        Test a query to see how FTS5 parses it.
        
        Useful for debugging query syntax.
        
        Args:
            query: Query to test
        
        Returns:
            Dict with query parsing info
        """
        try:
            # Try the query with LIMIT 1 to see if it's valid
            results = self.search_bm25(query, top_k=1)
            
            return {
                "valid": True,
                "query": query,
                "result_count": len(results),
                "message": "Query is valid"
            }
        
        except Exception as e:
            return {
                "valid": False,
                "query": query,
                "error": str(e),
                "message": "Query syntax error"
            }


# Global instance
_fts_service: Optional[FTSService] = None


def get_fts_service(db_session: Session) -> FTSService:
    """
    Get FTS service instance.
    
    Args:
        db_session: SQLAlchemy session
    
    Returns:
        FTSService instance
    """
    return FTSService(db_session)

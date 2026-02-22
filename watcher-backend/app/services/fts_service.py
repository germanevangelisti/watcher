"""
Full-Text Search Service

Supports two backends:
- PostgreSQL: tsvector/tsquery with ts_rank (production)
- SQLite: FTS5 with BM25 (development fallback)

The backend is chosen automatically based on DATABASE_URL.
"""

import logging
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)


class FTSSearchResult:
    """Result from full-text search."""

    def __init__(
        self,
        chunk_id: int,
        document_id: str,
        chunk_index: int,
        text: str,
        section_type: Optional[str],
        bm25_score: float,
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
            "bm25_score": self.bm25_score,
        }


class FTSService:
    """Full-text search service with PostgreSQL and SQLite backends."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self._use_postgres = settings.is_postgres

    def _build_filter_clauses(self, filters: Optional[Dict[str, Any]]) -> tuple:
        """Build WHERE clauses and params from filters dict."""
        where_clauses: list = []
        params: dict = {}

        if not filters:
            return where_clauses, params

        if filters.get("document_id"):
            where_clauses.append("c.document_id = :document_id")
            params["document_id"] = filters["document_id"]
        if filters.get("boletin_id") is not None:
            where_clauses.append("c.boletin_id = :boletin_id")
            params["boletin_id"] = filters["boletin_id"]
        if filters.get("section_type"):
            where_clauses.append("c.section_type = :section_type")
            params["section_type"] = filters["section_type"]
        if filters.get("topic"):
            where_clauses.append("c.topic = :topic")
            params["topic"] = filters["topic"]
        if filters.get("language"):
            where_clauses.append("c.language = :language")
            params["language"] = filters["language"]
        if filters.get("has_tables") is not None:
            where_clauses.append("c.has_tables = :has_tables")
            params["has_tables"] = filters["has_tables"]
        if filters.get("has_amounts") is not None:
            where_clauses.append("c.has_amounts = :has_amounts")
            params["has_amounts"] = filters["has_amounts"]

        return where_clauses, params

    # ------------------------------------------------------------------
    # PostgreSQL backend
    # ------------------------------------------------------------------

    def _search_postgres(
        self, query: str, top_k: int, filters: Optional[Dict[str, Any]]
    ) -> List[FTSSearchResult]:
        where_clauses, params = self._build_filter_clauses(filters)
        params["query"] = query
        params["limit"] = top_k

        tsquery_expr = "plainto_tsquery('spanish', :query)"
        rank_expr = f"ts_rank(c.search_vector, {tsquery_expr})"

        where_clauses.insert(0, f"c.search_vector @@ {tsquery_expr}")
        where_sql = " AND ".join(where_clauses)

        sql = text(f"""
            SELECT
                c.id,
                c.document_id,
                c.chunk_index,
                c.text,
                c.section_type,
                {rank_expr} AS score
            FROM chunk_records AS c
            WHERE {where_sql}
            ORDER BY score DESC
            LIMIT :limit
        """)

        result = self.db.execute(sql, params)
        rows = result.fetchall()
        return [
            FTSSearchResult(
                chunk_id=r[0], document_id=r[1], chunk_index=r[2],
                text=r[3], section_type=r[4], bm25_score=r[5],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # SQLite FTS5 backend
    # ------------------------------------------------------------------

    def _search_sqlite(
        self, query: str, top_k: int, filters: Optional[Dict[str, Any]]
    ) -> List[FTSSearchResult]:
        where_clauses, params = self._build_filter_clauses(filters)
        params["query"] = query
        params["limit"] = top_k

        # SQLite FTS5 uses boolean 0/1
        if "has_tables" in params:
            params["has_tables"] = 1 if params["has_tables"] else 0
        if "has_amounts" in params:
            params["has_amounts"] = 1 if params["has_amounts"] else 0

        extra_where = ""
        if where_clauses:
            extra_where = " AND " + " AND ".join(where_clauses)

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
            WHERE chunk_records_fts MATCH :query{extra_where}
            ORDER BY bm25(chunk_records_fts)
            LIMIT :limit
        """)

        result = self.db.execute(sql, params)
        rows = result.fetchall()
        return [
            FTSSearchResult(
                chunk_id=r[0], document_id=r[1], chunk_index=r[2],
                text=r[3], section_type=r[4], bm25_score=r[5],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_bm25(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[FTSSearchResult]:
        """Full-text search. Delegates to the appropriate backend."""
        if not query or not query.strip():
            return []
        try:
            if self._use_postgres:
                results = self._search_postgres(query, top_k, filters)
            else:
                results = self._search_sqlite(query, top_k, filters)
            logger.info(f"FTS search for '{query}' returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Error performing FTS search: {e}", exc_info=True)
            return []

    def rebuild_index(self) -> Dict[str, Any]:
        """Rebuild the full-text search index."""
        try:
            if self._use_postgres:
                self.db.execute(text(
                    "UPDATE chunk_records SET search_vector = to_tsvector('spanish', COALESCE(text, ''))"
                ))
            else:
                check = self.db.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='chunk_records_fts'"
                ))
                if not check.fetchone():
                    return {"success": False, "error": "FTS5 table does not exist"}
                self.db.execute(text(
                    "INSERT INTO chunk_records_fts(chunk_records_fts) VALUES('rebuild')"
                ))
            self.db.commit()
            stats = self.get_index_stats()
            logger.info(f"FTS index rebuilt. Total chunks: {stats.get('total_chunks', 0)}")
            return {"success": True, "message": "FTS index rebuilt successfully", "stats": stats}
        except Exception as e:
            logger.error(f"Error rebuilding FTS index: {e}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def optimize_index(self) -> Dict[str, Any]:
        """Optimize the search index (SQLite-specific; no-op on PostgreSQL)."""
        try:
            if self._use_postgres:
                self.db.execute(text("REINDEX INDEX idx_chunk_search_vector"))
            else:
                self.db.execute(text(
                    "INSERT INTO chunk_records_fts(chunk_records_fts) VALUES('optimize')"
                ))
            self.db.commit()
            logger.info("FTS index optimized")
            return {"success": True, "message": "FTS index optimized successfully"}
        except Exception as e:
            logger.error(f"Error optimizing FTS index: {e}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the search index."""
        try:
            if self._use_postgres:
                count_sql = text(
                    "SELECT COUNT(*) FROM chunk_records WHERE search_vector IS NOT NULL"
                )
            else:
                count_sql = text("SELECT COUNT(*) FROM chunk_records_fts")
            result = self.db.execute(count_sql)
            total_chunks = result.scalar()

            source_sql = text("SELECT COUNT(*) FROM chunk_records")
            source_chunks = self.db.execute(source_sql).scalar()

            section_sql = text("""
                SELECT section_type, COUNT(*) as cnt
                FROM chunk_records
                WHERE section_type IS NOT NULL
                GROUP BY section_type
                ORDER BY cnt DESC
            """)
            sections = {r[0]: r[1] for r in self.db.execute(section_sql).fetchall()}

            return {
                "total_chunks": total_chunks,
                "source_chunks": source_chunks,
                "in_sync": total_chunks == source_chunks,
                "by_section": sections,
            }
        except Exception as e:
            logger.error(f"Error getting FTS stats: {e}", exc_info=True)
            return {"total_chunks": 0, "error": str(e)}

    def test_query(self, query: str) -> Dict[str, Any]:
        """Test whether a query is valid."""
        try:
            results = self.search_bm25(query, top_k=1)
            return {"valid": True, "query": query, "result_count": len(results), "message": "Query is valid"}
        except Exception as e:
            return {"valid": False, "query": query, "error": str(e), "message": "Query syntax error"}


_fts_service: Optional[FTSService] = None


def get_fts_service(db_session: Session) -> FTSService:
    return FTSService(db_session)

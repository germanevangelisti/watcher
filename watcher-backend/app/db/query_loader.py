"""
Query Loader — Loads SQL and Cypher queries from external files.

Inspired by br/acc's pattern of externalizing all queries into separate files
for better maintainability, testing, and performance (cached with lru_cache).

Usage:
    from app.db.query_loader import load_query

    query = load_query("dashboard_stats")       # loads app/queries/dashboard_stats.sql
    cypher = load_query("entity_search", "cypher")  # loads graph/queries/entity_search.cypher
"""

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# Resolve directories relative to the watcher-backend root
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_SQL_QUERIES_DIR = _BACKEND_ROOT / "app" / "queries"
_CYPHER_QUERIES_DIR = _BACKEND_ROOT / "graph" / "queries"


class QueryNotFoundError(FileNotFoundError):
    """Raised when a query file cannot be found."""


@lru_cache(maxsize=128)
def load_query(name: str, dialect: str = "sql") -> str:
    """
    Load a query from an external file.

    Args:
        name: Query name (without extension). E.g. "dashboard_stats".
        dialect: "sql" or "cypher". Determines the directory and file extension.

    Returns:
        The query string.

    Raises:
        QueryNotFoundError: If the query file does not exist.
    """
    if dialect == "cypher":
        base_dir = _CYPHER_QUERIES_DIR
        ext = ".cypher"
    else:
        base_dir = _SQL_QUERIES_DIR
        ext = ".sql"

    path = base_dir / f"{name}{ext}"

    if not path.is_file():
        raise QueryNotFoundError(
            f"Query '{name}' not found at {path}. "
            f"Available queries: {list_queries(dialect)}"
        )

    content = path.read_text(encoding="utf-8").strip()
    logger.debug("Loaded %s query '%s' (%d chars)", dialect, name, len(content))
    return content


def list_queries(dialect: str = "sql") -> list[str]:
    """List all available query names for the given dialect."""
    if dialect == "cypher":
        base_dir = _CYPHER_QUERIES_DIR
        ext = ".cypher"
    else:
        base_dir = _SQL_QUERIES_DIR
        ext = ".sql"

    if not base_dir.is_dir():
        return []

    return sorted(p.stem for p in base_dir.glob(f"*{ext}"))


def clear_cache() -> None:
    """Clear the query cache. Useful during development or testing."""
    load_query.cache_clear()
    logger.info("Query cache cleared")

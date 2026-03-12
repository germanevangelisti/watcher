"""
Tests for the query_loader module.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.db.query_loader import (
    QueryNotFoundError,
    clear_cache,
    list_queries,
    load_query,
)


@pytest.fixture(autouse=True)
def _clear_query_cache():
    """Clear LRU cache before each test to avoid cross-test contamination."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def tmp_query_dirs(tmp_path):
    """Create temporary query directories with sample files."""
    sql_dir = tmp_path / "app" / "queries"
    sql_dir.mkdir(parents=True)

    cypher_dir = tmp_path / "graph" / "queries"
    cypher_dir.mkdir(parents=True)

    # Create sample SQL query
    (sql_dir / "dashboard_stats.sql").write_text(
        "SELECT COUNT(*) AS total FROM boletines;"
    )
    (sql_dir / "alertas_activas.sql").write_text(
        "SELECT * FROM alertas_gestion WHERE estado = 'activa';"
    )

    # Create sample Cypher query
    (cypher_dir / "entity_search.cypher").write_text(
        "MATCH (n) WHERE n.nombre CONTAINS $query RETURN n LIMIT $limit"
    )

    return tmp_path


class TestLoadQuery:
    """Tests for load_query function."""

    def test_load_sql_query(self, tmp_query_dirs):
        """Test loading a SQL query file."""
        with patch("app.db.query_loader._SQL_QUERIES_DIR", tmp_query_dirs / "app" / "queries"):
            result = load_query("dashboard_stats", "sql")
            assert "SELECT COUNT(*)" in result
            assert "boletines" in result

    def test_load_cypher_query(self, tmp_query_dirs):
        with patch("app.db.query_loader._CYPHER_QUERIES_DIR", tmp_query_dirs / "graph" / "queries"):
            result = load_query("entity_search", "cypher")
            assert "MATCH" in result
            assert "$query" in result

    def test_query_not_found_raises_error(self, tmp_query_dirs):
        with patch("app.db.query_loader._SQL_QUERIES_DIR", tmp_query_dirs / "app" / "queries"):
            with pytest.raises(QueryNotFoundError) as exc_info:
                load_query("nonexistent_query", "sql")
            assert "nonexistent_query" in str(exc_info.value)

    def test_default_dialect_is_sql(self, tmp_query_dirs):
        with patch("app.db.query_loader._SQL_QUERIES_DIR", tmp_query_dirs / "app" / "queries"):
            result = load_query("dashboard_stats")
            assert "SELECT" in result

    def test_lru_cache_works(self, tmp_query_dirs):
        """Verify that repeated calls return cached results."""
        with patch("app.db.query_loader._SQL_QUERIES_DIR", tmp_query_dirs / "app" / "queries"):
            result1 = load_query("dashboard_stats")
            result2 = load_query("dashboard_stats")
            assert result1 is result2  # Same object = cached

    def test_query_is_stripped(self, tmp_query_dirs):
        """Verify leading/trailing whitespace is stripped."""
        query_file = tmp_query_dirs / "app" / "queries" / "whitespace.sql"
        query_file.write_text("\n\n  SELECT 1;  \n\n")
        with patch("app.db.query_loader._SQL_QUERIES_DIR", tmp_query_dirs / "app" / "queries"):
            result = load_query("whitespace")
            assert result == "SELECT 1;"


class TestListQueries:
    """Tests for list_queries function."""

    def test_list_sql_queries(self, tmp_query_dirs):
        with patch("app.db.query_loader._SQL_QUERIES_DIR", tmp_query_dirs / "app" / "queries"):
            result = list_queries("sql")
            assert "dashboard_stats" in result
            assert "alertas_activas" in result
            assert len(result) == 2

    def test_list_cypher_queries(self, tmp_query_dirs):
        with patch("app.db.query_loader._CYPHER_QUERIES_DIR", tmp_query_dirs / "graph" / "queries"):
            result = list_queries("cypher")
            assert "entity_search" in result
            assert len(result) == 1

    def test_list_empty_directory(self, tmp_path):
        """Returns empty list if query directory doesn't exist."""
        with patch("app.db.query_loader._SQL_QUERIES_DIR", tmp_path / "nonexistent"):
            result = list_queries("sql")
            assert result == []

    def test_queries_are_sorted(self, tmp_query_dirs):
        with patch("app.db.query_loader._SQL_QUERIES_DIR", tmp_query_dirs / "app" / "queries"):
            result = list_queries("sql")
            assert result == sorted(result)


class TestClearCache:
    """Tests for clear_cache function."""

    def test_clear_cache_resets_lru(self, tmp_query_dirs):
        with patch("app.db.query_loader._SQL_QUERIES_DIR", tmp_query_dirs / "app" / "queries"):
            load_query("dashboard_stats")
            info_before = load_query.cache_info()
            assert info_before.hits >= 0

            clear_cache()
            info_after = load_query.cache_info()
            assert info_after.hits == 0
            assert info_after.misses == 0

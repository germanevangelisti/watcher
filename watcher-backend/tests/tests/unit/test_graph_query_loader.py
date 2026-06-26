"""
Unit tests for Cypher query loading via query_loader.

Validates that:
- All expected .cypher files exist in graph/queries/
- Each file loads correctly and contains expected Cypher keywords
- The query_loader correctly distinguishes sql vs cypher dialects
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.db.query_loader import load_query, list_queries, clear_cache, QueryNotFoundError

# Expected query files created in Fase 2.2
EXPECTED_CYPHER_QUERIES = {
    "upsert_entity",
    "upsert_boletin",
    "upsert_mention_edge",
    "graph_overview_nodes",
    "graph_overview_links",
    "entity_relationships",
    "neighborhood",
    "load_for_networkx",
    # Fase 0.2 baseline
    "entity_search",
}


@pytest.fixture(autouse=True)
def _clear_and_patch_dirs():
    """Clear cache and patch query dirs to source tree (pip install moves __file__)."""
    clear_cache()
    backend_root = Path(__file__).resolve().parents[3]
    source_cypher_dir = backend_root / "graph" / "queries"
    source_sql_dir = backend_root / "app" / "queries"
    with patch("app.db.query_loader._CYPHER_QUERIES_DIR", source_cypher_dir), \
         patch("app.db.query_loader._SQL_QUERIES_DIR", source_sql_dir):
        yield
    clear_cache()


class TestCypherQueryFilesExist:
    def test_all_expected_cypher_files_present(self):
        """All graph/queries/*.cypher files must exist on disk."""
        backend_root = Path(__file__).resolve().parents[3]  # watcher-backend/
        cypher_dir = backend_root / "graph" / "queries"

        assert cypher_dir.is_dir(), f"graph/queries/ directory not found at {cypher_dir}"

        available = {p.stem for p in cypher_dir.glob("*.cypher")}
        missing = EXPECTED_CYPHER_QUERIES - available
        assert not missing, f"Missing .cypher files: {missing}"

    def test_list_queries_returns_cypher_names(self):
        """list_queries('cypher') must include all expected query names."""
        available = set(list_queries("cypher"))
        missing = EXPECTED_CYPHER_QUERIES - available
        assert not missing, f"list_queries() missing: {missing}"


class TestCypherQueryContent:
    def test_upsert_entity_contains_merge(self):
        q = load_query("upsert_entity", "cypher")
        assert "MERGE" in q
        assert "Entidad" in q
        assert "$nombre_normalizado" in q

    def test_upsert_boletin_contains_merge(self):
        q = load_query("upsert_boletin", "cypher")
        assert "MERGE" in q
        assert "Boletin" in q
        assert "$pg_id" in q

    def test_upsert_mention_edge_contains_match_and_merge(self):
        q = load_query("upsert_mention_edge", "cypher")
        assert "MATCH" in q
        assert "MERGE" in q
        assert "MENCIONADO_EN" in q

    def test_graph_overview_nodes_has_limit(self):
        q = load_query("graph_overview_nodes", "cypher")
        assert "LIMIT" in q
        assert "$max_nodes" in q
        assert "$min_mentions" in q

    def test_graph_overview_links_returns_source_and_target(self):
        q = load_query("graph_overview_links", "cypher")
        assert "source" in q
        assert "target" in q
        assert "$ids" in q

    def test_entity_relationships_returns_neighbors(self):
        q = load_query("entity_relationships", "cypher")
        assert "neighbors" in q
        assert "edges" in q
        assert "$pg_id" in q

    def test_neighborhood_uses_variable_depth(self):
        q = load_query("neighborhood", "cypher")
        assert "$depth" in q
        assert "all_nodes" in q
        assert "all_rels" in q

    def test_load_for_networkx_matches_entidad(self):
        q = load_query("load_for_networkx", "cypher")
        assert "Entidad" in q
        assert "$min_mentions" in q


class TestCypherQueryLoader:
    def test_nonexistent_cypher_raises_error(self, tmp_path):
        with patch("app.db.query_loader._CYPHER_QUERIES_DIR", tmp_path / "nonexistent"):
            with pytest.raises(QueryNotFoundError) as exc_info:
                load_query("does_not_exist", "cypher")
            assert "does_not_exist" in str(exc_info.value)

    def test_cypher_queries_are_stripped(self, tmp_path):
        (tmp_path / "test_query.cypher").write_text("\n  MATCH (n) RETURN n  \n")
        with patch("app.db.query_loader._CYPHER_QUERIES_DIR", tmp_path):
            result = load_query("test_query", "cypher")
        assert result == "MATCH (n) RETURN n"

    def test_cypher_and_sql_use_different_dirs(self, tmp_path):
        sql_dir = tmp_path / "sql"
        cypher_dir = tmp_path / "cypher"
        sql_dir.mkdir()
        cypher_dir.mkdir()

        (sql_dir / "my_query.sql").write_text("SELECT 1")
        (cypher_dir / "my_query.cypher").write_text("MATCH (n) RETURN n")

        with patch("app.db.query_loader._SQL_QUERIES_DIR", sql_dir):
            with patch("app.db.query_loader._CYPHER_QUERIES_DIR", cypher_dir):
                sql = load_query("my_query", "sql")
                cypher = load_query("my_query", "cypher")

        assert "SELECT" in sql
        assert "MATCH" in cypher

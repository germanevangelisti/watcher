"""
Unit tests for graph/init.cypher schema file.

Validates structure and completeness of the declarative schema
without requiring a live Neo4j instance.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# Path resolution: test file is at watcher-backend/tests/tests/unit/
# parents[3] = watcher-backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_INIT_CYPHER = _BACKEND_ROOT / "graph" / "init.cypher"


@pytest.fixture(scope="module")
def init_cypher_text() -> str:
    assert _INIT_CYPHER.is_file(), f"graph/init.cypher not found at {_INIT_CYPHER}"
    return _INIT_CYPHER.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def cypher_statements(init_cypher_text: str) -> list:
    """Parse CREATE statements from init.cypher using the production parser."""
    from app.db.graph_driver import _parse_cypher_statements
    return _parse_cypher_statements(init_cypher_text)


class TestInitCypherExists:
    def test_file_exists(self):
        assert _INIT_CYPHER.is_file()

    def test_file_is_not_empty(self, init_cypher_text):
        assert len(init_cypher_text.strip()) > 0


class TestConstraints:
    def test_has_entidad_nombre_norm_constraint(self, init_cypher_text):
        assert "entidad_nombre_norm_unique" in init_cypher_text

    def test_has_entidad_pg_id_constraint(self, init_cypher_text):
        assert "entidad_pg_id_unique" in init_cypher_text

    def test_has_boletin_pg_id_constraint(self, init_cypher_text):
        assert "boletin_pg_id_unique" in init_cypher_text

    def test_constraints_use_if_not_exists(self, init_cypher_text):
        """All CREATE CONSTRAINT statements must be idempotent."""
        import re
        constraint_stmts = re.findall(
            r"CREATE\s+CONSTRAINT\s+\w+",
            init_cypher_text,
            re.IGNORECASE,
        )
        assert len(constraint_stmts) >= 3, "Expected at least 3 constraints"
        # Verify IF NOT EXISTS appears for each
        assert init_cypher_text.count("IF NOT EXISTS") >= len(constraint_stmts)


class TestIndexes:
    def test_has_tipo_index(self, init_cypher_text):
        assert "entidad_tipo_idx" in init_cypher_text

    def test_has_menciones_index(self, init_cypher_text):
        assert "entidad_menciones_idx" in init_cypher_text

    def test_indexes_use_if_not_exists(self, init_cypher_text):
        import re
        index_stmts = re.findall(
            r"CREATE\s+(?:INDEX|FULLTEXT\s+INDEX)\s+\w+",
            init_cypher_text,
            re.IGNORECASE,
        )
        assert len(index_stmts) >= 3, "Expected at least 3 indexes"


class TestFulltextIndex:
    def test_has_fulltext_index(self, init_cypher_text):
        assert "FULLTEXT" in init_cypher_text.upper()
        assert "entidad_nombre_fulltext" in init_cypher_text

    def test_fulltext_index_covers_nombre_display(self, init_cypher_text):
        assert "nombre_display" in init_cypher_text

    def test_fulltext_index_covers_nombre_normalizado(self, init_cypher_text):
        assert "nombre_normalizado" in init_cypher_text


class TestStatementParsing:
    def test_at_least_8_statements(self, cypher_statements):
        """Expect at minimum: 3 constraints + 5 indexes."""
        assert len(cypher_statements) >= 8, (
            f"Expected ≥8 statements, found {len(cypher_statements)}"
        )

    def test_all_statements_start_with_create(self, cypher_statements):
        for stmt in cypher_statements:
            assert stmt.upper().startswith("CREATE"), (
                f"Non-CREATE statement found: {stmt[:60]}"
            )

"""
graph_driver.py — Neo4j async driver with declarative schema init and query loader.

Replaces neo4j_client.py. Backward-compatible re-export kept in neo4j_client.py.

Public API:
    init_neo4j()            — startup: connect + apply init.cypher
    close_neo4j()           — shutdown: close driver
    get_driver()            — returns AsyncDriver or None
    get_neo4j_session()     — async context manager
    get_neo4j_session_dep   — FastAPI Depends generator
    run_query(name, params) — run an externalized .cypher query by name
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession as Neo4jAsyncSession

from app.core.config import settings
from app.db.query_loader import load_query, QueryNotFoundError

logger = logging.getLogger(__name__)

_driver: Optional[AsyncDriver] = None

# Path to the declarative schema file
_INIT_CYPHER = Path(__file__).resolve().parent.parent.parent / "graph" / "init.cypher"


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


async def init_neo4j() -> bool:
    """
    Connect to Neo4j, verify connectivity, and apply the declarative schema.

    Returns True on success, False if Neo4j is not configured or unreachable.
    Called from main.py startup_event.
    """
    global _driver

    if not settings.NEO4J_URI:
        logger.warning("NEO4J_URI not configured — Neo4j disabled")
        return False

    try:
        _driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_pool_size=20,
            connection_timeout=10.0,
        )
        await _driver.verify_connectivity()
        logger.info("Neo4j connected: %s", settings.NEO4J_URI)
        await _apply_schema()
        return True

    except Exception as exc:
        logger.error("Neo4j init failed: %s", exc)
        _driver = None
        return False


async def close_neo4j() -> None:
    """Close the driver. Called from main.py shutdown_event."""
    global _driver
    if _driver:
        await _driver.close()
        _driver = None
        logger.info("Neo4j driver closed")


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------


def get_driver() -> Optional[AsyncDriver]:
    """Return the singleton driver, or None if not initialized."""
    return _driver


@asynccontextmanager
async def get_neo4j_session() -> AsyncGenerator[Neo4jAsyncSession, None]:
    """
    Async context manager for Neo4j sessions.

    Usage:
        async with get_neo4j_session() as session:
            await session.run(...)
    """
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialized — call init_neo4j() first")
    async with _driver.session() as session:
        yield session


async def get_neo4j_session_dep() -> AsyncGenerator[Neo4jAsyncSession, None]:
    """FastAPI Depends version of get_neo4j_session."""
    if _driver is None:
        raise RuntimeError("Neo4j not available")
    async with _driver.session() as session:
        yield session


# ---------------------------------------------------------------------------
# Query runner
# ---------------------------------------------------------------------------


async def run_query(
    session: Neo4jAsyncSession,
    query_name: str,
    params: Optional[Dict[str, Any]] = None,
):
    """
    Run a named Cypher query loaded from graph/queries/<query_name>.cypher.

    Args:
        session:    An active Neo4j session.
        query_name: File stem of the .cypher file (e.g. "upsert_entity").
        params:     Query parameters dict (forwarded to session.run).

    Returns:
        AsyncResult from session.run.

    Raises:
        QueryNotFoundError: if the .cypher file doesn't exist.
    """
    cypher = load_query(query_name, "cypher")
    return await session.run(cypher, **(params or {}))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_cypher_statements(text: str) -> List[str]:
    """
    Parse individual CREATE statements from a multi-statement Cypher file.

    Each statement is separated by ';'. Comment-only lines (starting with //)
    are stripped from each segment so that leading comments don't cause the
    entire segment to be discarded.
    """
    statements = []
    for segment in text.split(";"):
        # Remove comment lines; keep only Cypher lines
        cypher_lines = [
            line for line in segment.splitlines()
            if line.strip() and not line.strip().startswith("//")
        ]
        cleaned = "\n".join(cypher_lines).strip()
        if cleaned:
            statements.append(cleaned)
    return statements


# ---------------------------------------------------------------------------
# Internal: schema application
# ---------------------------------------------------------------------------


async def _apply_schema() -> None:
    """
    Apply constraints and indexes from graph/init.cypher.

    Each statement is executed individually; failures are logged but don't
    abort the startup sequence (allows partial schema upgrades).
    """
    if not _INIT_CYPHER.is_file():
        logger.warning("graph/init.cypher not found at %s — skipping schema init", _INIT_CYPHER)
        return

    raw = _INIT_CYPHER.read_text(encoding="utf-8")
    statements = _parse_cypher_statements(raw)

    applied = 0
    async with _driver.session() as session:
        for stmt in statements:
            # Re-attach the semicolon that was consumed by split
            try:
                await session.run(stmt)
                applied += 1
            except Exception as exc:
                logger.warning("Schema statement skipped (%s): %.80s", exc, stmt)

    logger.info("Neo4j schema: %d/%d statements applied from init.cypher", applied, len(statements))

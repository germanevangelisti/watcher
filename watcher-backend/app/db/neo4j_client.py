"""
neo4j_client.py — Backward-compatible re-export shim.

The canonical implementation is now app.db.graph_driver.
Existing imports of `from app.db.neo4j_client import ...` continue to work.
"""

from app.db.graph_driver import (  # noqa: F401
    init_neo4j,
    close_neo4j,
    get_driver,
    get_neo4j_session,
    get_neo4j_session_dep,
    run_query,
)

__all__ = [
    "init_neo4j",
    "close_neo4j",
    "get_driver",
    "get_neo4j_session",
    "get_neo4j_session_dep",
    "run_query",
]

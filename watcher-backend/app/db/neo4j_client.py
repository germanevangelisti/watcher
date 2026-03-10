"""
Neo4j async driver — singleton client para la base de datos de grafos.

Expone:
  init_neo4j()          — llamar en startup_event
  close_neo4j()         — llamar en shutdown_event
  get_driver()          — retorna el driver o None
  get_neo4j_session()   — async context manager para sesiones
  get_neo4j_session_dep — FastAPI dependency
"""

import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession as Neo4jAsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

_driver: Optional[AsyncDriver] = None


async def init_neo4j() -> bool:
    """
    Inicializa el driver async de Neo4j y aplica constraints de schema.
    Retorna True si tuvo éxito, False si Neo4j no está disponible.
    Llamar desde main.py startup_event.
    """
    global _driver
    if not settings.NEO4J_URI:
        logger.warning("NEO4J_URI no configurado — Neo4j deshabilitado")
        return False

    try:
        _driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_pool_size=20,
            connection_timeout=10.0,
        )
        await _driver.verify_connectivity()
        logger.info("Neo4j conectado: %s", settings.NEO4J_URI)
        await _create_schema_constraints()
        return True
    except Exception as exc:
        logger.error("Neo4j inicialización fallida: %s", exc)
        _driver = None
        return False


async def close_neo4j() -> None:
    """Cierra el driver. Llamar desde main.py shutdown_event."""
    global _driver
    if _driver:
        await _driver.close()
        _driver = None
        logger.info("Neo4j driver cerrado")


def get_driver() -> Optional[AsyncDriver]:
    """Retorna el driver singleton, o None si no fue inicializado."""
    return _driver


@asynccontextmanager
async def get_neo4j_session() -> AsyncGenerator[Neo4jAsyncSession, None]:
    """
    Async context manager para sesiones Neo4j.

    Uso:
        async with get_neo4j_session() as session:
            await session.run(...)
    """
    if _driver is None:
        raise RuntimeError("Neo4j driver no inicializado")
    async with _driver.session() as session:
        yield session


async def get_neo4j_session_dep() -> AsyncGenerator[Neo4jAsyncSession, None]:
    """
    Versión FastAPI Depends de get_neo4j_session.

    Uso en endpoint:
        session: Neo4jAsyncSession = Depends(get_neo4j_session_dep)
    """
    if _driver is None:
        raise RuntimeError("Neo4j no disponible")
    async with _driver.session() as session:
        yield session


async def _create_schema_constraints() -> None:
    """Aplica constraints e índices idempotentes. Se ejecuta en cada startup."""
    statements = [
        "CREATE CONSTRAINT entidad_nombre_norm_unique IF NOT EXISTS "
        "FOR (e:Entidad) REQUIRE e.nombre_normalizado IS UNIQUE",

        "CREATE CONSTRAINT entidad_pg_id_unique IF NOT EXISTS "
        "FOR (e:Entidad) REQUIRE e.pg_id IS UNIQUE",

        "CREATE CONSTRAINT boletin_pg_id_unique IF NOT EXISTS "
        "FOR (b:Boletin) REQUIRE b.pg_id IS UNIQUE",

        "CREATE INDEX entidad_tipo_idx IF NOT EXISTS "
        "FOR (e:Entidad) ON (e.tipo)",

        "CREATE INDEX entidad_menciones_idx IF NOT EXISTS "
        "FOR (e:Entidad) ON (e.total_menciones)",
    ]
    async with _driver.session() as session:
        for stmt in statements:
            await session.run(stmt)
    logger.info("Neo4j schema constraints aplicados")

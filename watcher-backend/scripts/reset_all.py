#!/usr/bin/env python3
"""
Reset completo: borra todos los nodos de Neo4j + tablas de entidades/boletines en PostgreSQL.
Uso: python3 scripts/reset_all.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.database import AsyncSessionLocal
from app.db.neo4j_client import init_neo4j, close_neo4j, get_neo4j_session
from app.core.config import settings

TABLES = [
    # Dependientes primero (FK children)
    "chunk_records",
    "menciones_entidades",
    "relaciones_entidades",
    "entidades_extraidas",
    "analysis_results",
    "analysis_executions",
    "check_results",
    "evidences",
    "agent_tasks",
    "workflow_logs",
    "agent_workflows",
    "analysis_comparisons",
    "red_flags",
    "analisis",
    "actos_administrativos",
    "vinculos_acto_presupuesto",
    "procesamiento_batch",
    "boletin_documents",
    "sumarios_parseados",
    "boletines",
]


async def reset_postgres():
    print("--- PostgreSQL ---")
    async with AsyncSessionLocal() as db:
        for table in TABLES:
            result = await db.execute(text(f"DELETE FROM {table}"))
            print(f"  {table}: {result.rowcount} filas eliminadas")
        await db.commit()
    print("PostgreSQL limpio.\n")


async def reset_neo4j():
    print("--- Neo4j ---")
    if not settings.NEO4J_URI:
        print("  NEO4J_URI no configurado — saltando.")
        return
    ok = await init_neo4j()
    if not ok:
        print("  No se pudo conectar a Neo4j.")
        return
    async with get_neo4j_session() as session:
        result = await session.run("MATCH (n) DETACH DELETE n")
        summary = await result.consume()
        print(f"  Nodos eliminados: {summary.counters.nodes_deleted}")
        print(f"  Relaciones eliminadas: {summary.counters.relationships_deleted}")
    await close_neo4j()
    print("Neo4j limpio.\n")


async def main():
    print("=== RESET COMPLETO ===\n")
    await reset_neo4j()
    await reset_postgres()
    print("=== LISTO ===")


asyncio.run(main())

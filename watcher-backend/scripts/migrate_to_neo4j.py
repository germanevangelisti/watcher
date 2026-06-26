#!/usr/bin/env python3
"""
Migración one-time: grafo de conocimiento PostgreSQL → Neo4j.

Ejecutar DESPUÉS de que Neo4j esté healthy y el backend haya aplicado
los constraints de schema (vía init_neo4j en startup).

Uso (desde watcher-backend/):
    python scripts/migrate_to_neo4j.py --dry-run
    python scripts/migrate_to_neo4j.py --batch-size 200
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos de la app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models import EntidadExtraida, RelacionEntidad, MencionEntidad, Boletin
from app.db.neo4j_client import init_neo4j, close_neo4j, get_neo4j_session
from app.services.graph_service import (
    upsert_entity, upsert_boletin, upsert_relationship, upsert_mention_edge,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("migrate_to_neo4j")


async def migrate_entities(batch_size: int, dry_run: bool) -> int:
    count = 0
    async with AsyncSessionLocal() as pg:
        offset = 0
        while True:
            result = await pg.execute(
                select(EntidadExtraida)
                .order_by(EntidadExtraida.id)
                .offset(offset)
                .limit(batch_size)
            )
            rows = result.scalars().all()
            if not rows:
                break

            if not dry_run:
                async with get_neo4j_session() as neo:
                    for e in rows:
                        await upsert_entity(
                            neo,
                            pg_id=e.id,
                            tipo=e.tipo,
                            nombre_normalizado=e.nombre_normalizado,
                            nombre_display=e.nombre_display,
                            variantes=e.variantes or [],
                            total_menciones=e.total_menciones,
                            primera_aparicion=e.primera_aparicion.isoformat() if e.primera_aparicion else None,
                            ultima_aparicion=e.ultima_aparicion.isoformat() if e.ultima_aparicion else None,
                            metadata_extra=e.metadata_extra,
                        )

            count += len(rows)
            logger.info("Entidades migradas: %d", count)
            offset += batch_size
    return count


async def migrate_boletines(batch_size: int, dry_run: bool) -> int:
    count = 0
    async with AsyncSessionLocal() as pg:
        offset = 0
        while True:
            result = await pg.execute(
                select(Boletin)
                .order_by(Boletin.id)
                .offset(offset)
                .limit(batch_size)
            )
            rows = result.scalars().all()
            if not rows:
                break

            if not dry_run:
                async with get_neo4j_session() as neo:
                    for b in rows:
                        await upsert_boletin(
                            neo,
                            pg_id=b.id,
                            filename=b.filename,
                            date=b.date,
                        )

            count += len(rows)
            logger.info("Boletines migrados: %d", count)
            offset += batch_size
    return count


async def migrate_relationships(batch_size: int, dry_run: bool) -> int:
    count = 0
    async with AsyncSessionLocal() as pg:
        offset = 0
        while True:
            # Join para traer nombre_normalizado del origen
            result = await pg.execute(
                select(
                    RelacionEntidad,
                    EntidadExtraida.nombre_normalizado.label("origen_norm"),
                )
                .join(EntidadExtraida, RelacionEntidad.entidad_origen_id == EntidadExtraida.id)
                .order_by(RelacionEntidad.id)
                .offset(offset)
                .limit(batch_size)
            )
            rows = result.all()
            if not rows:
                break

            # Traer nombre_normalizado de destinos en batch
            destino_ids = [r.RelacionEntidad.entidad_destino_id for r in rows]
            dest_result = await pg.execute(
                select(EntidadExtraida.id, EntidadExtraida.nombre_normalizado)
                .where(EntidadExtraida.id.in_(destino_ids))
            )
            dest_map = {row.id: row.nombre_normalizado for row in dest_result.all()}

            if not dry_run:
                async with get_neo4j_session() as neo:
                    for row in rows:
                        rel = row.RelacionEntidad
                        destino_norm = dest_map.get(rel.entidad_destino_id)
                        if not destino_norm:
                            continue
                        await upsert_relationship(
                            neo,
                            origen_nombre_normalizado=row.origen_norm,
                            destino_nombre_normalizado=destino_norm,
                            tipo_relacion=rel.tipo_relacion,
                            pg_id=rel.id,
                            boletin_pg_id=rel.boletin_id,
                            fecha=rel.fecha_relacion.isoformat(),
                            confianza=rel.confianza,
                            contexto=rel.contexto,
                            metadata_extra=rel.metadata_extra,
                        )

            count += len(rows)
            logger.info("Relaciones migradas: %d", count)
            offset += batch_size
    return count


async def migrate_mentions(batch_size: int, dry_run: bool) -> int:
    count = 0
    async with AsyncSessionLocal() as pg:
        offset = 0
        while True:
            result = await pg.execute(
                select(
                    MencionEntidad,
                    EntidadExtraida.nombre_normalizado.label("entidad_norm"),
                )
                .join(EntidadExtraida, MencionEntidad.entidad_id == EntidadExtraida.id)
                .order_by(MencionEntidad.id)
                .offset(offset)
                .limit(batch_size)
            )
            rows = result.all()
            if not rows:
                break

            if not dry_run:
                async with get_neo4j_session() as neo:
                    for row in rows:
                        m = row.MencionEntidad
                        await upsert_mention_edge(
                            neo,
                            entidad_nombre_normalizado=row.entidad_norm,
                            boletin_pg_id=m.boletin_id,
                            pg_id=m.id,
                            fragmento=m.fragmento or "",
                            confianza=m.confianza or 0.8,
                        )

            count += len(rows)
            logger.info("Menciones migradas: %d", count)
            offset += batch_size
    return count


async def main(batch_size: int, dry_run: bool) -> None:
    logger.info("=== Migración Neo4j %s===", "[DRY RUN] " if dry_run else "")

    if not dry_run:
        ok = await init_neo4j()
        if not ok:
            logger.error("No se pudo conectar a Neo4j. Abortando.")
            sys.exit(1)
    else:
        logger.info("Dry run: verificando conectividad PostgreSQL...")

    n_entities = await migrate_entities(batch_size, dry_run)
    n_boletines = await migrate_boletines(batch_size, dry_run)
    n_relationships = await migrate_relationships(batch_size, dry_run)
    n_mentions = await migrate_mentions(batch_size, dry_run)

    logger.info(
        "Migración completa: %d entidades, %d boletines, %d relaciones, %d menciones",
        n_entities, n_boletines, n_relationships, n_mentions,
    )

    if not dry_run:
        await close_neo4j()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrar grafo de conocimiento a Neo4j")
    parser.add_argument("--batch-size", type=int, default=200, help="Tamaño del batch")
    parser.add_argument("--dry-run", action="store_true", help="Solo contar, no escribir")
    args = parser.parse_args()
    asyncio.run(main(args.batch_size, args.dry_run))

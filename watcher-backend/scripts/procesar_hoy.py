#!/usr/bin/env python3
"""
Procesa los boletines oficiales de HOY para todas las secciones.

Flujo:
  1. Construye filenames para hoy (YYYYMMDD_1_Secc.pdf ... YYYYMMDD_5_Secc.pdf)
  2. Crea/reutiliza registros Boletin en PostgreSQL
  3. Corre el pipeline completo para cada uno (extracción + NLP + Neo4j dual-write)

Uso:
    python3 scripts/procesar_hoy.py
    python3 scripts/procesar_hoy.py --fecha 20260308        # fecha específica
    python3 scripts/procesar_hoy.py --secciones 1 2         # solo ciertas secciones
    python3 scripts/procesar_hoy.py --jurisdiccion 1        # Córdoba Provincial (default)
"""

import asyncio
import argparse
import logging
import uuid
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models import Boletin, FuenteDato
from app.services.url_fetcher import build_url_cordoba_provincial, build_url_from_template
from app.db.neo4j_client import init_neo4j, close_neo4j
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("procesar_hoy")

SECTION_NAMES = {
    "1": "Designaciones y Decretos",
    "2": "Compras y Contrataciones",
    "3": "Subsidios y Transferencias",
    "4": "Obras Públicas",
    "5": "Notificaciones Judiciales",
}


async def get_url_template(jurisdiccion_id: int) -> str | None:
    """Busca el url_template activo de FuenteDato para la jurisdicción."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(FuenteDato).where(
                FuenteDato.jurisdiccion_id == jurisdiccion_id,
                FuenteDato.tipo == "boletin_diario",
                FuenteDato.activa == True,
            )
        )
        fuente = result.scalar_one_or_none()
        return fuente.url_template if fuente else None


async def upsert_boletin(filename: str, fecha: str, section: str, source_url: str, jurisdiccion_id: int) -> int:
    """Crea o reutiliza un Boletin. Retorna su ID."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Boletin).where(Boletin.filename == filename))
        boletin = result.scalar_one_or_none()

        if boletin is None:
            boletin = Boletin(
                filename=filename,
                date=fecha,
                section=section,
                seccion_nombre=SECTION_NAMES.get(section),
                status="pending",
                jurisdiccion_id=jurisdiccion_id,
                source_url=source_url,
            )
            db.add(boletin)
            await db.flush()
            await db.commit()
            logger.info("  Boletin creado: id=%d  %s", boletin.id, filename)
        elif boletin.status == "completed":
            logger.info("  Boletin ya procesado: id=%d  %s — saltando", boletin.id, filename)
            return -1  # señal de "skip"
        else:
            logger.info("  Boletin existente (status=%s): id=%d  %s — reprocesando", boletin.status, boletin.id, filename)
            boletin.status = "pending"
            if not boletin.source_url:
                boletin.source_url = source_url
            await db.commit()

        return boletin.id


async def run_pipeline(boletin_id: int, filename: str) -> bool:
    """Importa y corre el pipeline directamente. Retorna True si completó sin error."""
    from app.api.v1.endpoints.pipeline import _process_document_pipeline
    from app.db.database import BackgroundSessionLocal
    from app.schemas.pipeline import PipelineConfig
    from sqlalchemy import select as _select

    session_id = str(uuid.uuid4())[:8]
    logger.info("  Pipeline iniciado: session=%s  boletin_id=%d", session_id, boletin_id)

    await _process_document_pipeline(boletin_id, filename, session_id, PipelineConfig())

    # Verificar estado real en DB
    async with BackgroundSessionLocal() as db:
        result = await db.execute(_select(Boletin).where(Boletin.id == boletin_id))
        boletin = result.scalar_one_or_none()
        status = boletin.status if boletin else "unknown"

    if status == "completed":
        logger.info("  OK — boletin_id=%d status=completed", boletin_id)
        return True
    else:
        logger.error("  FALLÓ — boletin_id=%d status=%s", boletin_id, status)
        return False


async def main(fecha_str: str, secciones: list[str], jurisdiccion_id: int):
    logger.info("=== Procesando boletines del %s ===", fecha_str)
    logger.info("Secciones: %s  |  Jurisdiccion: %d", secciones, jurisdiccion_id)

    # Inicializar Neo4j para que el dual-write funcione
    if settings.NEO4J_URI:
        neo4j_ok = await init_neo4j()
        if neo4j_ok:
            logger.info("Neo4j conectado — dual-write activo")
        else:
            logger.warning("Neo4j no disponible — se procesará solo en PostgreSQL")
    else:
        logger.warning("NEO4J_URI no configurado — solo PostgreSQL")

    # Obtener URL template (fallback a función hardcodeada de Córdoba)
    url_template = await get_url_template(jurisdiccion_id)
    if url_template:
        logger.info("Usando url_template de FuenteDato: %s", url_template[:60])
    else:
        logger.info("Sin FuenteDato — usando build_url_cordoba_provincial")

    results = {"ok": 0, "skip": 0, "error": 0}

    for section in secciones:
        filename = f"{fecha_str}_{section}_Secc.pdf"
        logger.info("\n[Sección %s — %s]", section, SECTION_NAMES.get(section, "?"))
        logger.info("  Filename: %s", filename)

        # Construir URL
        try:
            if url_template:
                source_url = build_url_from_template(url_template, filename)
            else:
                source_url = build_url_cordoba_provincial(filename)
            logger.info("  URL: %s", source_url)
        except Exception as e:
            logger.error("  Error construyendo URL: %s", e)
            results["error"] += 1
            continue

        # Crear/obtener boletin
        try:
            boletin_id = await upsert_boletin(filename, fecha_str, section, source_url, jurisdiccion_id)
        except Exception as e:
            logger.error("  Error creando boletin en DB: %s", e)
            results["error"] += 1
            continue

        if boletin_id == -1:
            results["skip"] += 1
            continue

        # Correr pipeline
        try:
            ok = await run_pipeline(boletin_id, filename)
            if ok:
                results["ok"] += 1
            else:
                results["error"] += 1
        except Exception as e:
            logger.error("  Pipeline falló para %s: %s", filename, e, exc_info=True)
            results["error"] += 1

    await close_neo4j()

    logger.info("\n=== RESUMEN ===")
    logger.info("  Procesados: %d", results["ok"])
    logger.info("  Saltados (ya completos): %d", results["skip"])
    logger.info("  Errores: %d", results["error"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procesa boletines del día")
    parser.add_argument(
        "--fecha",
        default=date.today().strftime("%Y%m%d"),
        help="Fecha en formato YYYYMMDD (default: hoy)",
    )
    parser.add_argument(
        "--secciones",
        nargs="+",
        default=["1", "2", "3", "4", "5"],
        help="Secciones a procesar (default: 1 2 3 4 5)",
    )
    parser.add_argument(
        "--jurisdiccion",
        type=int,
        default=1,
        help="ID de jurisdiccion (default: 1 = Córdoba Provincial)",
    )
    args = parser.parse_args()

    asyncio.run(main(args.fecha, args.secciones, args.jurisdiccion))

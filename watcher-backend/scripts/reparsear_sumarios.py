#!/usr/bin/env python3
"""
Backfill: parsea el sumario de los boletines provinciales de Córdoba ya procesados
y persiste los resultados en la tabla sumarios_parseados.

Usa el PDF original (no el .txt) para tener separación real de páginas.
Si el PDF no se encuentra, intenta con el .txt como fallback.

Uso:
    python scripts/reparsear_sumarios.py                  # Procesar todos
    python scripts/reparsear_sumarios.py --dry-run        # Solo contar, sin escribir
    python scripts/reparsear_sumarios.py --year 2025      # Filtrar por año
    python scripts/reparsear_sumarios.py --limit 50       # Procesar solo N
    python scripts/reparsear_sumarios.py --format-stats   # Mostrar distribución de formatos
"""

import asyncio
import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime
from typing import Optional

# Añadir raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models import Boletin, FuenteBoletin, SumarioParseado
from app.core.config import settings
from app.services.sumario_parser import SumarioParser


BATCH_SIZE = 100


def _find_pdf(filename: str) -> Optional[Path]:
    """Busca el PDF en los directorios conocidos."""
    if len(filename) >= 8:
        year = filename[:4]
        month = filename[4:6]
        candidate = settings.BOLETINES_DIR / year / month / filename
        if candidate.exists():
            return candidate
        matches = list(settings.BOLETINES_DIR.rglob(filename))
        if matches:
            return matches[0]
    return None


def _find_txt(filename: str) -> Optional[Path]:
    """Busca el .txt pre-extraído como fallback."""
    txt_name = filename.replace(".pdf", ".txt")
    txt_path = settings.DATA_DIR / "processed" / txt_name
    return txt_path if txt_path.exists() else None


async def _get_text_for_boletin(filename: str) -> Optional[str]:
    """
    Obtiene el texto del boletín para parseo de sumario.
    Prefiere el PDF (páginas reales); fallback al .txt pre-extraído.
    """
    # Intentar PDF primero para tener separación de páginas
    pdf_path = _find_pdf(filename)
    if pdf_path:
        try:
            from app.services.extractors.registry import ExtractorRegistry
            content = await ExtractorRegistry.extract(pdf_path, method="pdfplumber")
            if content.success and content.pages:
                # Retornar solo las primeras 3 páginas concatenadas
                text = "\n\n".join(p.text for p in content.pages[:3] if p.text)
                return text
        except Exception:
            pass  # Fallback al .txt

    # Fallback: .txt pre-extraído
    txt_path = _find_txt(filename)
    if txt_path:
        try:
            return txt_path.read_text(encoding="utf-8", errors="replace")[:8000]
        except Exception:
            pass

    return None


async def run_backfill(
    year: Optional[str] = None,
    limit: Optional[int] = None,
    dry_run: bool = False,
    format_stats: bool = False,
):
    parser = SumarioParser()
    stats = {
        "total": 0,
        "procesados": 0,
        "saltados_ya_existentes": 0,
        "sin_texto": 0,
        "fallidos": 0,
        "not_found": 0,
        "found": 0,
    }
    format_counter: Counter = Counter()

    print("=" * 70)
    print("  BACKFILL: PARSEO DE SUMARIOS DE BOLETINES PROVINCIALES")
    if dry_run:
        print("  [DRY RUN — sin escritura en DB]")
    print("=" * 70)
    t_inicio = datetime.now()

    async with AsyncSessionLocal() as db:
        # Query: boletines provinciales de Córdoba ya procesados
        query = (
            select(Boletin)
            .where(Boletin.fuente == FuenteBoletin.PROVINCIAL)
            .where(Boletin.jurisdiccion_id == 1)
            .where(Boletin.status == "completed")
            .order_by(Boletin.date.desc())
        )
        if year:
            query = query.where(Boletin.date.like(f"{year}%"))
            print(f"Filtro: año {year}")
        if limit:
            query = query.limit(limit)
            print(f"Límite: {limit}")

        result = await db.execute(query)
        boletines = result.scalars().all()
        stats["total"] = len(boletines)
        print(f"Boletines a procesar: {stats['total']}\n")

        if not boletines:
            print("No hay boletines que procesar.")
            return

        for i, boletin in enumerate(boletines, 1):
            # Verificar si ya tiene sumario
            existing = await db.execute(
                select(SumarioParseado.id).where(SumarioParseado.boletin_id == boletin.id)
            )
            if existing.first():
                stats["saltados_ya_existentes"] += 1
                continue

            text = await _get_text_for_boletin(boletin.filename)
            if not text:
                stats["sin_texto"] += 1
                if i % 50 == 0 or i == stats["total"]:
                    print(f"[{i}/{stats['total']}] ⚠ Sin texto: {boletin.filename}")
                continue

            try:
                sumario = parser.parse_from_text(text)
                format_counter[sumario.format_type] += 1

                if sumario.found:
                    stats["found"] += 1
                else:
                    stats["not_found"] += 1

                if not dry_run:
                    record = SumarioParseado(
                        boletin_id=boletin.id,
                        format_type=sumario.format_type,
                        confidence=sumario.confidence,
                        pagina_sumario=sumario.sumario_page,
                        entries_json=json.dumps(
                            [e.__dict__ for e in sumario.entries],
                            ensure_ascii=False,
                        ),
                        raw_text=sumario.raw_text if sumario.found else None,
                    )
                    db.add(record)

                stats["procesados"] += 1

                if i % BATCH_SIZE == 0:
                    if not dry_run:
                        await db.commit()
                    elapsed = (datetime.now() - t_inicio).total_seconds()
                    rate = i / elapsed if elapsed > 0 else 0
                    pct_found = stats["found"] / max(stats["procesados"], 1) * 100
                    print(
                        f"[{i}/{stats['total']}] {rate:.1f} bol/s — "
                        f"encontrados: {stats['found']} ({pct_found:.0f}%)"
                    )

            except Exception as exc:
                stats["fallidos"] += 1
                print(f"[{i}/{stats['total']}] ✗ Error {boletin.filename}: {exc}")

        # Commit final
        if not dry_run and stats["procesados"] > 0:
            await db.commit()

    # Resumen final
    elapsed = (datetime.now() - t_inicio).total_seconds()
    print("\n" + "=" * 70)
    print("  RESUMEN")
    print("=" * 70)
    print(f"  Total boletines consultados : {stats['total']}")
    print(f"  Procesados                  : {stats['procesados']}")
    print(f"    ✓ Sumario encontrado       : {stats['found']}")
    print(f"    ✗ Sumario no encontrado    : {stats['not_found']}")
    print(f"  Saltados (ya existían)       : {stats['saltados_ya_existentes']}")
    print(f"  Sin texto disponible         : {stats['sin_texto']}")
    print(f"  Fallidos (error)             : {stats['fallidos']}")
    print(f"  Tiempo total                 : {elapsed:.1f}s")
    if stats["procesados"] > 0:
        pct = stats["found"] / stats["procesados"] * 100
        print(f"  Cobertura de sumarios       : {pct:.1f}%")

    if format_stats and format_counter:
        print("\n  Distribución por formato:")
        for fmt, count in format_counter.most_common():
            print(f"    {fmt:<30} {count}")

    if dry_run:
        print("\n  [DRY RUN — nada fue escrito en la DB]")
    print("=" * 70)


def main():
    ap = argparse.ArgumentParser(description="Backfill de sumarios para boletines provinciales")
    ap.add_argument("--year", help="Filtrar por año (ej: 2025)")
    ap.add_argument("--limit", type=int, help="Procesar solo N boletines")
    ap.add_argument("--dry-run", action="store_true", help="No escribir en DB")
    ap.add_argument("--format-stats", action="store_true", help="Mostrar distribución de formatos al final")
    args = ap.parse_args()

    asyncio.run(run_backfill(
        year=args.year,
        limit=args.limit,
        dry_run=args.dry_run,
        format_stats=args.format_stats,
    ))


if __name__ == "__main__":
    main()

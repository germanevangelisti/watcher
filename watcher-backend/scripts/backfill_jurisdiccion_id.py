#!/usr/bin/env python3
"""
Backfill `boletines.jurisdiccion_id` para las filas que nacieron en NULL.

Por qué existe: `crud.create_boletin` no tiene parámetro `jurisdiccion_id`, así
que toda fila creada por el `BatchProcessor` o por el upload nace huérfana.
`GET /boletines/calendar` filtra `Boletin.jurisdiccion_id == jurisdiccion_id`
(el frontend siempre manda 1), y `NULL == 1` es falso en SQL: esas filas quedan
invisibles al calendario, que las dibuja como `not_found` y ofrece un botón
"Descargar" que no hace nada (el endpoint las encuentra por filename, las ve
`completed`, y contesta "Ya procesado").

El jurisdiccion_id destino NO se hardcodea: se deriva de la única fuente
`boletin_diario` activa. Si hubiera más de una, el script se niega — asignar a
ciegas sería inventar procedencia.

Uso:
    python scripts/backfill_jurisdiccion_id.py            # dry-run (default)
    python scripts/backfill_jurisdiccion_id.py --apply     # escribe
"""

import argparse
import asyncio
import re
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import AsyncSessionLocal
from app.db.models import Boletin, FuenteDato

#: `YYYYMMDD_N_Secc.pdf` — el formato que produce el scraper provincial.
PATTERN_FILENAME = re.compile(r"^(\d{8})_([1-5])_Secc\.pdf$")


async def derivar_jurisdiccion(db) -> int:
    """El jurisdiccion_id de la única fuente `boletin_diario` activa."""
    result = await db.execute(
        select(FuenteDato.jurisdiccion_id, FuenteDato.nombre).where(
            FuenteDato.tipo == "boletin_diario",
            FuenteDato.activa,
        )
    )
    fuentes = result.all()

    if len(fuentes) != 1:
        raise SystemExit(
            f"❌ Esperaba exactamente 1 fuente boletin_diario activa, encontré "
            f"{len(fuentes)}: {fuentes}. No asigno jurisdicción a ciegas."
        )

    jurisdiccion_id, nombre = fuentes[0]
    print(f"🎯 Fuente boletin_diario activa: '{nombre}' → jurisdiccion_id={jurisdiccion_id}")
    return jurisdiccion_id


async def backfill(apply: bool) -> None:
    print("=" * 78)
    print("  BACKFILL jurisdiccion_id" + ("" if apply else "   [DRY-RUN — no escribe]"))
    print("=" * 78)

    async with AsyncSessionLocal() as db:
        jurisdiccion_id = await derivar_jurisdiccion(db)

        result = await db.execute(
            select(Boletin).where(Boletin.jurisdiccion_id.is_(None)).order_by(Boletin.id)
        )
        huerfanas = result.scalars().all()

        print(f"\n📊 Filas con jurisdiccion_id NULL: {len(huerfanas)}")
        if not huerfanas:
            print("✅ No hay nada que backfillear.")
            return

        # El guard: una fila que no matchea el formato provincial no se toca.
        # Preferimos dejar una fila invisible y reportarla antes que afirmar una
        # procedencia que no podemos sostener.
        asignables, sospechosas = [], []
        for b in huerfanas:
            (asignables if PATTERN_FILENAME.match(b.filename) else sospechosas).append(b)

        por_mes = Counter(b.date[:6] for b in asignables)
        print("\n📅 A asignar por mes:")
        for mes, n in sorted(por_mes.items()):
            print(f"     {mes}: {n:>4}")

        if sospechosas:
            print(f"\n⚠️  {len(sospechosas)} filas NO matchean 'YYYYMMDD_N_Secc.pdf' — no se tocan:")
            for b in sospechosas[:10]:
                print(f"     id={b.id} filename={b.filename!r} date={b.date!r}")
            if len(sospechosas) > 10:
                print(f"     … y {len(sospechosas) - 10} más")

        if not apply:
            print(f"\n🔎 Dry-run: se asignarían {len(asignables)} filas a "
                  f"jurisdiccion_id={jurisdiccion_id}.")
            print("   Volvé a correr con --apply para escribir.")
            return

        for b in asignables:
            b.jurisdiccion_id = jurisdiccion_id
        await db.commit()
        print(f"\n💾 Commit: {len(asignables)} filas → jurisdiccion_id={jurisdiccion_id}")

        # Verificación post-escritura, leída de la DB y no del objeto en memoria.
        restantes = await db.execute(
            select(Boletin.id).where(Boletin.jurisdiccion_id.is_(None))
        )
        n_restantes = len(restantes.all())
        print("\n" + "=" * 78)
        print("VERIFICACIÓN")
        print("=" * 78)
        print(f"✅ Asignadas          : {len(asignables)}")
        print(f"⚠️  Sospechosas (sin tocar): {len(sospechosas)}")
        print(f"📊 Siguen en NULL     : {n_restantes}")
        print("=" * 78)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill de boletines.jurisdiccion_id (NULL → fuente boletin_diario)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Escribe los cambios. Sin este flag corre en dry-run.",
    )
    args = parser.parse_args()
    asyncio.run(backfill(apply=args.apply))

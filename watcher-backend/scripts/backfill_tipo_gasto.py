#!/usr/bin/env python3
"""
Poblar `analisis.tipo_gasto`, `nivel`, `municipio`, `gasto_motivo` e
`is_duplicate_gasto` (M8, historia `pm-gasto-deteccion-ampliada`).

Por qué existe: el clasificador de gasto (`app/services/gasto_classifier.py`)
corre en vivo dentro del pipeline, pero los actos **ya extraídos** tienen las
columnas de M8 en NULL.  Y el ledger `ejecucion_presupuestaria` no sirve como
universo: sólo contiene los 1.220 actos que P.7 marcó como gasto público,
mientras que M8 pide clasificar **todo acto con monto** — 4.639 filas en
`analisis`.  Sin este backfill el listado de detección arrancaría vacío.

No re-extrae nada: clasifica con reglas sobre lo que ya está persistido
(`tipo_acto`, `descripcion`, `fragmento`, `organismo`, `boletines.section`).

Idempotente: recalcula todo el universo en cada corrida.  Tiene que ser así,
porque `is_duplicate_gasto` es un hecho **del corpus** (una republicación se
detecta comparando una fila contra las anteriores en orden de publicación), no
de una fila suelta.

Uso:
    python scripts/backfill_tipo_gasto.py              # dry-run (default)
    python scripts/backfill_tipo_gasto.py --apply      # escribe
    python scripts/backfill_tipo_gasto.py --limit 50   # muestra chica
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.gasto_classifier import (
    TIPO_NO_ES_GASTO,
    TIPO_OTRO,
    classify_gasto,
)
from app.services.presupuesto_matching import duplicados_de_filas

DB_PATH = Path(__file__).parent.parent / "sqlite.db"

# Debe coincidir con `_SQLITE_ADDED_COLUMNS` en app/db/database.py y con
# `_ADDED_COLUMNS` en scripts/etl_analisis_to_ejecucion.py.
_ADDED_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "analisis": [
        ("tipo_gasto", "TEXT"),
        ("objeto", "TEXT"),
        ("nivel", "TEXT"),
        ("municipio", "TEXT"),
        ("gasto_motivo", "TEXT"),
        ("is_duplicate_gasto", "INTEGER NOT NULL DEFAULT 0"),
    ],
}

_SELECT = """
    SELECT
        a.id            AS id,
        a.tipo_acto,
        a.numero_acto,
        a.organismo,
        a.descripcion,
        a.fragmento,
        a.monto_numerico,
        b.section       AS boletin_section
    FROM analisis a
    JOIN boletines b ON a.boletin_id = b.id
    WHERE a.monto_numerico > 0
    ORDER BY b.date, a.id
"""


def _ensure_columns(cur) -> None:
    for table, columns in _ADDED_COLUMNS.items():
        cur.execute(f"PRAGMA table_info({table})")
        existing = {r[1] for r in cur.fetchall()}
        if not existing:
            continue
        for col_name, col_type in columns:
            if col_name not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")


def run(apply: bool, limit: int | None) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    _ensure_columns(cur)

    rows = [dict(r) for r in cur.execute(_SELECT).fetchall()]
    if limit:
        rows = rows[:limit]
    print(f"actos con monto: {len(rows)}")

    # Corpus-wide, in publication order: same keys the ledger uses.
    dup = duplicados_de_filas(rows)

    por_tipo: Counter = Counter()
    por_objeto: Counter = Counter()
    por_nivel: Counter = Counter()
    sin_motivo = 0
    sin_clasificar = 0
    actualizados = 0

    for row in rows:
        c = classify_gasto(row, section=row.get("boletin_section"))
        fields = c.as_analisis_fields()
        is_dup = dup.get(row["id"], 0)

        por_tipo[fields["tipo_gasto"]] += 1
        por_objeto[fields["objeto"]] += 1
        por_nivel[fields["nivel"]] += 1
        if fields["tipo_gasto"] in (TIPO_OTRO, TIPO_NO_ES_GASTO) and not fields["gasto_motivo"]:
            sin_motivo += 1
        # Invariante de M8: ningún acto con monto queda sin ejes.
        if not fields["tipo_gasto"] or not fields["nivel"]:
            sin_clasificar += 1

        if apply:
            cur.execute(
                "UPDATE analisis SET tipo_gasto=?, objeto=?, nivel=?, municipio=?, "
                "gasto_motivo=?, is_duplicate_gasto=? WHERE id=?",
                (
                    fields["tipo_gasto"],
                    fields["objeto"],
                    fields["nivel"],
                    fields["municipio"],
                    fields["gasto_motivo"],
                    is_dup,
                    row["id"],
                ),
            )
            actualizados += 1
            if actualizados % 200 == 0:
                conn.commit()
                print(f"  ... {actualizados} actualizados")

    if apply:
        conn.commit()

    print("\nRESUMEN M8")
    print(f"  modo                 {'APPLY' if apply else 'DRY-RUN (no escribió)'}")
    print(f"  actos con monto      {len(rows)}")
    print(f"  republicaciones      {sum(1 for v in dup.values() if v)}")
    print(f"  sin tipo/nivel       {sin_clasificar}  (debe ser 0)")
    print(f"  otro/no_es_gasto sin motivo  {sin_motivo}  (debe ser 0)")
    print("\n  por tipo_gasto:")
    for tipo, n in por_tipo.most_common():
        print(f"    {tipo:24s} {n}")
    print("\n  por objeto:")
    for objeto, n in por_objeto.most_common():
        print(f"    {objeto:24s} {n}")
    print("\n  por nivel:")
    for nivel, n in por_nivel.most_common():
        print(f"    {nivel:24s} {n}")

    if not apply:
        print("\n   Volvé a correr con --apply para escribir.")
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Escribe los cambios. Sin este flag corre en dry-run.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Clasificar sólo las primeras N filas.")
    parser.add_argument("--db", type=Path, default=None, help="Ruta a sqlite.db (default: la del repo).")
    args = parser.parse_args()

    global DB_PATH
    if args.db:
        DB_PATH = args.db

    run(apply=args.apply, limit=args.limit)


if __name__ == "__main__":
    main()

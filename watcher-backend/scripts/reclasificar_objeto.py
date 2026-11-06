#!/usr/bin/env python3
"""
Reclasificar el eje `objeto` de todo el corpus con las reglas vigentes (WCL1).

Por qué existe: `objeto` se calcula en vivo en el pipeline y en la ingesta
municipal, pero las filas ya persistidas conservan el valor que tenían cuando se
escribieron.  Ampliar las reglas (racionamiento/alimentos, reparación edilicia,
"servicio de X", bienes por especie) no cambia una sola fila hasta que se
reclasifica.

**Sólo toca `analisis.objeto`.**  Los otros ejes (`tipo_gasto`, `etapa_gasto`,
`nivel`, `municipio`, `gasto_motivo`, `is_duplicate_gasto`) se dejan como están a
propósito:

- en las filas del portal municipal (`fuente='municipal_compras'`) la figura la
  dicta el portal, no el texto — reescribirla borraría el dato de la fuente;
- `is_duplicate_gasto` es un hecho del corpus que se recalcula entero en
  `scripts/backfill_tipo_gasto.py`, no acá;
- `objeto` es una pregunta distinta y autocontenida, y así el cambio de WCL1 no
  arrastra reclasificaciones que nadie pidió.

Idempotente: recalcula todo el universo `monto_numerico > 0` en cada corrida.
La segunda corrida informa 0 cambios.

Uso (desde `watcher-backend/`):
    python scripts/reclasificar_objeto.py            # dry-run (default)
    python scripts/reclasificar_objeto.py --apply     # escribe
    python scripts/reclasificar_objeto.py --db otra.db --apply

Antes de `--apply` sobre el corpus real conviene un backup con la API de backup
de SQLite (`sqlite3.Connection.backup`), no una copia del archivo.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.gasto_classifier import classify_objeto, texto_de_acto

DB_PATH = Path(__file__).parent.parent / "sqlite.db"

_SELECT = """
    SELECT
        a.id,
        a.tipo_gasto,
        a.objeto,
        a.descripcion,
        a.fragmento,
        a.organismo,
        b.fuente AS fuente
    FROM analisis a
    JOIN boletines b ON a.boletin_id = b.id
    WHERE a.monto_numerico > 0
    ORDER BY b.date, a.id
"""

_DISTRIBUCION = """
    SELECT b.fuente, a.objeto
    FROM analisis a
    JOIN boletines b ON a.boletin_id = b.id
    WHERE a.monto_numerico > 0
"""


def _distribucion(cur) -> Counter:
    return Counter((r[0], r[1] or "(sin objeto)") for r in cur.execute(_DISTRIBUCION))


def _print_distribucion(titulo: str, dist: Counter) -> None:
    print(titulo)
    for fuente in sorted({fuente for fuente, _ in dist}, key=str):
        print(f"  {fuente}")
        filas = sorted(
            ((objeto, n) for (f, objeto), n in dist.items() if f == fuente),
            key=lambda kv: (-kv[1], kv[0]),
        )
        for objeto, n in filas:
            print(f"    {objeto:16s} {n:5d}")


def run(apply: bool, limit: int | None) -> int:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    antes = _distribucion(cur)
    rows = [dict(r) for r in cur.execute(_SELECT).fetchall()]
    if limit:
        rows = rows[:limit]

    despues = Counter(antes)
    cambios: Counter = Counter()
    sin_figura = 0
    actualizados = 0

    for row in rows:
        if not row["tipo_gasto"]:
            # No debería pasar: el universo es `monto > 0` y el backfill de M8
            # clasificó los 4.639.  Si aparece, se informa en vez de inventar.
            sin_figura += 1
            continue

        nuevo = classify_objeto(row["tipo_gasto"], texto_de_acto(row))
        viejo = row["objeto"] or "(sin objeto)"
        if nuevo == viejo:
            continue

        cambios[(row["fuente"], viejo, nuevo)] += 1
        despues[(row["fuente"], viejo)] -= 1
        despues[(row["fuente"], nuevo)] += 1

        if apply:
            cur.execute("UPDATE analisis SET objeto=? WHERE id=?", (nuevo, row["id"]))
            actualizados += 1
            if actualizados % 500 == 0:
                conn.commit()
                print(f"  ... {actualizados} actualizados")

    if apply:
        conn.commit()

    print(f"\nactos con monto: {len(rows)}")
    print(f"modo: {'APPLY' if apply else 'DRY-RUN (no escribió)'}")
    print(f"cambios de objeto: {sum(cambios.values())}")
    if sin_figura:
        print(f"filas sin tipo_gasto (no tocadas): {sin_figura}")

    _print_distribucion("\nANTES — por fuente y objeto", antes)
    if apply:
        _print_distribucion("\nDESPUES — por fuente y objeto", despues)

    if cambios:
        print("\nCambios por fuente (antes -> despues):")
        for fuente in sorted({f for f, _, _ in cambios}, key=str):
            print(f"  {fuente}")
            for (_, viejo, nuevo), n in sorted(
                ((k, v) for k, v in cambios.items() if k[0] == fuente), key=lambda kv: -kv[1]
            ):
                print(f"    {viejo:16s} -> {nuevo:16s} {n:5d}")

    if not apply:
        print("\nVolvé a correr con --apply para escribir.")
    conn.close()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Escribe los cambios. Sin este flag corre en dry-run.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Reclasificar sólo las primeras N filas.")
    parser.add_argument("--db", type=Path, default=None, help="Ruta a sqlite.db (default: la del repo).")
    args = parser.parse_args()

    global DB_PATH
    if args.db:
        DB_PATH = args.db

    raise SystemExit(run(apply=args.apply, limit=args.limit))


if __name__ == "__main__":
    main()

"""Report ledger rows whose persisted `presupuesto_base_id` the live matcher no longer assigns.

`presupuesto_base_id` is a persisted field: the ETL writes it once and nothing
revalidates it.  When `presupuesto_matching` gets stricter (V.2 did exactly
that), rows keep pointing at denominators the current matcher rejects.  The UI
groups by `COALESCE(pb.organismo, e.organismo)` and marks an organism `matched`
whenever it exists in `presupuesto_base`, so a stale id does not merely mislabel
a bar — it resurrects a false denominator and a false >100% alert.

Read-only.  Exits 1 when drift is found so it can gate CI or a test.

Usage:
    cd watcher-backend
    python scripts/check_match_drift.py [--json]
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.presupuesto_matching import (
    _normalize,
    build_presupuesto_index,
    match_organismo,
)

DB_PATH = Path(__file__).parent.parent / "sqlite.db"


def load_ledger_rows(cur: sqlite3.Cursor) -> list[dict]:
    cur.execute(
        """
        SELECT e.id, e.organismo, e.monto, e.etapa_gasto, e.jurisdiccion,
               e.presupuesto_base_id, pb.organismo AS pb_organismo
        FROM ejecucion_presupuestaria e
        LEFT JOIN presupuesto_base pb ON pb.id = e.presupuesto_base_id
        WHERE e.monto > 0
        ORDER BY e.monto DESC
        """
    )
    return [dict(r) for r in cur.fetchall()]


def load_presupuesto_index(cur: sqlite3.Cursor):
    cur.execute(
        "SELECT id, organismo, programa, partida_presupuestaria "
        "FROM presupuesto_base WHERE ejercicio=2026"
    )
    return build_presupuesto_index(
        [(r["id"], r["organismo"], r["programa"], r["partida_presupuestaria"]) for r in cur]
    )


def find_drift(cur: sqlite3.Cursor) -> list[dict]:
    """Return rows where the live matcher disagrees with the persisted pb_id."""
    pb_index, pb_exact = load_presupuesto_index(cur)
    drift: list[dict] = []
    for row in load_ledger_rows(cur):
        live_id, score, method, _, _ = match_organismo(
            _normalize(row["organismo"] or ""), pb_index, pb_exact
        )
        if live_id == row["presupuesto_base_id"]:
            continue
        drift.append(
            {
                "id": row["id"],
                "organismo": row["organismo"],
                "monto": float(row["monto"]),
                "etapa": row["etapa_gasto"],
                "jurisdiccion": row["jurisdiccion"],
                "pb_id_persisted": row["presupuesto_base_id"],
                "pb_organismo_persisted": row["pb_organismo"],
                "pb_id_live": live_id,
                "score_live": score,
                "method_live": method,
            }
        )
    return drift


def render(drift: list[dict]) -> None:
    total = sum(d["monto"] for d in drift)
    unmatched = [d for d in drift if d["pb_id_live"] is None and d["pb_id_persisted"]]
    unmatched_monto = sum(d["monto"] for d in unmatched)

    print(f"filas con deriva de match: {len(drift)}  (${total / 1e9:.2f}B)")
    print(
        f"  de esas, el matcher vivo las declara SIN match: {len(unmatched)} "
        f"(${unmatched_monto / 1e9:.2f}B) — denominador falso persistido"
    )
    if not drift:
        print("OK: el ledger persistido coincide con el matcher actual.")
        return

    print()
    print(f"{'id':>5} {'monto':>12} {'pb viejo':>9} {'pb vivo':>8} {'score':>6}  organismo")
    for d in drift:
        viejo = d["pb_id_persisted"] if d["pb_id_persisted"] is not None else "-"
        vivo = d["pb_id_live"] if d["pb_id_live"] is not None else "None"
        print(
            f"{d['id']:>5} {d['monto'] / 1e9:>11.2f}B {str(viejo):>9} {str(vivo):>8} "
            f"{d['score_live']:>6.2f}  {(d['organismo'] or '')[:44]}"
        )

    print()
    por_jurisdiccion: dict[str, float] = defaultdict(float)
    for d in drift:
        por_jurisdiccion[d["jurisdiccion"] or "(sin)"] += d["monto"]
    for jur, monto in sorted(por_jurisdiccion.items(), key=lambda kv: -kv[1]):
        print(f"  {jur:<18} ${monto / 1e9:.2f}B")


def main() -> int:
    if not DB_PATH.exists():
        print(f"no existe {DB_PATH}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        drift = find_drift(conn.cursor())
    finally:
        conn.close()

    if "--json" in sys.argv:
        print(json.dumps(drift, ensure_ascii=False, indent=2))
    else:
        render(drift)
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())

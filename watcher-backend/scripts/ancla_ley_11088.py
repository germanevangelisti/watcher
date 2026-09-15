#!/usr/bin/env python3
"""V.1.4 — contrast presupuesto_base 2026 vs parsed Ley 11.088 / Mapas."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.presupuesto_matching import (
    _normalize,
    build_presupuesto_index,
    match_organismo,
)

DB = Path(__file__).resolve().parent.parent / "sqlite.db"
PARSED = (
    Path(__file__).resolve().parent.parent.parent
    / "watcher-doc"
    / "data"
    / "2026"
    / "presupuesto_2026_parsed.json"
)
MD_OUT = (
    Path(__file__).resolve().parent.parent.parent
    / "knowledgebase"
    / "current"
    / "ancla-ley-11088.md"
)


def _sum_org(rows, needles: tuple[str, ...]) -> float:
    total = 0.0
    for org, vigente in rows:
        n = _normalize(org)
        if any(needle in n for needle in needles):
            total += vigente or 0
    return total


def main() -> None:
    parsed = json.loads(PARSED.read_text(encoding="utf-8"))
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cur = conn.cursor()
    db_orgs = cur.execute(
        "SELECT organismo, SUM(monto_vigente) FROM presupuesto_base "
        "WHERE ejercicio=2026 GROUP BY organismo"
    ).fetchall()
    db_n = cur.execute(
        "SELECT COUNT(*) FROM presupuesto_base WHERE ejercicio=2026"
    ).fetchone()[0]
    db_total = cur.execute(
        "SELECT SUM(monto_vigente) FROM presupuesto_base WHERE ejercicio=2026"
    ).fetchone()[0]
    parsed_total = sum(r.get("monto_vigente") or 0 for r in parsed)
    parsed_by_prog = {
        (r.get("organismo"), r.get("programa")): r.get("monto_vigente")
        for r in parsed
    }
    sample_rows = cur.execute(
        """
        SELECT organismo, programa, monto_vigente
        FROM presupuesto_base WHERE ejercicio=2026
        ORDER BY monto_vigente DESC
        LIMIT 15
        """
    ).fetchall()

    pb_rows = cur.execute(
        "SELECT id, organismo, programa, partida_presupuestaria "
        "FROM presupuesto_base WHERE ejercicio=2026"
    ).fetchall()
    pb_index, pb_exact = build_presupuesto_index(list(pb_rows))

    probes = [
        "UNIDAD EJECUTORA",
        "LAS PENAS SUD - LAS ISLETILLAS",
        "DIRECCION DE MINISTERIO",
        "EPEC",
        "ACIF",
        "MINISTERIO DE SEGURIDAD",
        "PODER JUDICIAL DE LA PROVINCIA DE CORDOBA",
        "EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA",
    ]
    match_log = []
    for name in probes:
        pb_id, score, method, programa, partida = match_organismo(
            _normalize(name), pb_index, pb_exact
        )
        dest = None
        if pb_id:
            dest = cur.execute(
                "SELECT organismo FROM presupuesto_base WHERE id=?", (pb_id,)
            ).fetchone()[0]
        match_log.append((name, pb_id, score, method, dest, programa))

    unmatched = cur.execute(
        """
        SELECT a.organismo, COUNT(*) n,
               SUM(CASE WHEN e.is_duplicate=1 THEN 0 ELSE COALESCE(e.monto,0) END)
        FROM analisis a
        LEFT JOIN ejecucion_presupuestaria e ON e.analisis_id=a.id
        WHERE a.is_gasto_publico=1
          AND a.jurisdiccion_gasto='provincial'
          AND (e.presupuesto_base_id IS NULL)
        GROUP BY a.organismo
        ORDER BY n DESC
        """
    ).fetchall()

    epec_db = _sum_org(db_orgs, ("EPEC", "EMPRESA PROVINCIAL DE ENERGIA"))
    acif_db = _sum_org(db_orgs, ("ACIF", "AGENCIA CORDOBA DE INVERSION"))
    epec_json = sum(
        r.get("monto_vigente") or 0
        for r in parsed
        if "EPEC" in _normalize(r.get("organismo") or "")
        or "EMPRESA PROVINCIAL DE ENERGIA" in _normalize(r.get("organismo") or "")
    )
    acif_json = sum(
        r.get("monto_vigente") or 0
        for r in parsed
        if "ACIF" in _normalize(r.get("organismo") or "")
        or "AGENCIA CORDOBA DE INVERSION" in _normalize(r.get("organismo") or "")
    )

    lines = [
        "# Ancla Ley 11.088 — V.1.4",
        "",
        "Denominador = `presupuesto_base` ejercicio 2026 (parser de "
        "`Mapas-por-Programas.pdf`). No es caja CGE.",
        "",
        "## Totales",
        "",
        "| Fuente | Programas | Suma `monto_vigente` |",
        "|---|---:|---:|",
        f"| `presupuesto_base` | {db_n} | ${db_total:,.0f} |",
        f"| JSON parseado | {len(parsed)} | ${parsed_total:,.0f} |",
        f"| Δ | {db_n - len(parsed)} | ${ (db_total or 0) - parsed_total:,.0f} |",
        "",
        "## EPEC / ACIF",
        "",
        "| Organismo | DB | JSON parseado |",
        "|---|---:|---:|",
        f"| EPEC | ${epec_db:,.0f} | ${epec_json:,.0f} |",
        f"| ACIF | ${acif_db:,.0f} | ${acif_json:,.0f} |",
        "",
        "## Sample 15 programas (los de mayor vigente en DB)",
        "",
        "| Organismo | Programa | vigente DB | vigente JSON | Δ |",
        "|---|---|---:|---:|---:|",
    ]
    for org, prog, vigente in sample_rows:
        j = parsed_by_prog.get((org, prog))
        delta = "" if j is None else f"${(vigente or 0) - j:,.0f}"
        jtxt = "—" if j is None else f"${j:,.0f}"
        lines.append(
            f"| {org} | {prog} | ${vigente or 0:,.0f} | {jtxt} | {delta} |"
        )

    lines.extend(
        [
            "",
            "## Matching S-511 / UNIDAD EJECUTORA / DIRECCIÓN DE MINISTERIO",
            "",
            "En este corte el pliego S-511 (pavimento Las Peñas–Isletillas, "
            "~$25.341 M) entra al ledger como `UNIDAD EJECUTORA` o el tramo "
            "de ruta, no como `DIRECCIÓN DE MINISTERIO`. El 295% de P.7.4 "
            "venía de un recorte con 1-sep; acá el falso positivo se "
            "reproduce como Jaccard contra el índice, no como fila viva.",
            "",
            "| Query | pb_id | score | method | organismo DB | programa |",
            "|---|---:|---:|---|---|---|",
        ]
    )
    for name, pb_id, score, method, dest, programa in match_log:
        lines.append(
            f"| `{name}` | {pb_id or ''} | {score:.2f} | {method or ''} | "
            f"{dest or ''} | {programa or ''} |"
        )

    lines.extend(
        [
            "",
            "## Unmatched provinciales (`is_gasto_publico=1`, sin `presupuesto_base_id`)",
            "",
            "| Organismo | n | monto ledger |",
            "|---|---:|---:|",
        ]
    )
    for org, n, monto in unmatched:
        lines.append(f"| {org} | {n} | ${monto or 0:,.0f} |")
    lines.append("")
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    conn.close()


if __name__ == "__main__":
    main()

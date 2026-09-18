#!/usr/bin/env python3
"""V.2.1 — bitácora de alertas >100% vs Ley 11.088.

Organismo UI → filas ledger canónicas → pb_id → monto_vigente.
Read-only against sqlite.db. Does not rewrite the ledger.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ejecucion_contrast import (
    aggregate_organismos,
    remap_organismo_key,
    vigente_por_organismo_canonico,
)
from app.services.presupuesto_matching import (
    _normalize,
    build_presupuesto_index,
    match_organismo,
)

DB = Path(__file__).resolve().parent.parent / "sqlite.db"
MD_OUT = (
    Path(__file__).resolve().parent.parent.parent
    / "knowledgebase"
    / "current"
    / "bitacora-alertas-v2-post.md"
)


def main() -> None:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    vig_rows = cur.execute(
        """
        SELECT organismo, SUM(monto_vigente) vigente
        FROM presupuesto_base WHERE ejercicio=2026
        GROUP BY organismo
        """
    ).fetchall()
    vigente_por_org, display_by_canon = vigente_por_organismo_canonico(
        [(r["organismo"], float(r["vigente"] or 0)) for r in vig_rows]
    )

    spend_rows = cur.execute(
        """
        SELECT
            COALESCE(pb.organismo, e.organismo) AS org_key,
            e.etapa_gasto,
            SUM(COALESCE(e.monto, 0)) AS total,
            COUNT(*) AS cnt
        FROM ejecucion_presupuestaria e
        LEFT JOIN presupuesto_base pb ON pb.id = e.presupuesto_base_id
        WHERE e.is_duplicate = 0
          AND e.jurisdiccion = 'provincial'
        GROUP BY org_key, e.etapa_gasto
        """
    ).fetchall()
    contrast = aggregate_organismos(
        [
            (
                remap_organismo_key(r["org_key"], display_by_canon),
                r["etapa_gasto"],
                float(r["total"]),
                int(r["cnt"]),
            )
            for r in spend_rows
        ],
        vigente_por_org,
    )
    alerts = [c for c in contrast if c.sobre_compromiso]

    pb_rows = cur.execute(
        "SELECT id, organismo, programa, partida_presupuestaria "
        "FROM presupuesto_base WHERE ejercicio=2026"
    ).fetchall()
    pb_index, pb_exact = build_presupuesto_index(
        [(r["id"], r["organismo"], r["programa"], r["partida_presupuestaria"]) for r in pb_rows]
    )

    lines: list[str] = [
        "# Bitácora alertas — post V.2 matching/denominador",
        "",
        "Capa B: compromisos del Boletín vs `presupuesto_base` (Ley 11.088). "
        "No es caja CGE. Reproducible con "
        "`uv run python scripts/bitacora_alertas_v2.py`.",
        "",
        f"Alertas `sobre_compromiso` (filtro provincial, canónicos): **{len(alerts)}**.",
        "",
        "| Organismo UI | compromiso | vigente | % | n |",
        "|---|---:|---:|---:|---:|",
    ]
    for c in alerts:
        lines.append(
            f"| {c.organismo} | ${c.monto_compromiso:,.0f} | "
            f"${c.monto_vigente or 0:,.0f} | {c.pct_compromiso}% | {c.count} |"
        )

    for c in alerts:
        lines.extend(
            [
                "",
                f"## {c.organismo}",
                "",
                f"- compromiso ${c.monto_compromiso:,.0f} / vigente "
                f"${c.monto_vigente or 0:,.0f} = **{c.pct_compromiso}%**",
                "",
            ]
        )

        pb_for_org = cur.execute(
            """
            SELECT id, organismo, programa, monto_vigente
            FROM presupuesto_base
            WHERE ejercicio=2026 AND organismo = ?
            ORDER BY monto_vigente DESC
            """,
            (c.organismo,),
        ).fetchall()
        lines.append("### Programas `presupuesto_base` con este organismo")
        lines.append("")
        lines.append("| pb_id | programa | vigente |")
        lines.append("|---:|---|---:|")
        if not pb_for_org:
            lines.append("|  | *(ninguno — vigente vino de otro nombre)* |  |")
        for r in pb_for_org:
            lines.append(
                f"| {r['id']} | {r['programa']} | ${r['monto_vigente'] or 0:,.0f} |"
            )

        ledger = cur.execute(
            """
            SELECT
                e.id,
                e.organismo AS org_ledger,
                e.monto,
                e.etapa_gasto,
                e.presupuesto_base_id,
                e.programa AS prog_match,
                e.observaciones,
                a.numero_acto AS numero_analisis,
                pb.organismo AS org_pb,
                pb.programa AS prog_pb,
                pb.monto_vigente
            FROM ejecucion_presupuestaria e
            LEFT JOIN analisis a ON a.id = e.analisis_id
            LEFT JOIN presupuesto_base pb ON pb.id = e.presupuesto_base_id
            WHERE e.is_duplicate = 0
              AND e.jurisdiccion = 'provincial'
              AND COALESCE(pb.organismo, e.organismo) = ?
            ORDER BY e.monto DESC
            LIMIT 25
            """,
            (c.organismo,),
        ).fetchall()
        lines.append("")
        lines.append("### Filas ledger (top 25 por monto)")
        lines.append("")
        lines.append(
            "| id | org ledger | número | monto | etapa | pb_id | org pb | programa pb |"
        )
        lines.append("|---:|---|---|---:|---|---:|---|---|")
        for r in ledger:
            lines.append(
                f"| {r['id']} | {r['org_ledger'] or ''} | "
                f"{r['numero_analisis'] or ''} | ${r['monto'] or 0:,.0f} | "
                f"{r['etapa_gasto'] or ''} | {r['presupuesto_base_id'] or ''} | "
                f"{r['org_pb'] or ''} | {r['prog_pb'] or r['prog_match'] or ''} |"
            )

        distinct_ledger_orgs = cur.execute(
            """
            SELECT e.organismo, COUNT(*) n, SUM(e.monto) monto
            FROM ejecucion_presupuestaria e
            LEFT JOIN presupuesto_base pb ON pb.id = e.presupuesto_base_id
            WHERE e.is_duplicate = 0
              AND e.jurisdiccion = 'provincial'
              AND COALESCE(pb.organismo, e.organismo) = ?
            GROUP BY e.organismo
            ORDER BY monto DESC
            """,
            (c.organismo,),
        ).fetchall()
        lines.append("")
        lines.append("### Nombres en el ledger que cuelgan de este organismo UI")
        lines.append("")
        lines.append("| organismo ledger | n | monto | match en vivo |")
        lines.append("|---|---:|---:|---|")
        for r in distinct_ledger_orgs:
            org = r["organismo"] or ""
            pb_id, score, method, programa, _ = match_organismo(
                _normalize(org), pb_index, pb_exact
            )
            dest = ""
            if pb_id:
                dest = cur.execute(
                    "SELECT organismo FROM presupuesto_base WHERE id=?", (pb_id,)
                ).fetchone()[0]
            lines.append(
                f"| {org} | {r['n']} | ${r['monto'] or 0:,.0f} | "
                f"{method or 'unmatched'} pb_id={pb_id or '—'} "
                f"score={score:.2f} → {dest or programa or ''} |"
            )

    # Truncated names in presupuesto_base (V.2.4 evidence)
    trunc = cur.execute(
        """
        SELECT organismo, COUNT(*) n, SUM(monto_vigente) vigente
        FROM presupuesto_base WHERE ejercicio=2026
        GROUP BY organismo
        HAVING LENGTH(organismo) < 18
            OR organismo LIKE 'MINISTERIO DE'
            OR organismo LIKE 'SECRETAR_A DE %'
        ORDER BY vigente DESC
        LIMIT 40
        """
    ).fetchall()
    lines.extend(
        [
            "",
            "## Nombres cortos / truncos en `presupuesto_base`",
            "",
            "| organismo | n programas | vigente |",
            "|---|---:|---:|",
        ]
    )
    for r in trunc:
        lines.append(
            f"| {r['organismo']} | {r['n']} | ${r['vigente'] or 0:,.0f} |"
        )

    lines.append("")
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    conn.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""V.1.5 — contrast CGE T1 2026 (Marzo) vs 8 organismos of the ledger.

Does not mix CGE pagado into the UI compromiso/ejecución bar.
Registers fuentes_dato tipo ejecucion_trimestral for Provincia.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.cge_trimestral import (
    CGE_TARGETS,
    aggregate_cge_rows,
    iter_gasto_rows,
    magnitude_note,
    match_ledger_bucket,
    pick_targets,
)
from app.services.gasto_classifier import (
    ETAPAS_COMPROMISO,
    ETAPAS_EJECUCION,
    JURISDICCION_PROVINCIAL,
)

REPO = Path(__file__).resolve().parent.parent.parent
DB = Path(__file__).resolve().parent.parent / "sqlite.db"
CGE_DIR = REPO / "watcher-doc" / "data" / "2026" / "cge"
EXTRACTED = CGE_DIR / "extracted"
MD_OUT = REPO / "knowledgebase" / "current" / "cge-trimestral.md"
JSON_OUT = CGE_DIR / "ejecucion_marzo_2026_organismos.json"

GASTO_FILES = (
    "Gastos Administración Central - Acumulado Marzo 2026.xlsx",
    "Gastos EMAEE - Acumulado Marzo 2026.xlsx",
)
CGE_PORTAL = (
    "https://economiaygestionpublica.cba.gov.ar/publicacion/"
    "ejecucion-presupuestaria/"
)
CGE_DATOS = (
    "https://economiaygestionpublica.cba.gov.ar/download/12397/"
    "?tmstv=1789410356"
)
CGE_INFORME = (
    "https://economiaygestionpublica.cba.gov.ar/download/12413/"
    "?tmstv=1789410356"
)


def _money(value: float) -> str:
    mill = value / 1_000_000
    return f"${mill:,.1f} M"


def _ledger_buckets(conn: sqlite3.Connection) -> dict[str, dict[str, float]]:
    rows = conn.execute(
        """
        SELECT organismo, etapa_gasto, SUM(monto), COUNT(*)
        FROM ejecucion_presupuestaria
        WHERE COALESCE(is_duplicate, 0) = 0
          AND (jurisdiccion IS NULL OR jurisdiccion = ?)
        GROUP BY organismo, etapa_gasto
        """,
        (JURISDICCION_PROVINCIAL,),
    ).fetchall()
    out: dict[str, dict[str, float]] = {}
    for org, etapa, monto, n in rows:
        bucket = out.setdefault(
            org or "",
            {"compromiso": 0.0, "ejecucion": 0.0, "n": 0.0},
        )
        amount = float(monto or 0)
        if etapa in ETAPAS_COMPROMISO:
            bucket["compromiso"] += amount
        elif etapa in ETAPAS_EJECUCION:
            bucket["ejecucion"] += amount
        bucket["n"] += int(n or 0)
    return out


def _sum_ledger(ledger: dict[str, dict[str, float]], needles: tuple[str, ...]):
    compromiso = ejecucion = n = 0.0
    for org, bucket in ledger.items():
        if not match_ledger_bucket(org, needles):
            continue
        compromiso += bucket["compromiso"]
        ejecucion += bucket["ejecucion"]
        n += bucket["n"]
    return compromiso, ejecucion, n


def register_fuente(conn: sqlite3.Connection) -> str:
    existing = conn.execute(
        "SELECT id FROM fuentes_dato WHERE jurisdiccion_id=1 "
        "AND tipo='ejecucion_trimestral'"
    ).fetchone()
    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
    desc = (
        "Informe CGE / Hacienda T1 2026 (acumulado a marzo). "
        f"Datos abiertos: {CGE_DATOS}. Informe: {CGE_INFORME}. "
        "Orden de magnitud vs ledger de boletines; no es join acto a acto."
    )
    if existing:
        conn.execute(
            """
            UPDATE fuentes_dato
            SET nombre=?, url_template=?, activa=1, descripcion=?,
                updated_at=?
            WHERE id=?
            """,
            (
                "Ejecución presupuestaria CGE T1 2026",
                CGE_PORTAL,
                desc,
                now,
                existing[0],
            ),
        )
        conn.commit()
        return f"updated id={existing[0]}"
    conn.execute(
        """
        INSERT INTO fuentes_dato
        (jurisdiccion_id, tipo, nombre, url_template, activa, descripcion,
         created_at, updated_at)
        VALUES (1, 'ejecucion_trimestral', ?, ?, 1, ?, ?, ?)
        """,
        (
            "Ejecución presupuestaria CGE T1 2026",
            CGE_PORTAL,
            desc,
            now,
            now,
        ),
    )
    conn.commit()
    return f"inserted id={conn.execute('SELECT last_insert_rowid()').fetchone()[0]}"


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

    all_totals: dict = {}
    for name in GASTO_FILES:
        path = EXTRACTED / name
        if not path.exists():
            raise SystemExit(f"Falta el Excel CGE extraído: {path}")
        rows = list(iter_gasto_rows(path))
        chunk = aggregate_cge_rows(rows, source=name)
        all_totals.update(chunk)

    targets = pick_targets(all_totals)
    conn = sqlite3.connect(DB)
    ledger = _ledger_buckets(conn)
    fuente_msg = register_fuente(conn)

    table_rows = []
    json_rows = []
    for target, spec in zip(targets, CGE_TARGETS):
        display, needles, _kind = spec
        l_comp, l_ejec, l_n = _sum_ledger(ledger, needles)
        cge_box = target.devengado or target.pagado
        note = magnitude_note(l_comp + l_ejec, cge_box)
        table_rows.append(
            (
                display,
                target.vigente,
                target.compromiso,
                target.devengado,
                target.pagado,
                l_comp,
                l_ejec,
                l_n,
                note,
            )
        )
        json_rows.append(
            {
                "organismo": display,
                "cge": target.as_dict(),
                "ledger_compromiso": l_comp,
                "ledger_ejecucion": l_ejec,
                "ledger_n": l_n,
                "nota": note,
            }
        )

    lines = [
        "# Trimestral CGE vs ledger — V.1.5",
        "",
        "Corte: **acumulado a marzo 2026 (T1)** publicado por Economía y "
        "Gestión Pública / CGE. El ledger de Watcher es **proxy de "
        "compromisos publicados** en el Boletín Oficial, no tesorería.",
        "",
        f"- Portal: {CGE_PORTAL}",
        f"- Datos abiertos (zip de Excel): `{CGE_DATOS}`",
        f"- Informe PDF: `{CGE_INFORME}`",
        f"- `fuentes_dato`: {fuente_msg}",
        "",
        "No mezclar `pagado` CGE en la misma barra que compromiso/ejecución "
        "del boletín.",
        "",
        "## Ocho organismos (orden de magnitud)",
        "",
        "| Organismo | CGE vigente | CGE compromiso | CGE devengado | "
        "CGE pagado | Ledger compromiso | Ledger ejecución | n | Lectura |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in table_rows:
        (
            display, vig, comp, dev, pag, l_comp, l_ejec, l_n, note,
        ) = row
        lines.append(
            f"| {display} | {_money(vig)} | {_money(comp)} | {_money(dev)} | "
            f"{_money(pag)} | {_money(l_comp)} | {_money(l_ejec)} | "
            f"{int(l_n)} | {note} |"
        )
    lines.extend(
        [
            "",
            "## Qué significa",
            "",
            "- EMAEE (EPEC, ACIF) **no publica COMPROMISO**; el número de "
            "caja es DEVENGADO (EPEC) o DEVENGADO+PAGADO (ACIF).",
            "- ACIF vigente CGE (~$1,82 billones) **no coincide** con el "
            "vigente Ley 11.088 en `presupuesto_base` (~$0,57 billones): "
            "perímetros distintos (fideicomisos / financiamiento vs "
            "programa de la Ley). Documentado, no silenciado.",
            "- EPEC vigente CGE ≈ vigente Ley (~$2,63 billones).",
            "- Policía es unidad 199 bajo Ministerio de Seguridad, no una "
            "jurisdicción propia.",
            "- `Dirección de Ministerio` / Inteligencia Fiscal **no existe** "
            "como unidad CGE. El 295% de P.7 era matching del pliego S-511, "
            "no caja.",
            "- Watcher cubre feb–mar 2026 publicado (marzo cerrado). CGE cubre "
            "todo el T1 SIGAF. El ledger es **suelo de avisos del BO**, no "
            "tesorería: un % alto vs CGE (p.ej. EPEC/ACIF) no es join acto a "
            "acto ni caja.",
            "",
            "KPI prohibido: sumar `analisis.monto_numerico` crudo.",
            "",
        ]
    )
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")
    CGE_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(
        json.dumps(
            {
                "periodo": "marzo-2026",
                "portal": CGE_PORTAL,
                "datos_abiertos": CGE_DATOS,
                "informe": CGE_INFORME,
                "organismos": json_rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print("\n".join(lines))
    print(f"Wrote {MD_OUT}")
    print(f"Wrote {JSON_OUT}")
    print(f"fuente {fuente_msg}")
    conn.close()


if __name__ == "__main__":
    main()

"""
ETL: analisis → ejecucion_presupuestaria

Batch rebuild of the budget execution table from analyzed administrative acts.
The live per-boletín path is `app/services/ejecucion_ledger.py`; this script
exists to backfill a corpus ingested before that hook, and both share
`app/services/presupuesto_matching.py` so they agree on dedup keys.

Only actos classified as public spending reach the table (P.7.1): remates,
corporate filings and budget line transfers carry large montos but are not
spending.  Actos ingested before the classifier existed are classified here on
the fly and the result is written back to `analisis`.

Attempts fuzzy organismo matching against presupuesto_base (ejercicio=2026).
Detects duplicate publications of the same acto (same tender published on
consecutive days) and marks them with is_duplicate=1; their monto is excluded
from the cumulative accumulators.

Usage:
    cd watcher-backend
    python scripts/etl_analisis_to_ejecucion.py [--dry-run]
"""

from __future__ import annotations

import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.gasto_classifier import classify_gasto
from app.services.presupuesto_matching import (
    _ACTO_NO_DEDUP,
    _ANALISIS_NO_MATCH,
    _dedup_key,
    _normalize,
    _normalize_acto,
    _ORGANISMO_ALIASES,
    _token_jaccard,
    build_presupuesto_index,
    extract_numero_acto,
    first_beneficiario,
    looks_like_publication_id,
    match_organismo,
    parse_date,
    resolve_numero_acto,
)

# Re-exported so the existing test suite keeps importing these from the script.
__all__ = [
    "_ACTO_NO_DEDUP",
    "_ANALISIS_NO_MATCH",
    "_ORGANISMO_ALIASES",
    "_dedup_key",
    "_normalize",
    "_normalize_acto",
    "_token_jaccard",
    "build_presupuesto_index",
    "classify_gasto",
    "extract_numero_acto",
    "first_beneficiario",
    "looks_like_publication_id",
    "match_organismo",
    "parse_date",
    "resolve_numero_acto",
    "run_etl",
]

DB_PATH = Path(__file__).parent.parent / "sqlite.db"


def load_presupuesto_rows(cur, ejercicio: int = 2026) -> list[tuple[int, str, str, str | None]]:
    """Fetch presupuesto_base rows for one ejercicio as raw index input."""
    cur.execute(
        "SELECT id, organismo, programa, partida_presupuestaria "
        "FROM presupuesto_base WHERE ejercicio=?",
        (ejercicio,),
    )
    return [tuple(r) for r in cur.fetchall()]


_ADDED_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "ejecucion_presupuestaria": [
        ("is_duplicate", "INTEGER NOT NULL DEFAULT 0"),
        ("analisis_id", "INTEGER"),
        ("etapa_gasto", "TEXT"),
        ("jurisdiccion", "TEXT"),
    ],
    "analisis": [
        ("is_gasto_publico", "INTEGER"),
        ("etapa_gasto", "TEXT"),
        ("jurisdiccion_gasto", "TEXT"),
    ],
}


def _ensure_columns(cur) -> None:
    """Add columns missing from DBs created before P.7 (idempotent)."""
    for table, columns in _ADDED_COLUMNS.items():
        cur.execute(f"PRAGMA table_info({table})")
        existing = {r[1] for r in cur.fetchall()}
        if not existing:
            continue
        for col_name, col_type in columns:
            if col_name not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")


def _classify_pending(cur, rows: list[dict], dry_run: bool = False) -> int:
    """Classify rows lacking P.7.1 flags, mutating them in place.

    Writes the classification back to `analisis` so it is computed once, and
    recovers `numero_acto` when the LLM left it null — without it the dedup key
    collapses to (organismo, monto) and republished tenders stay uncollapsed.
    """
    pending = 0
    for row in rows:
        if row.get("is_gasto_publico") is None or not row.get("etapa_gasto"):
            classification = classify_gasto(row, section=row.get("boletin_section"))
            row["is_gasto_publico"] = 1 if classification.is_gasto_publico else 0
            row["etapa_gasto"] = classification.etapa_gasto
            row["jurisdiccion_gasto"] = classification.jurisdiccion
            pending += 1
        row["numero_acto"] = resolve_numero_acto(
            row.get("numero_acto"), row.get("descripcion"), row.get("fragmento")
        )

        if not dry_run:
            cur.execute(
                "UPDATE analisis SET is_gasto_publico=?, etapa_gasto=?, "
                "jurisdiccion_gasto=?, numero_acto=? WHERE id=?",
                (
                    row["is_gasto_publico"],
                    row["etapa_gasto"],
                    row["jurisdiccion_gasto"],
                    row["numero_acto"],
                    row["analisis_id"],
                ),
            )
    return pending


# ── ETL main ───────────────────────────────────────────────────────────────────

def run_etl(dry_run: bool = False) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    _ensure_columns(cur)

    # Load presupuesto_base index + exact-match dict for O(1) lookups
    pb_index, pb_exact = build_presupuesto_index(load_presupuesto_rows(cur))
    print(f"presupuesto_base 2026: {len(pb_index)} programmes loaded")

    # Fetch analisis records with montos > 0 joined with boletin date
    cur.execute("""
        SELECT
            a.id            AS analisis_id,
            a.boletin_id,
            a.tipo_acto,
            a.numero_acto,
            a.organismo,
            a.descripcion,
            a.fragmento,
            a.monto_numerico,
            a.categoria,
            a.riesgo,
            a.beneficiarios_json,
            a.entidad_beneficiaria,
            a.motivo_riesgo,
            a.is_gasto_publico,
            a.etapa_gasto,
            a.jurisdiccion_gasto,
            b.date          AS boletin_date,
            b.section       AS boletin_section
        FROM analisis a
        JOIN boletines b ON a.boletin_id = b.id
        WHERE a.monto_numerico > 0
        ORDER BY b.date, a.id
    """)
    rows = [dict(r) for r in cur.fetchall()]
    print(f"analisis rows with monto > 0: {len(rows)}")

    # Classify actos ingested before P.7.1 and persist the result so the live
    # ledger and this script see the same flags on the next run.
    classified = _classify_pending(cur, rows, dry_run=dry_run)
    if classified:
        print(f"clasificados en este run: {classified}")
    if not dry_run:
        conn.commit()

    gasto_rows = [r for r in rows if r["is_gasto_publico"]]
    print(f"actos de gasto público: {len(gasto_rows)} (excluidos {len(rows) - len(gasto_rows)})")
    rows = gasto_rows

    # Build cumulative monthly / quarterly / annual totals per organismo
    # Only canonical (non-duplicate) rows contribute to accumulators.
    monthly_acc: dict[tuple, float] = defaultdict(float)
    quarterly_acc: dict[tuple, float] = defaultdict(float)
    annual_acc: dict[tuple, float] = defaultdict(float)

    # Deduplication: track seen (org_norm, monto_rounded, acto_norm) keys.
    # acto_norm=None rows are never deduplicated (can't identify reliably).
    seen_dedup_keys: set = set()

    if not dry_run:
        cur.execute("DELETE FROM ejecucion_presupuestaria")
        conn.commit()
        print("Cleared ejecucion_presupuestaria")

    inserted = 0
    matched = 0
    duplicates = 0
    match_stats: dict[str, int] = defaultdict(int)
    now_iso = datetime.utcnow().isoformat()

    for row in rows:
        fecha = parse_date(row["boletin_date"])
        if fecha is None:
            continue

        monto = float(row["monto_numerico"])
        org = row["organismo"] or ""
        org_norm = _normalize(org)

        # Deduplication check
        acto_norm = _normalize_acto(row.get("numero_acto"))
        key = _dedup_key(org_norm, monto, acto_norm)
        is_duplicate = 0
        if acto_norm is not None:
            if key in seen_dedup_keys:
                is_duplicate = 1
                duplicates += 1
            else:
                seen_dedup_keys.add(key)

        # Accumulate only for canonical rows — duplicates don't add to totals
        year = fecha.year
        month = fecha.month
        quarter = (month - 1) // 3 + 1

        if not is_duplicate:
            monthly_acc[(org_norm, year, month)] += monto
            quarterly_acc[(org_norm, year, quarter)] += monto
            annual_acc[(org_norm, year)] += monto

        # Match to presupuesto_base
        pb_id, score, method, programa, partida = match_organismo(org_norm, pb_index, pb_exact)
        if pb_id:
            matched += 1
            match_stats[method] += 1

        concepto = row["descripcion"] or (row["fragmento"] or "")[:200]
        beneficiario = first_beneficiario(row)
        riesgo = (row["riesgo"] or "").lower()
        requiere_revision = riesgo in ("alto", "medio")

        obs_parts = []
        if row.get("motivo_riesgo"):
            obs_parts.append(row["motivo_riesgo"])
        if method:
            obs_parts.append(f"match={method} score={score:.2f}")
        obs_parts.append(f"analisis_id={row['analisis_id']}")
        observaciones = " | ".join(obs_parts) if obs_parts else None

        if dry_run:
            inserted += 1
            continue

        cur.execute("""
            INSERT INTO ejecucion_presupuestaria (
                boletin_id, presupuesto_base_id, analisis_id,
                fecha_boletin, organismo, beneficiario, concepto,
                monto, tipo_operacion,
                partida_presupuestaria, programa,
                categoria_watcher, riesgo_watcher,
                etapa_gasto, jurisdiccion,
                monto_acumulado_mes, monto_acumulado_trimestre, monto_acumulado_anual,
                es_modificacion_presupuestaria, requiere_revision, observaciones,
                is_duplicate, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            row["boletin_id"],
            pb_id,
            row["analisis_id"],
            fecha.isoformat(),
            org[:200] if org else None,
            beneficiario,
            concepto[:500] if concepto else None,
            monto,
            row["tipo_acto"],
            partida,
            programa,
            row["categoria"],
            riesgo or None,
            row["etapa_gasto"],
            row["jurisdiccion_gasto"],
            monthly_acc[(org_norm, year, month)],
            quarterly_acc[(org_norm, year, quarter)],
            annual_acc[(org_norm, year)],
            0,  # es_modificacion_presupuestaria
            1 if requiere_revision else 0,
            observaciones,
            is_duplicate,
            now_iso,
        ))
        inserted += 1

        if inserted % 200 == 0:
            conn.commit()
            print(f"  ... {inserted} inserted")

    if not dry_run:
        conn.commit()

    conn.close()

    canonical = inserted - duplicates
    mode = "[DRY RUN] " if dry_run else ""
    print(f"\n{mode}RESUMEN ETL")
    print(f"  Rows procesados    : {len(rows)}")
    print(f"  Insertados         : {inserted}")
    print(f"  Duplicados         : {duplicates}")
    print(f"  Canónicos          : {canonical}")
    print(f"  Con match PB       : {matched} ({matched/max(inserted,1)*100:.1f}%)")
    print(f"  Sin match          : {inserted - matched}")
    print("  Match por método:")
    for method, count in sorted(match_stats.items(), key=lambda x: -x[1]):
        print(f"    {method:<12} {count}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run_etl(dry_run=dry_run)

"""
ETL: analisis → ejecucion_presupuestaria

Populates the budget execution table from analyzed administrative acts.
Attempts fuzzy organismo matching against presupuesto_base (ejercicio=2026).
Detects duplicate publications of the same acto (same tender published on
consecutive days) and marks them with is_duplicate=1; their monto is excluded
from the cumulative accumulators.

Usage:
    cd watcher-backend
    python scripts/etl_analisis_to_ejecucion.py [--dry-run]
"""

from __future__ import annotations

import sys
import re
import json
import unicodedata
import sqlite3
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent.parent / "sqlite.db"

# ── Normalización ──────────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    """Uppercase + strip accents + compress whitespace."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_str.upper().strip())


def _token_jaccard(a: str, b: str) -> float:
    """Jaccard similarity on word-token sets."""
    ta = set(a.split())
    tb = set(b.split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# ── Organismo matching ─────────────────────────────────────────────────────────

def build_presupuesto_index(cur) -> list[tuple[int, str, str, str | None]]:
    """Load presupuesto_base 2026 and return list of (id, org_norm, programa, partida)."""
    cur.execute(
        "SELECT id, organismo, programa, partida_presupuestaria FROM presupuesto_base WHERE ejercicio=2026"
    )
    return [(r[0], _normalize(r[1]), r[2], r[3]) for r in cur.fetchall()]


# Generic placeholder names in analisis that must not match any presupuesto_base organism
_ANALISIS_NO_MATCH = {"UNIDAD EJECUTORA", "N/A", "NO IDENTIFICADO", "DESCONOCIDO"}

# Explicit alias table: maps normalized analisis organismo → canonical presupuesto_base
# organismo name to use for matching.  Extend this dict whenever a new known variant
# appears in analisis that fuzzy matching fails or mis-routes.
#   str value  → use that name for matching against pb_index / pb_exact
#   None value → entity is outside the provincial central budget; skip matching
_ORGANISMO_ALIASES: dict[str, str | None] = {
    # ── Poder Judicial ────────────────────────────────────────────────────────
    # "PODER JUDICIAL" (len=14) scores 0.34 on substring against the longer
    # analisis forms — below the 0.40 threshold.  Force canonical form.
    "PODER JUDICIAL DE LA PROVINCIA DE CORDOBA": "PODER JUDICIAL",
    "PODER JUDICIAL DE CORDOBA": "PODER JUDICIAL",
    # Tribunal Superior de Justicia is part of the Poder Judicial branch and
    # was incorrectly matched to "TRIBUNAL DE CUENTAS" via Jaccard (score 0.40).
    "TRIBUNAL SUPERIOR DE JUSTICIA": "PODER JUDICIAL",
    "TRIBUNAL SUPERIOR DE JUSTICIA DE CORDOBA": "PODER JUDICIAL",
    "TSJ": "PODER JUDICIAL",
}


def match_organismo(
    org_norm: str,  # pre-normalized by caller
    pb_index: list[tuple[int, str, str, str | None]],
    pb_exact: dict[str, tuple[int, str, str | None]],
    threshold: float = 0.4,
) -> tuple[int | None, float, str | None, str | None, str | None]:
    """
    Returns (pb_id, score, method, programa, partida) or (None, 0, None, None, None).
    Methods: alias > exact > substring > jaccard
    pb_exact is a pre-built dict for O(1) exact lookups.
    """
    if not org_norm or org_norm in _ANALISIS_NO_MATCH:
        return None, 0.0, None, None, None

    # Alias override — applied before any fuzzy logic
    aliased = False
    if org_norm in _ORGANISMO_ALIASES:
        canonical = _ORGANISMO_ALIASES[org_norm]
        if canonical is None:
            return None, 0.0, None, None, None  # explicitly non-matchable
        org_norm = canonical
        aliased = True

    # O(1) exact match
    if org_norm in pb_exact:
        pb_id, programa, partida = pb_exact[org_norm]
        method = "alias+exact" if aliased else "exact"
        return pb_id, 1.0, method, programa, partida

    best = (None, 0.0, None, None, None)

    for pb_id, pb_norm, programa, partida in pb_index:
        # Substring match
        if org_norm in pb_norm or pb_norm in org_norm:
            score = min(len(org_norm), len(pb_norm)) / max(len(org_norm), len(pb_norm))
            if score > best[1]:
                best = (pb_id, score, "substring", programa, partida)
            continue

        # Token Jaccard
        jac = _token_jaccard(org_norm, pb_norm)
        if jac > best[1]:
            best = (pb_id, jac, "jaccard", programa, partida)

    if best[1] >= threshold:
        return best
    return None, 0.0, None, None, None


# ── Deduplicación ─────────────────────────────────────────────────────────────

# Placeholder acto numbers that carry no dedup information
# After whitespace removal, these become: N/A, NA, NOESPECIFICADO, SINNUMERO, NINGUNO
_ACTO_NO_DEDUP = {"N/A", "NA", "NOESPECIFICADO", "SINNUMERO", "NINGUNO"}


def _normalize_acto(s: str | None) -> str | None:
    """Normalize acto number for deduplication key. Returns None for empty/generic values."""
    if not s:
        return None
    norm = re.sub(r"\s+", "", s.upper().strip())
    if norm in _ACTO_NO_DEDUP or not norm:
        return None
    return norm


def _dedup_key(org_norm: str, monto: float, acto_norm: str | None) -> tuple:
    """
    Returns a hashable deduplication key.
    Rounds monto to nearest 1M to absorb floating-point noise between publications.
    acto_norm=None means we can't deduplicate this row by acto number.
    """
    return (org_norm, round(monto / 1e6), acto_norm)


# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_date(date_str: str) -> date | None:
    """Parse YYYYMMDD string to date."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y%m%d").date()
    except ValueError:
        return None


def first_beneficiario(analisis_row: dict) -> str | None:
    """Extract first beneficiary from json or entidad_beneficiaria fallback."""
    bj = analisis_row.get("beneficiarios_json")
    if isinstance(bj, list) and bj:
        return str(bj[0])[:200]
    if isinstance(bj, str):
        try:
            parsed = json.loads(bj)
            if isinstance(parsed, list) and parsed:
                return str(parsed[0])[:200]
        except (json.JSONDecodeError, TypeError):
            pass
    return analisis_row.get("entidad_beneficiaria") or None


def _ensure_is_duplicate_column(cur) -> None:
    """Add is_duplicate column if the table was created before this feature."""
    cur.execute("PRAGMA table_info(ejecucion_presupuestaria)")
    cols = {r[1] for r in cur.fetchall()}
    if "is_duplicate" not in cols:
        cur.execute(
            "ALTER TABLE ejecucion_presupuestaria ADD COLUMN is_duplicate INTEGER NOT NULL DEFAULT 0"
        )


# ── ETL main ───────────────────────────────────────────────────────────────────

def run_etl(dry_run: bool = False) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    _ensure_is_duplicate_column(cur)

    # Load presupuesto_base index + exact-match dict for O(1) lookups
    pb_index = build_presupuesto_index(cur)
    pb_exact = {pb_norm: (pb_id, programa, partida) for pb_id, pb_norm, programa, partida in pb_index}
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
            b.date          AS boletin_date
        FROM analisis a
        JOIN boletines b ON a.boletin_id = b.id
        WHERE a.monto_numerico > 0
        ORDER BY b.date, a.id
    """)
    rows = [dict(r) for r in cur.fetchall()]
    print(f"analisis rows with monto > 0: {len(rows)}")

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
                boletin_id, presupuesto_base_id,
                fecha_boletin, organismo, beneficiario, concepto,
                monto, tipo_operacion,
                partida_presupuestaria, programa,
                categoria_watcher, riesgo_watcher,
                monto_acumulado_mes, monto_acumulado_trimestre, monto_acumulado_anual,
                es_modificacion_presupuestaria, requiere_revision, observaciones,
                is_duplicate, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            row["boletin_id"],
            pb_id,
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

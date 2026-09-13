"""Shared organismo matching and acto deduplication primitives.

Single source of truth for the logic behind `scripts/etl_analisis_to_ejecucion.py`
(batch, sqlite3) and `app/services/ejecucion_ledger.py` (async, per boletin).
Both tiers must produce identical dedup keys, otherwise a boletin processed by
the pipeline and the same boletin reprocessed by the batch ETL would disagree on
which publication is canonical.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, datetime

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


def build_presupuesto_index(
    rows: list[tuple[int, str, str, str | None]],
) -> tuple[list[tuple[int, str, str, str | None]], dict[str, tuple[int, str, str | None]]]:
    """Build (pb_index, pb_exact) from raw (id, organismo, programa, partida) rows.

    pb_index keeps the normalized organismo for fuzzy passes; pb_exact gives O(1)
    exact lookups.  Callers fetch the rows however they like (sqlite3 cursor or
    SQLAlchemy) and hand them over already materialized.
    """
    pb_index = [(r[0], _normalize(r[1]), r[2], r[3]) for r in rows]
    pb_exact = {
        pb_norm: (pb_id, programa, partida) for pb_id, pb_norm, programa, partida in pb_index
    }
    return pb_index, pb_exact


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


# ── numero_acto extraction ─────────────────────────────────────────────────────

# Tender/acto identifiers as they appear in the Córdoba boletín.  Ordered by
# specificity: the tender code (S-511, 12/2026) is what gets republished verbatim
# across days, so it is the strongest dedup signal available.
_NUMERO_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "Licitación Pública N° S-511/2026", "Compulsa Abreviada Nro 12/2026"
    re.compile(
        r"(?:licitaci[oó]n\s+p[uú]blica|licitaci[oó]n\s+privada|licitaci[oó]n"
        r"|compulsa\s+abreviada|subasta\s+electr[oó]nica|concurso\s+de\s+precios"
        r"|contrataci[oó]n\s+directa|expediente)"
        r"[^\n]{0,40}?N[°ºro\.\s]{1,6}([A-Z]{0,3}-?\s?[\d.\-/]{2,20})",
        re.IGNORECASE,
    ),
    # "Obra: ... S-511" — bare tender code with the provincial S- prefix
    re.compile(r"\b(S-\s?\d{2,6}(?:/\d{2,4})?)\b", re.IGNORECASE),
    # "Decreto N° 456/2026", "Resolución Nº 1813"
    re.compile(
        r"(?:decreto|resoluci[oó]n|disposici[oó]n|acuerdo|ordenanza|ley)"
        r"[^\n]{0,30}?N[°ºro\.\s]{1,6}([\d.\-/]{1,20})",
        re.IGNORECASE,
    ),
)


def extract_numero_acto(*texts: str | None) -> str | None:
    """Best-effort acto identifier from raw acto text.

    Deterministic fallback for when the LLM omits `numero`: without it
    `_dedup_key` degrades to (organismo, monto) and republished tenders cannot be
    collapsed.  Scans each text in order and returns the first match.
    """
    for text in texts:
        if not text:
            continue
        snippet = text[:2000]
        for pattern in _NUMERO_PATTERNS:
            match = pattern.search(snippet)
            if not match:
                continue
            raw = re.sub(r"\s+", "", match.group(1)).strip(".-/")
            if len(raw) >= 2 and any(c.isdigit() for c in raw):
                return raw[:100]
    return None


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

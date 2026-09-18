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


# Tokens that appear in almost every provincial organism name.  A Jaccard of
# 0.40 on {DIRECCION, DE} vs {DIRECCION, DE, MINISTERIO} is how S-511 landed
# on Inteligencia Fiscal and how unrelated secretarías hung $50B off a $1.9B
# program.  Matching must score the distinctive remainder.
_STOPWORDS = {
    "DE", "DEL", "LA", "LAS", "EL", "LOS", "Y", "E", "PARA", "AL", "DA", "EN",
}
_GENERIC_ORG_TOKENS = {
    "MINISTERIO",
    "SECRETARIA",
    "DIRECCION",
    "SUBSECRETARIA",
    "GENERAL",
    "NACIONAL",
    "PROVINCIAL",
    "PROVINCIA",
    "CORDOBA",
    "UNIDAD",
    "JURISDICCION",
    "JUR",
}
_RE_TRAILING_HYPHEN = re.compile(r"[\s\-–—]+$")


def canonical_organismo(org_norm: str) -> str:
    """Collapse parser artifacts on an already-normalized organismo name."""
    if not org_norm:
        return ""
    s = _RE_TRAILING_HYPHEN.sub("", org_norm).strip(" -")
    tokens = s.split()
    out: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in _STOPWORDS:
            if out and out[-1] in _STOPWORDS:
                continue
            out.append(token)
            continue
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
    while out and out[-1] in _STOPWORDS:
        out.pop()
    return " ".join(out)


def canonical_organismo_name(name: str | None) -> str:
    """Normalize + collapse a raw organismo name into the grouping key."""
    return canonical_organismo(_normalize(name or ""))


def _distinctive_tokens(org_norm: str) -> set[str]:
    canon = canonical_organismo(org_norm)
    return {
        t for t in canon.split()
        if t not in _STOPWORDS and t not in _GENERIC_ORG_TOKENS
    }


def is_truncated_organismo(name: str | None) -> bool:
    """True when the name is a Mapas column stub, not a matchable organism."""
    canon = canonical_organismo_name(name)
    if not canon:
        return True
    if canon.endswith((" DE", " DEL", " Y")):
        return True
    return not _distinctive_tokens(canon)


def preferred_organismo_display(names: list[str]) -> str:
    """Pick a human-facing label for a canonical organism bucket."""
    if not names:
        return ""

    def rank(raw: str) -> tuple:
        stripped = raw.strip(" -–—")
        norm = _normalize(raw)
        trunc = is_truncated_organismo(norm)
        messy = canonical_organismo(norm) != norm
        return (trunc, messy, -len(stripped), stripped)

    return min(names, key=rank).strip(" -–—")


def _distinctive_jaccard(a: str, b: str) -> float:
    ta = _distinctive_tokens(a)
    tb = _distinctive_tokens(b)
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
    # ── EPEC (Ley 11.088 art. 11; jurisdicción 8.05, no está en Mapas Admin.) ─
    "EPEC": "EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA",
    "EPEC SAU": "EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA",
    "EMPRESA PROVINCIAL DE ENERGIA": "EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA",
    # ── ACIF (Ley 11.088 art. 15) ────────────────────────────────────────────
    "ACIF": "AGENCIA CORDOBA DE INVERSION Y FINANCIAMIENTO",
    # ── Policía ───────────────────────────────────────────────────────────────
    "POLICIA": "POLICIA DE LA PROVINCIA",
    "POLICIA DE LA PROVINCIA DE CORDOBA": "POLICIA DE LA PROVINCIA",
    "POLICIA DE CORDOBA": "POLICIA DE LA PROVINCIA",
    # ── Fuera del presupuesto provincial ─────────────────────────────────────
    "CCU": None,
    "CORDOBA CAPITAL": None,
    "MUNICIPALIDAD DE CORDOBA CAPITAL": None,
}

# Corporate suffixes and parentheticals the LLM appends to the same organism.
# Collapsing them lets "EPEC S.A.U. (EPEC)" share an alias/exact key with "EPEC".
_RE_ORG_PARENS = re.compile(r"\([^)]*\)")
_RE_ORG_SUFFIX = re.compile(r"\b(?:S\.?A\.?U\.?|S\.?E\.?M\.?|S\.?A\.?|S\.?R\.?L\.?)\b")


def _collapse_organismo(org_norm: str) -> str:
    """Strip legal suffixes and parentheticals from an already-normalized name."""
    if not org_norm:
        return ""
    collapsed = _RE_ORG_PARENS.sub(" ", org_norm)
    collapsed = _RE_ORG_SUFFIX.sub(" ", collapsed)
    return re.sub(r"\s+", " ", collapsed).strip(" .,-")


def _resolve_alias(org_norm: str) -> tuple[str, bool]:
    """Apply the alias table and the legal-suffix collapse to a normalized name.

    Shared by `match_organismo` and `_dedup_key` so both agree on when two
    spellings name the same organismo.  Returns (name, aliased); `name` is empty
    only when the alias table explicitly marks the entity as outside the
    provincial central budget.
    """
    collapsed = _collapse_organismo(org_norm)
    alias_key = org_norm if org_norm in _ORGANISMO_ALIASES else None
    if alias_key is None and collapsed in _ORGANISMO_ALIASES:
        alias_key = collapsed
    if alias_key is None:
        return (collapsed or org_norm), False
    canonical = _ORGANISMO_ALIASES[alias_key]
    if canonical is None:
        return "", True  # explicitly non-matchable
    return canonical, True


def build_presupuesto_index(
    rows: list[tuple[int, str, str, str | None]],
) -> tuple[list[tuple[int, str, str, str | None]], dict[str, tuple[int, str, str | None]]]:
    """Build (pb_index, pb_exact) from raw (id, organismo, programa, partida) rows.

    pb_index keeps the normalized organismo for fuzzy passes; pb_exact gives O(1)
    exact lookups.  Callers fetch the rows however they like (sqlite3 cursor or
    SQLAlchemy) and hand them over already materialized.
    """
    pb_index = [
        (r[0], canonical_organismo(_normalize(r[1])), r[2], r[3]) for r in rows
    ]
    pb_exact = {
        pb_norm: (pb_id, programa, partida)
        for pb_id, pb_norm, programa, partida in pb_index
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

    org_norm, aliased = _resolve_alias(org_norm)
    if not org_norm:
        return None, 0.0, None, None, None  # explicitly non-matchable

    org_norm = canonical_organismo(org_norm)

    # Truncated stubs ("MINISTERIO DE", "DIRECCION DE MINISTERIO") are not
    # organisms. Exact against them would keep the S-511 295% false positive.
    if is_truncated_organismo(org_norm):
        return None, 0.0, None, None, None

    # O(1) exact match
    if org_norm in pb_exact:
        pb_id, programa, partida = pb_exact[org_norm]
        method = "alias+exact" if aliased else "exact"
        return pb_id, 1.0, method, programa, partida

    best = (None, 0.0, None, None, None)

    for pb_id, pb_norm, programa, partida in pb_index:
        pb_norm = canonical_organismo(pb_norm)
        if not pb_norm or is_truncated_organismo(pb_norm):
            continue

        dist_q = _distinctive_tokens(org_norm)
        dist_t = _distinctive_tokens(pb_norm)
        if not dist_q or not dist_t or not (dist_q & dist_t):
            continue

        # Substring match
        if org_norm in pb_norm or pb_norm in org_norm:
            score = min(len(org_norm), len(pb_norm)) / max(len(org_norm), len(pb_norm))
            if score > best[1]:
                best = (pb_id, score, "substring", programa, partida)
            continue

        jac = _distinctive_jaccard(org_norm, pb_norm)
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


def _dedup_organismo(org_norm: str) -> str:
    """Organism component of the dedup key.

    Coarser than matching on purpose: it has to merge spellings of one organism
    ("...S.A.U (EPEC)" vs "...S.A.U"; "EPEC" vs "EMPRESA PROVINCIAL DE ENERGIA
    DE CORDOBA") without ever merging two distinct ones.  Keying on the raw name
    split one act into two canonical rows that both counted — the boletín
    republishes a tender the next day under a variant spelling and the organism
    was the only component of the key that changed.

    Entities the alias table marks as outside the provincial budget still get a
    stable key, so their own republications dedup among themselves.
    """
    name, _ = _resolve_alias(org_norm)
    base = name or _collapse_organismo(org_norm) or org_norm
    return canonical_organismo(base)


def _dedup_key(org_norm: str, monto: float, acto_norm: str | None) -> tuple:
    """
    Returns a hashable deduplication key.
    Rounds monto to nearest 1M to absorb floating-point noise between publications.
    acto_norm=None means we can't deduplicate this row by acto number.
    """
    return (_dedup_organismo(org_norm), round(monto / 1e6), acto_norm)


# ── Obra-code dedup tier ───────────────────────────────────────────────────────

# Public-works codes the boletín republishes verbatim while a tender is open:
# "camino S-511", "tramo T294-06".  They survive the republication even when the
# acto number changes (an "Apertura de registro de oposición" cites the obra code
# and a resolución number instead of the original tender number), which is the one
# case the (organismo, monto, acto) key cannot reach.
#
# Deliberately narrow.  A looser "same monto + similar text" rule would merge
# EPEC's ZONA III SUROESTE with ZONA IV SURESTE — identical amount, near-identical
# wording, different tenders.  A code that only exists when the boletín names the
# obra does not have that failure mode.
_RE_OBRA_CODE = re.compile(r"\b(S-\s?\d{2,6}(?:/\d{2,4})?)\b", re.IGNORECASE)
_RE_TRAMO_CODE = re.compile(r"\b(T\d{2,4}-\d{2})\b", re.IGNORECASE)


def extract_obra_code(*texts: str | None) -> str | None:
    """Return the public-works code named in the text, if any."""
    for pattern in (_RE_OBRA_CODE, _RE_TRAMO_CODE):
        for text in texts:
            if not text:
                continue
            match = pattern.search(text[:2000])
            if match:
                return re.sub(r"\s+", "", match.group(1)).upper()
    return None


def _obra_key(obra_code: str, monto: float) -> tuple:
    return ("OBRA", obra_code, round(monto / 1e6))


def dedup_keys(
    org_norm: str,
    monto: float,
    acto_norm: str | None,
    *texts: str | None,
) -> list[tuple]:
    """Every key that identifies this act.  A row is a duplicate if any matches.

    Empty list means the row carries no stable identity and must not dedup.
    """
    keys: list[tuple] = []
    if acto_norm is not None:
        keys.append(_dedup_key(org_norm, monto, acto_norm))
    obra_code = extract_obra_code(*texts)
    if obra_code is not None:
        keys.append(_obra_key(obra_code, monto))
    return keys


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

    Deterministic fallback for when the LLM omits `numero` or returns a bare
    publication ID: without a stable identifier `_dedup_key` cannot collapse
    republished tenders.  Patterns are tried most-specific first, so a tender
    code wins over a generic "Resolución N° 56".
    """
    for pattern in _NUMERO_PATTERNS:
        for text in texts:
            if not text:
                continue
            match = pattern.search(text[:2000])
            if not match:
                continue
            raw = re.sub(r"\s+", "", match.group(1)).strip(".-/")
            if len(raw) >= 2 and any(c.isdigit() for c in raw):
                return raw[:100]
    return None


# A bare run of digits with no year, separator or prefix.  The Córdoba boletín
# uses these as per-publication IDs, so the same tender carries a different one
# each day it is republished ("646961" then "645803") and using it as the dedup
# key splits one acto into several canonical ledger rows.
_RE_BARE_PUBLICATION_ID = re.compile(r"^\d{5,9}$")


def looks_like_publication_id(numero: str | None) -> bool:
    """True when `numero` carries no stable acto identity."""
    if not numero:
        return False
    return bool(_RE_BARE_PUBLICATION_ID.match(re.sub(r"\s+", "", numero.strip())))


def resolve_numero_acto(numero: str | None, *texts: str | None) -> str | None:
    """Pick the most stable acto identifier available.

    A structured identifier from the LLM wins outright.  A bare publication ID
    is only kept when the text yields nothing better: it still beats `None`,
    which disables dedup altogether, and it can never merge two distinct actos.
    """
    candidate = (numero or "").strip() or None
    if candidate and not looks_like_publication_id(candidate):
        return candidate[:100]

    recovered = extract_numero_acto(*texts)
    if recovered:
        return recovered
    return candidate[:100] if candidate else None


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

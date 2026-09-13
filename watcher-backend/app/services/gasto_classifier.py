"""Rules-based classification of an acto as public spending (P.7.1).

The raw sum of `analisis.monto_numerico` is not public spending: it mixes tender
calls, re-publications, judicial auctions, corporate filings and budget line
transfers.  This module decides, per acto, whether it belongs in the spending
ledger at all, at which stage of the spending cycle it sits, and against which
jurisdiction's budget it should be counted.

Rules only — no LLM call.  Signals used: `tipo_acto`, the boletín section, and
keywords over the acto text.

Two distinctions drive everything downstream:

- A tender call (`llamado`) is a *commitment*, not a payment.  A transfer or
  subsidy (`pago`) is *execution*.  The UI must never add them into one bar.
- A budget line transfer (`modificacion`) moves the ceiling without spending
  anything, so it is not spending even though it carries a large monto.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# ── Etapas del ciclo de gasto ──────────────────────────────────────────────────

ETAPA_LLAMADO = "llamado"
ETAPA_ADJUDICACION = "adjudicacion"
ETAPA_CONTRATO = "contrato"
ETAPA_PAGO = "pago"
ETAPA_MODIFICACION = "modificacion"
ETAPA_NO_APLICA = "no_aplica"

ETAPAS_GASTO = (
    ETAPA_LLAMADO,
    ETAPA_ADJUDICACION,
    ETAPA_CONTRATO,
    ETAPA_PAGO,
    ETAPA_MODIFICACION,
    ETAPA_NO_APLICA,
)

# Etapas that commit budget without disbursing it
ETAPAS_COMPROMISO = (ETAPA_LLAMADO, ETAPA_ADJUDICACION, ETAPA_CONTRATO)
# Etapas that actually disburse
ETAPAS_EJECUCION = (ETAPA_PAGO,)

# ── Jurisdicciones ─────────────────────────────────────────────────────────────

JURISDICCION_PROVINCIAL = "provincial"
JURISDICCION_MUNICIPAL = "municipal"
JURISDICCION_FUERA = "fuera_presupuesto"

JURISDICCIONES = (JURISDICCION_PROVINCIAL, JURISDICCION_MUNICIPAL, JURISDICCION_FUERA)

# ── Secciones del boletín provincial ───────────────────────────────────────────

SECCION_LEGISLACION = 1
SECCION_JUDICIAL = 2
SECCION_SOCIEDADES = 3
SECCION_LICITACIONES = 4
SECCION_MUNICIPAL = 5

# Sections whose content is structurally outside the provincial budget:
# S2 is judicial (edictos, remates, ejecuciones fiscales) and S3 is private
# corporate filings (capital, escisiones, asambleas).
_SECCIONES_NO_GASTO = {SECCION_JUDICIAL, SECCION_SOCIEDADES}


def _parse_section(section: Any) -> int | None:
    """Normalize the many shapes of `boletines.section` to 1-5.

    Seen in the wild: "1".."5" (current provincial rows), "S1".."S5" (older
    fixtures), "1_Secc" (scraper config), 4 (int).
    """
    if section is None:
        return None
    if isinstance(section, int):
        return section if 1 <= section <= 5 else None
    match = re.search(r"\d", str(section))
    if not match:
        return None
    value = int(match.group())
    return value if 1 <= value <= 5 else None


# ── Keyword sets ───────────────────────────────────────────────────────────────
#
# All patterns run against accent-stripped text (see `_strip_accents`).  Boletín
# text is inconsistent about accents and PDF extraction drops them, so matching
# "adjudicase" once beats spelling out "adjud[ií]c" in every pattern.

# Budget line transfers: they move the ceiling, they do not pay anyone.
_RE_MODIFICACION = re.compile(
    r"compensacion\s+de\s+(?:partidas|creditos)"
    r"|incremento\s+de\s+partidas"
    r"|modificacion\s+(?:del\s+)?presupuestaria"
    r"|modificacion\s+de\s+partidas"
    r"|reasignacion\s+de\s+(?:partidas|creditos)"
    r"|adecuacion\s+de\s+partidas"
    r"|ampliacion\s+de\s+partidas"
    r"|transferencia\s+de\s+partidas"
    r"|refuerzo\s+presupuestario",
    re.IGNORECASE,
)

# Judicial acts: notifications and asset auctions, never provincial spending.
# "subasta" alone is not enough — "subasta electrónica" is a procurement method.
_RE_JUDICIAL = re.compile(
    r"\bremate\b"
    r"|subasta\s+judicial"
    r"|ejecucion\s+fiscal"
    r"|\bmartiller[oa]\b"
    r"|\bedicto\b"
    r"|cita\s+y\s+emplaza"
    r"|concurso\s+preventivo"
    r"|\bquiebra\b"
    r"|\busucapion\b"
    r"|juicio\s+sucesorio"
    r"|declaratoria\s+de\s+herederos",
    re.IGNORECASE,
)

# Private corporate filings published in S3.
_RE_SOCIETARIO = re.compile(
    r"aumento\s+de\s+capital"
    r"|capital\s+social"
    r"|\bescision\b"
    r"|fusion\s+por\s+absorcion"
    r"|cesion\s+de\s+cuotas"
    r"|transformacion\s+societaria"
    r"|disolucion\s+(?:y\s+liquidacion|de\s+la\s+sociedad)"
    r"|reforma\s+de\s+estatuto"
    r"|asamblea\s+(?:general\s+)?(?:ordinaria|extraordinaria)"
    r"|designacion\s+de\s+autoridades",
    re.IGNORECASE,
)

_RE_ADJUDICACION = re.compile(r"adjudic|preadjudic", re.IGNORECASE)

_RE_CONTRATO = re.compile(
    r"contratacion\s+directa"
    r"|\bcontrato\b"
    r"|\bconvenio\b"
    r"|prorroga\s+de\s+contrato"
    r"|redeterminacion\s+de\s+precios"
    r"|ampliacion\s+de\s+obra",
    re.IGNORECASE,
)

_RE_PAGO = re.compile(
    r"\bsubsidio\b"
    r"|\btransferencia\b"
    r"|aporte\s+no\s+reintegrable"
    r"|\bpaguese\b"
    r"|autoriz\w*\s+(?:el\s+)?pago"
    r"|orden\s+de\s+pago"
    r"|\blibrese\b"
    r"|\bdevengad[oa]\b"
    r"|\babonar\b",
    re.IGNORECASE,
)

_RE_LLAMADO = re.compile(
    r"licitacion"
    r"|llama[sd]e?\s+a"
    r"|llamado\s+a"
    r"|\bpliego\b"
    r"|compulsa\s+abreviada"
    r"|concurso\s+de\s+precios"
    r"|subasta\s+electronica"
    r"|apertura\s+de\s+(?:las\s+)?ofertas"
    r"|presupuesto\s+oficial",
    re.IGNORECASE,
)

_RE_MUNICIPAL = re.compile(
    r"municipalidad|municipio|\bcomuna\b|concejo\s+deliberante|\bordenanza\b",
    re.IGNORECASE,
)

# tipo_acto values that are payments by nature
_TIPOS_PAGO = {"subsidio", "transferencia"}
# tipo_acto values that are tender calls by nature
_TIPOS_LLAMADO = {"licitacion"}


@dataclass(frozen=True)
class GastoClassification:
    """Outcome of classifying one acto."""

    is_gasto_publico: bool
    etapa_gasto: str
    jurisdiccion: str
    motivo: str

    def as_analisis_fields(self) -> dict[str, Any]:
        """Shape expected by `Analisis` / `create_analisis`."""
        return {
            "is_gasto_publico": self.is_gasto_publico,
            "etapa_gasto": self.etapa_gasto,
            "jurisdiccion_gasto": self.jurisdiccion,
        }

    @property
    def cuenta_contra_presupuesto_provincial(self) -> bool:
        """Whether this acto may sum into the provincial accumulators."""
        return self.is_gasto_publico and self.jurisdiccion == JURISDICCION_PROVINCIAL


def _strip_accents(s: str) -> str:
    """Drop diacritics so patterns match 'adjudicase' and 'adjudícase' alike."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _haystack(acto: Mapping[str, Any]) -> str:
    """Concatenate the acto text fields the keyword rules run over."""
    parts = [
        acto.get("descripcion"),
        acto.get("texto_original"),
        acto.get("relacion_principal"),
        acto.get("fragmento"),
        acto.get("organismo"),
    ]
    joined = " \n ".join(str(p) for p in parts if p)
    return _strip_accents(joined[:4000])


def _classify_jurisdiccion(section: int | None, text: str) -> str:
    if section in _SECCIONES_NO_GASTO:
        return JURISDICCION_FUERA
    if section == SECCION_MUNICIPAL:
        return JURISDICCION_MUNICIPAL
    if _RE_MUNICIPAL.search(text):
        return JURISDICCION_MUNICIPAL
    return JURISDICCION_PROVINCIAL


def _classify_etapa(tipo_acto: str, text: str) -> tuple[str, str]:
    """Return (etapa, motivo) for an acto already known to be spending-like.

    Precedence is by position in the spending cycle, latest stage first: an acto
    that adjudicates a tender is an `adjudicacion` even though its text still
    says "Licitación Pública".  `tipo_acto` wins for payments because the LLM
    field is more reliable there than keyword soup.
    """
    if tipo_acto in _TIPOS_PAGO:
        return ETAPA_PAGO, f"tipo_acto={tipo_acto}"
    if _RE_ADJUDICACION.search(text):
        return ETAPA_ADJUDICACION, "keyword adjudicacion"
    if _RE_CONTRATO.search(text):
        return ETAPA_CONTRATO, "keyword contrato"
    if _RE_PAGO.search(text):
        return ETAPA_PAGO, "keyword pago"
    if _RE_LLAMADO.search(text) or tipo_acto in _TIPOS_LLAMADO:
        return ETAPA_LLAMADO, "keyword llamado"
    return ETAPA_NO_APLICA, "sin señal de gasto"


def classify_gasto(
    acto: Mapping[str, Any],
    section: Any = None,
) -> GastoClassification:
    """Classify one acto for the spending ledger.

    `acto` accepts either the LLM extraction dict or a row-like mapping from
    `analisis`; it reads `tipo_acto`, `descripcion`, `texto_original`,
    `relacion_principal`, `fragmento` and `organismo`, all optional.
    `section` is `boletines.section` in any of its observed shapes.

    Actos with no recognizable spending signal default to
    `is_gasto_publico=False`: the ledger is a claim about public money, so an
    unclassifiable acto stays out of it rather than inflating the total.
    """
    sec = _parse_section(section)
    text = _haystack(acto)
    tipo_acto = str(acto.get("tipo_acto") or "").strip().lower()
    jurisdiccion = _classify_jurisdiccion(sec, text)

    # Budget line transfers first: they can appear in S1 legislation and would
    # otherwise read as spending via "transferencia".
    if _RE_MODIFICACION.search(text):
        return GastoClassification(
            is_gasto_publico=False,
            etapa_gasto=ETAPA_MODIFICACION,
            jurisdiccion=jurisdiccion,
            motivo="modificacion de partidas: mueve el techo, no paga",
        )

    if _RE_JUDICIAL.search(text):
        return GastoClassification(
            is_gasto_publico=False,
            etapa_gasto=ETAPA_NO_APLICA,
            jurisdiccion=JURISDICCION_FUERA,
            motivo="acto judicial (edicto/remate/ejecucion fiscal)",
        )

    if _RE_SOCIETARIO.search(text):
        return GastoClassification(
            is_gasto_publico=False,
            etapa_gasto=ETAPA_NO_APLICA,
            jurisdiccion=JURISDICCION_FUERA,
            motivo="acto societario privado (capital/escision/asamblea)",
        )

    if sec in _SECCIONES_NO_GASTO:
        return GastoClassification(
            is_gasto_publico=False,
            etapa_gasto=ETAPA_NO_APLICA,
            jurisdiccion=JURISDICCION_FUERA,
            motivo=f"seccion {sec} fuera del presupuesto provincial",
        )

    etapa, motivo = _classify_etapa(tipo_acto, text)
    return GastoClassification(
        is_gasto_publico=etapa != ETAPA_NO_APLICA,
        etapa_gasto=etapa,
        jurisdiccion=jurisdiccion,
        motivo=motivo,
    )

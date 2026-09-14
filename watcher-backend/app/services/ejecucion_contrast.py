"""Contrast ledger spending against presupuesto_base.monto_vigente (P.7.4).

The boletín publishes commitments (tender calls, awards, contracts) far more
often than payments.  Mixing them into one percentage against the Ley would
read as if Córdoba had already spent the money.  This module buckets each
canonical ledger row and computes two independent ratios:

    pct_compromiso = compromiso / monto_vigente
    pct_ejecucion  = pago       / monto_vigente

A ratio above 100% is an alert, not a crash: the ledger is a floor of what
was published, matching is fuzzy, and a false-positive organismo can blow
past the ceiling.  Callers decide how to render that.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.services.gasto_classifier import ETAPAS_COMPROMISO, ETAPAS_EJECUCION

BUCKET_COMPROMISO = "compromiso"
BUCKET_EJECUCION = "ejecucion"
BUCKET_OTRO = "otro"


def bucket_etapa(etapa: str | None) -> str:
    """Map an `etapa_gasto` value to compromiso / ejecucion / otro."""
    if etapa in ETAPAS_COMPROMISO:
        return BUCKET_COMPROMISO
    if etapa in ETAPAS_EJECUCION:
        return BUCKET_EJECUCION
    return BUCKET_OTRO


def pct_vs_vigente(numerador: float, vigente: float | None) -> float | None:
    """Return 100 * numerador / vigente, or None when there is no denominator."""
    if vigente is None or vigente <= 0:
        return None
    return round(100.0 * numerador / vigente, 2)


def is_sobre(pct: float | None, umbral: float = 100.0) -> bool:
    return pct is not None and pct > umbral


@dataclass(frozen=True)
class OrganismoContrast:
    organismo: str
    count: int
    monto_total: float
    monto_compromiso: float
    monto_ejecucion: float
    monto_vigente: float | None
    pct_compromiso: float | None
    pct_ejecucion: float | None
    sobre_compromiso: bool
    sobre_ejecucion: bool
    matched: bool


def aggregate_organismos(
    rows: list[tuple[str | None, str | None, float, int]],
    vigente_por_org: dict[str, float],
) -> list[OrganismoContrast]:
    """Fold (organismo, etapa, monto, count) rows into per-organismo contrast.

    `organismo` should already be the presupuesto_base name when the row
    matched, otherwise the ledger name.  Results are sorted by compromiso
    descending — that is 99% of what the boletín publishes.
    """
    acc: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "count": 0.0,
            BUCKET_COMPROMISO: 0.0,
            BUCKET_EJECUCION: 0.0,
            BUCKET_OTRO: 0.0,
        }
    )
    for org, etapa, monto, count in rows:
        key = org or "(sin organismo)"
        bucket = bucket_etapa(etapa)
        acc[key]["count"] += count
        acc[key][bucket] += monto

    out: list[OrganismoContrast] = []
    for org, vals in acc.items():
        compromiso = vals[BUCKET_COMPROMISO]
        ejecucion = vals[BUCKET_EJECUCION]
        total = compromiso + ejecucion + vals[BUCKET_OTRO]
        vigente = vigente_por_org.get(org)
        matched = org in vigente_por_org
        pct_c = pct_vs_vigente(compromiso, vigente if matched else None)
        pct_e = pct_vs_vigente(ejecucion, vigente if matched else None)
        out.append(
            OrganismoContrast(
                organismo=org,
                count=int(vals["count"]),
                monto_total=total,
                monto_compromiso=compromiso,
                monto_ejecucion=ejecucion,
                monto_vigente=vigente if matched else None,
                pct_compromiso=pct_c,
                pct_ejecucion=pct_e,
                sobre_compromiso=is_sobre(pct_c),
                sobre_ejecucion=is_sobre(pct_e),
                matched=matched,
            )
        )
    out.sort(key=lambda item: item.monto_compromiso, reverse=True)
    return out

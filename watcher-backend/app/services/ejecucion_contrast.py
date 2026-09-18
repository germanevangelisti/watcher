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
from collections.abc import Iterable
from dataclasses import dataclass

from app.services.gasto_classifier import (
    ETAPA_LLAMADO,
    ETAPAS_COMPROMISO,
    ETAPAS_EJECUCION,
)
from app.services.presupuesto_matching import (
    canonical_organismo_name,
    preferred_organismo_display,
)

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


def vigente_por_organismo_canonico(
    rows: Iterable[tuple[str | None, float]],
) -> tuple[dict[str, float], dict[str, str]]:
    """Sum vigente by canonical organism; return (display→vigente, canon→display).

    `PODER JUDICIAL` and `PODER JUDICIAL -` share a bucket.  Truncated stubs
    like `MINISTERIO DE` stay in their own bucket and are not a match target.
    """
    names_by_canon: dict[str, list[str]] = defaultdict(list)
    totals: dict[str, float] = defaultdict(float)
    for org, vigente in rows:
        if not org:
            continue
        key = canonical_organismo_name(org)
        if not key:
            continue
        totals[key] += vigente
        names_by_canon[key].append(org)
    display_by_canon = {
        key: preferred_organismo_display(names) for key, names in names_by_canon.items()
    }
    vigente_por_org = {
        display_by_canon[key]: total for key, total in totals.items()
    }
    return vigente_por_org, display_by_canon


def remap_organismo_key(
    raw: str | None, display_by_canon: dict[str, str]
) -> str:
    """Map a ledger/presupuesto name onto the contrast display key."""
    if not raw:
        return "(sin organismo)"
    key = canonical_organismo_name(raw)
    return display_by_canon.get(key, raw)


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
    # Portion of `monto_compromiso` that is only a tender call.  Disclosed, not
    # subtracted: the published pct and the alert keep their V.2 definition, so
    # separating the series cannot silently retire an alert.
    monto_llamado: float = 0.0


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
            "llamado": 0.0,
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
        if etapa == ETAPA_LLAMADO:
            acc[key]["llamado"] += monto

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
                monto_llamado=vals["llamado"],
            )
        )
    out.sort(key=lambda item: item.monto_compromiso, reverse=True)
    return out


@dataclass(frozen=True)
class Cobertura:
    """How much of the measured spend has a denominator to be measured against.

    The contrast can only state a percentage where `presupuesto_base` has a
    matching organism; everything else is publication without a ceiling.  The
    ledger is not wrong about that spend — it just cannot be contrasted, and the
    UI must say so rather than drop it from the list.
    """

    monto_total: float
    monto_con_denominador: float
    monto_sin_denominador: float
    count_sin_denominador: int
    pct_sin_denominador: float


def aggregate_cobertura(contrast: Iterable[OrganismoContrast]) -> Cobertura:
    """Coverage over an already-aggregated contrast (no extra query needed)."""
    total = con = sin = 0.0
    count_sin = 0
    for item in contrast:
        total += item.monto_total
        if item.matched:
            con += item.monto_total
        else:
            sin += item.monto_total
            count_sin += item.count
    pct = round(100.0 * sin / total, 2) if total > 0 else 0.0
    return Cobertura(
        monto_total=total,
        monto_con_denominador=con,
        monto_sin_denominador=sin,
        count_sin_denominador=count_sin,
        pct_sin_denominador=pct,
    )


@dataclass(frozen=True)
class CoberturaTemporal:
    """The period the numerator covers, and what it is actually divided by.

    `presupuesto_base` holds the whole year's Ley, so a percentage built from
    three months of boletines is divided by twelve.  That makes it incomparable
    rather than wrong, and the caller has to say which it is.  Nothing here
    prorates the Ley: budget execution is not uniform across the year, so a
    prorated denominator would be an invented one.

    Months outside the span are split by whether they are *due* yet.  A month
    that has not happened is not missing data, and lumping it in with May —
    which is overdue — would overstate the gap.
    """

    mes_desde: str | None
    mes_hasta: str | None
    meses_cubiertos: int
    meses_del_ejercicio: int
    meses_vencidos_sin_ingesta: tuple[str, ...]
    meses_futuros: tuple[str, ...]
    dias_con_publicacion: int
    dias_justificados: int
    dias_faltantes: int
    denominador_es_anual: bool


# A boletín that never came out (holiday, HTTP 404) is recorded as failed with
# this prefix instead of silently counting as a day of zero spending.
_JUSTIFIED_PREFIX = "justified:"


def aggregate_cobertura_temporal(
    rows: Iterable[tuple[str | None, str | None, str | None]],
    ejercicio: int,
    mes_desde: str | None = None,
    mes_hasta: str | None = None,
    mes_actual: str | None = None,
) -> CoberturaTemporal:
    """Summarize the publication calendar behind the numerator.

    `rows` are (date, status, error_message) as stored in `boletines`.  A day is
    *published* when any of its sections completed, *justified* when none did but
    every failure says so, and *missing* otherwise — a real gap, which is the
    only case that understates the numerator without saying so.
    """
    from collections import defaultdict

    by_day: dict[str, list[tuple[str | None, str | None]]] = defaultdict(list)
    for date, status, error in rows:
        if date:
            by_day[date].append((status, error))

    con_publicacion = justificados = faltantes = 0
    for sections in by_day.values():
        if any(status == "completed" for status, _ in sections):
            con_publicacion += 1
        elif sections and all(
            (error or "").startswith(_JUSTIFIED_PREFIX) for _, error in sections
        ):
            justificados += 1
        else:
            faltantes += 1

    meses_cubiertos = 0
    vencidos: list[str] = []
    futuros: list[str] = []
    if mes_desde and mes_hasta:
        cubiertos = {
            f"{ejercicio:04d}-{m:02d}"
            for m in range(int(mes_desde[5:7]), int(mes_hasta[5:7]) + 1)
        }
        meses_cubiertos = len(cubiertos)
        for m in range(1, 13):
            mes = f"{ejercicio:04d}-{m:02d}"
            if mes in cubiertos:
                continue
            if mes_actual is not None and mes > mes_actual:
                futuros.append(mes)
            else:
                vencidos.append(mes)

    return CoberturaTemporal(
        mes_desde=mes_desde,
        mes_hasta=mes_hasta,
        meses_cubiertos=meses_cubiertos,
        meses_del_ejercicio=12,
        meses_vencidos_sin_ingesta=tuple(vencidos),
        meses_futuros=tuple(futuros),
        dias_con_publicacion=con_publicacion,
        dias_justificados=justificados,
        dias_faltantes=faltantes,
        denominador_es_anual=True,
    )

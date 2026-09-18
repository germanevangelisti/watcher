"""Incremental spending ledger, written when a boletín finishes the pipeline (P.7.2).

`scripts/etl_analisis_to_ejecucion.py` rebuilds `ejecucion_presupuestaria` for the
whole corpus in one batch pass.  This module does the same work for a single
boletín so the ledger is live and no manual ETL run is needed after ingestion.

Both paths share `presupuesto_matching`, so a boletín written here and the same
boletín rewritten by the batch ETL agree on which publication is canonical.

Invariants:
- Only actos with `is_gasto_publico` reach the ledger; remates, corporate
  filings and budget line transfers are excluded upstream by `gasto_classifier`.
- A republished acto is stored with `is_duplicate=1` and does not add to
  `monto_acumulado_*`.
- Re-running for the same boletín replaces its rows instead of appending.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime

from app.db.models import Analisis, Boletin, EjecucionPresupuestaria, PresupuestoBase
from app.services.gasto_classifier import (
    JURISDICCION_PROVINCIAL,
    classify_gasto,
)
from app.services.presupuesto_matching import (
    _normalize,
    _normalize_acto,
    build_presupuesto_index,
    dedup_keys,
    first_beneficiario,
    match_organismo,
    parse_date,
    resolve_numero_acto,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class LedgerResult:
    """Outcome of writing the ledger for one boletín."""

    boletin_id: int
    rows_written: int = 0
    duplicates: int = 0
    matched_presupuesto: int = 0
    skipped_no_gasto: int = 0
    classified: int = 0
    motivo_skip: dict[str, int] = field(default_factory=dict)

    @property
    def canonical(self) -> int:
        return self.rows_written - self.duplicates

    def as_dict(self) -> dict:
        return {
            "boletin_id": self.boletin_id,
            "rows_written": self.rows_written,
            "canonical": self.canonical,
            "duplicates": self.duplicates,
            "matched_presupuesto": self.matched_presupuesto,
            "skipped_no_gasto": self.skipped_no_gasto,
            "classified": self.classified,
        }


def _quarter(month: int) -> int:
    return (month - 1) // 3 + 1


async def _load_presupuesto_index(db: AsyncSession, ejercicio: int):
    result = await db.execute(
        select(
            PresupuestoBase.id,
            PresupuestoBase.organismo,
            PresupuestoBase.programa,
            PresupuestoBase.partida_presupuestaria,
        ).where(PresupuestoBase.ejercicio == ejercicio)
    )
    return build_presupuesto_index([tuple(r) for r in result.all()])


async def _load_seen_dedup_keys(db: AsyncSession, boletin_id: int) -> set[tuple]:
    """Dedup keys already claimed by canonical ledger rows of *other* boletines.

    Joined back to `analisis` because `numero_acto` lives there; rows written
    before `analisis_id` existed simply contribute no key.
    """
    result = await db.execute(
        select(
            Analisis.organismo,
            Analisis.numero_acto,
            EjecucionPresupuestaria.monto,
            EjecucionPresupuestaria.concepto,
        )
        .join(Analisis, Analisis.id == EjecucionPresupuestaria.analisis_id)
        .where(
            EjecucionPresupuestaria.is_duplicate == 0,
            EjecucionPresupuestaria.boletin_id != boletin_id,
        )
    )
    seen: set[tuple] = set()
    for organismo, numero_acto, monto, concepto in result.all():
        if monto is None:
            continue
        acto_norm = _normalize_acto(numero_acto)
        seen.update(
            dedup_keys(_normalize(organismo or ""), float(monto), acto_norm, concepto)
        )
    return seen


async def _load_accumulators(
    db: AsyncSession, fecha: date, boletin_id: int
) -> tuple[dict, dict, dict]:
    """Canonical totals per organismo recorded up to and including `fecha`.

    Bounded at `fecha` rather than the whole year so `monto_acumulado_*` keeps
    its cumulative-to-date meaning: re-running an old boletín must not fold in
    spending published after it.  This is also what the batch ETL produces,
    since it walks boletines in date order.

    Excludes `boletin_id` so a re-run of the same boletín does not double count
    its own previous rows.
    """
    result = await db.execute(
        select(
            EjecucionPresupuestaria.organismo,
            EjecucionPresupuestaria.fecha_boletin,
            EjecucionPresupuestaria.monto,
        ).where(
            EjecucionPresupuestaria.is_duplicate == 0,
            EjecucionPresupuestaria.boletin_id != boletin_id,
            EjecucionPresupuestaria.fecha_boletin >= date(fecha.year, 1, 1),
            EjecucionPresupuestaria.fecha_boletin <= fecha,
        )
    )
    monthly: dict = defaultdict(float)
    quarterly: dict = defaultdict(float)
    annual: dict = defaultdict(float)

    for organismo, fecha, monto in result.all():
        if fecha is None or monto is None:
            continue
        org_norm = _normalize(organismo or "")
        monthly[(org_norm, fecha.year, fecha.month)] += float(monto)
        quarterly[(org_norm, fecha.year, _quarter(fecha.month))] += float(monto)
        annual[(org_norm, fecha.year)] += float(monto)

    return monthly, quarterly, annual


def _ensure_classification(acto: Analisis, section) -> bool:
    """Backfill classification on an acto that predates P.7.1. Returns True if set."""
    if acto.is_gasto_publico is not None and acto.etapa_gasto:
        return False
    classification = classify_gasto(
        {
            "tipo_acto": acto.tipo_acto,
            "descripcion": acto.descripcion,
            "fragmento": acto.fragmento,
            "organismo": acto.organismo,
        },
        section=section,
    )
    acto.is_gasto_publico = classification.is_gasto_publico
    acto.etapa_gasto = classification.etapa_gasto
    acto.jurisdiccion_gasto = classification.jurisdiccion
    return True


async def upsert_boletin_ejecucion(db: AsyncSession, boletin_id: int) -> LedgerResult:
    """Rebuild `ejecucion_presupuestaria` for one boletín.

    Safe to call repeatedly: the boletín's existing rows are deleted first, and
    accumulators and dedup keys are read from the other boletines only.
    Does not commit — the caller owns the transaction.
    """
    result = LedgerResult(boletin_id=boletin_id)

    boletin = (
        await db.execute(select(Boletin).where(Boletin.id == boletin_id))
    ).scalar_one_or_none()
    if boletin is None:
        logger.warning("Ledger: boletin %s no existe", boletin_id)
        return result

    fecha = parse_date(boletin.date or "")
    if fecha is None:
        logger.warning("Ledger: boletin %s sin fecha parseable (%r)", boletin_id, boletin.date)
        return result

    await db.execute(
        delete(EjecucionPresupuestaria).where(
            EjecucionPresupuestaria.boletin_id == boletin_id
        )
    )
    await db.flush()

    actos = (
        (
            await db.execute(
                select(Analisis)
                .where(Analisis.boletin_id == boletin_id)
                .order_by(Analisis.id)
            )
        )
        .scalars()
        .all()
    )
    if not actos:
        return result

    pb_index, pb_exact = await _load_presupuesto_index(db, fecha.year)
    seen_dedup_keys = await _load_seen_dedup_keys(db, boletin_id)
    monthly_acc, quarterly_acc, annual_acc = await _load_accumulators(db, fecha, boletin_id)

    month = fecha.month
    quarter = _quarter(month)
    now = datetime.utcnow()

    for acto in actos:
        if _ensure_classification(acto, boletin.section):
            result.classified += 1

        monto = float(acto.monto_numerico or 0.0)
        if monto <= 0:
            continue
        if not acto.is_gasto_publico:
            result.skipped_no_gasto += 1
            key = acto.etapa_gasto or "sin_clasificar"
            result.motivo_skip[key] = result.motivo_skip.get(key, 0) + 1
            continue

        org = acto.organismo or ""
        org_norm = _normalize(org)

        # Actos extracted before the prompt change may carry no numero_acto, or a
        # per-publication ID that changes every time the tender is republished.
        numero_acto = resolve_numero_acto(
            acto.numero_acto, acto.descripcion, acto.fragmento
        )
        if numero_acto != acto.numero_acto:
            acto.numero_acto = numero_acto

        acto_norm = _normalize_acto(numero_acto)
        keys = dedup_keys(
            org_norm, monto, acto_norm, acto.descripcion, acto.fragmento
        )
        is_duplicate = 0
        if keys:
            if any(k in seen_dedup_keys for k in keys):
                is_duplicate = 1
                result.duplicates += 1
            else:
                seen_dedup_keys.update(keys)

        if not is_duplicate:
            monthly_acc[(org_norm, fecha.year, month)] += monto
            quarterly_acc[(org_norm, fecha.year, quarter)] += monto
            annual_acc[(org_norm, fecha.year)] += monto

        pb_id, score, method, programa, partida = match_organismo(
            org_norm, pb_index, pb_exact
        )
        if pb_id:
            result.matched_presupuesto += 1

        concepto = acto.descripcion or (acto.fragmento or "")[:200]
        beneficiario = first_beneficiario(
            {
                "beneficiarios_json": acto.beneficiarios_json,
                "entidad_beneficiaria": acto.entidad_beneficiaria,
            }
        )
        riesgo = (acto.riesgo or "").lower()

        obs_parts = []
        if acto.motivo_riesgo:
            obs_parts.append(acto.motivo_riesgo)
        if method:
            obs_parts.append(f"match={method} score={score:.2f}")
        obs_parts.append(f"analisis_id={acto.id}")

        db.add(
            EjecucionPresupuestaria(
                boletin_id=boletin_id,
                presupuesto_base_id=pb_id,
                analisis_id=acto.id,
                fecha_boletin=fecha,
                organismo=org[:200] if org else None,
                beneficiario=beneficiario,
                concepto=concepto[:500] if concepto else None,
                monto=monto,
                tipo_operacion=acto.tipo_acto,
                partida_presupuestaria=partida,
                programa=programa,
                categoria_watcher=acto.categoria,
                riesgo_watcher=riesgo or None,
                etapa_gasto=acto.etapa_gasto,
                jurisdiccion=acto.jurisdiccion_gasto or JURISDICCION_PROVINCIAL,
                monto_acumulado_mes=monthly_acc[(org_norm, fecha.year, month)],
                monto_acumulado_trimestre=quarterly_acc[(org_norm, fecha.year, quarter)],
                monto_acumulado_anual=annual_acc[(org_norm, fecha.year)],
                es_modificacion_presupuestaria=False,
                requiere_revision=riesgo in ("alto", "medio"),
                observaciones=" | ".join(obs_parts) if obs_parts else None,
                is_duplicate=is_duplicate,
                created_at=now,
            )
        )
        result.rows_written += 1

    await db.flush()
    return result

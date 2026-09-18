"""
API endpoints for Presupuesto
"""

import json
from datetime import date
from pathlib import Path

from app.db.models import Boletin, EjecucionPresupuestaria, PresupuestoBase
from app.db.session import get_db
from app.schemas.presupuesto import (
    CoberturaResumen,
    CoberturaTemporalResumen,
    DenominadorSinDuenoItemResumen,
    DenominadorSinDuenoResumen,
    EjecucionListResponse,
    EjecucionResponse,
    EjecucionResumenResponse,
    MesResumenItem,
    OrganismoResponse,
    OrgResumenItem,
    ProgramaDetailResponse,
    ProgramaResponse,
    ProgramasListResponse,
)
from app.services.ejecucion_contrast import (
    BUCKET_COMPROMISO,
    BUCKET_EJECUCION,
    aggregate_cobertura,
    aggregate_cobertura_temporal,
    aggregate_denominador_sin_dueno,
    aggregate_organismos,
    bucket_etapa,
    remap_organismo_key,
    vigente_por_organismo_canonico,
)
from app.services.gasto_classifier import JURISDICCIONES
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

# Paths for analysis data
BASE_DIR = Path(__file__).parent.parent.parent.parent.parent.parent
DATOS_DIR = BASE_DIR / "watcher-doc"

async def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(dependencies=[Depends(_no_store)])

@router.get("/programas/", response_model=ProgramasListResponse)
async def get_programas(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    ejercicio: int | None = None,
    organismo: str | None = None,
    exclude_zero_budget: bool = Query(True, description="Excluir programas con presupuesto $0"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of programas presupuestarios with filters.
    Por defecto excluye programas con presupuesto vigente e inicial en $0.
    """
    try:
        query = select(PresupuestoBase)

        # Apply filters
        filters = []
        if ejercicio:
            filters.append(PresupuestoBase.ejercicio == ejercicio)
        if organismo:
            filters.append(PresupuestoBase.organismo == organismo)

        # Filtrar programas con presupuesto $0 (excluir donde ambos montos son 0)
        if exclude_zero_budget:
            # Excluir programas donde tanto monto_vigente como monto_inicial son 0
            # Incluir solo programas donde al menos uno de los montos no es 0
            filters.append(
                or_(
                    PresupuestoBase.monto_vigente != 0,
                    PresupuestoBase.monto_inicial != 0
                )
            )

        if filters:
            query = query.where(and_(*filters))

        # Get total count
        count_query = select(func.count()).select_from(PresupuestoBase)
        if filters:
            count_query = count_query.where(and_(*filters))

        result = await db.execute(count_query)
        total = result.scalar()

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(PresupuestoBase.organismo, PresupuestoBase.programa)
        result = await db.execute(query)
        programas = result.scalars().all()

        return ProgramasListResponse(
            programas=[ProgramaResponse.model_validate(p) for p in programas],
            total=total or 0,
            page=skip // limit + 1,
            page_size=limit
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/programas/{programa_id}", response_model=ProgramaDetailResponse)
async def get_programa(
    programa_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific programa by ID with ejecucion data
    """
    try:
        # Get programa
        result = await db.execute(
            select(PresupuestoBase).where(PresupuestoBase.id == programa_id)
        )
        programa = result.scalar_one_or_none()

        if not programa:
            raise HTTPException(status_code=404, detail="Programa not found")

        # Get ejecuciones
        ejecuciones_result = await db.execute(
            select(EjecucionPresupuestaria)
            .where(EjecucionPresupuestaria.presupuesto_base_id == programa_id)
            .order_by(EjecucionPresupuestaria.fecha_boletin.desc())
        )
        ejecuciones = ejecuciones_result.scalars().all()

        # Calculate total ejecutado
        total_ejecutado = sum(e.monto for e in ejecuciones)
        porcentaje_ejecucion = (total_ejecutado / programa.monto_vigente * 100) if programa.monto_vigente > 0 else 0

        # Build ejecuciones list
        ejecuciones_list = []
        for e in ejecuciones:
            ejecuciones_list.append(EjecucionResponse(
                id=e.id,
                fecha_boletin=e.fecha_boletin,
                organismo=e.organismo,
                beneficiario=e.beneficiario,
                concepto=e.concepto,
                monto=e.monto,
                tipo_operacion=e.tipo_operacion,
                monto_acumulado_mes=e.monto_acumulado_mes,
                monto_acumulado_anual=e.monto_acumulado_anual,
                categoria_watcher=e.categoria_watcher,
                riesgo_watcher=e.riesgo_watcher
            ))

        # Build programa detail response
        programa_detail = ProgramaDetailResponse(
            id=programa.id,
            ejercicio=programa.ejercicio,
            organismo=programa.organismo,
            programa=programa.programa,
            subprograma=programa.subprograma,
            partida_presupuestaria=programa.partida_presupuestaria,
            descripcion=programa.descripcion,
            monto_inicial=programa.monto_inicial,
            monto_vigente=programa.monto_vigente,
            fecha_aprobacion=programa.fecha_aprobacion,
            meta_fisica=programa.meta_fisica,
            meta_numerica=programa.meta_numerica,
            unidad_medida=programa.unidad_medida,
            fuente_financiamiento=programa.fuente_financiamiento,
            ejecuciones=ejecuciones_list,
            total_ejecutado=total_ejecutado,
            porcentaje_ejecucion=round(porcentaje_ejecucion, 2)
        )

        return programa_detail

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/programas/{programa_id}/ejecucion", response_model=list[EjecucionResponse])
async def get_programa_ejecucion(
    programa_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get ejecucion for specific programa
    """
    try:
        # Verify programa exists
        programa_result = await db.execute(
            select(PresupuestoBase).where(PresupuestoBase.id == programa_id)
        )
        programa = programa_result.scalar_one_or_none()

        if not programa:
            raise HTTPException(status_code=404, detail="Programa not found")

        # Get ejecuciones
        result = await db.execute(
            select(EjecucionPresupuestaria)
            .where(EjecucionPresupuestaria.presupuesto_base_id == programa_id)
            .order_by(EjecucionPresupuestaria.fecha_boletin.desc())
        )
        ejecuciones = result.scalars().all()

        return [EjecucionResponse.model_validate(e) for e in ejecuciones]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/organismos/", response_model=list[OrganismoResponse])
async def get_organismos(
    ejercicio: int | None = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of organismos with aggregated data
    """
    try:
        query = select(
            PresupuestoBase.organismo,
            func.count(PresupuestoBase.id).label('total_programas'),
            func.sum(PresupuestoBase.monto_inicial).label('monto_inicial_total'),
            func.sum(PresupuestoBase.monto_vigente).label('monto_vigente_total')
        ).group_by(PresupuestoBase.organismo)

        if ejercicio:
            query = query.where(PresupuestoBase.ejercicio == ejercicio)

        result = await db.execute(query)
        organismos = []

        for row in result.all():
            organismos.append(OrganismoResponse(
                organismo=row.organismo,
                total_programas=row.total_programas,
                monto_inicial_total=row.monto_inicial_total or 0,
                monto_vigente_total=row.monto_vigente_total or 0
            ))

        return sorted(organismos, key=lambda x: x.monto_vigente_total, reverse=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== EJECUCIÓN PRESUPUESTARIA =====

@router.get("/ejecucion/resumen/", response_model=EjecucionResumenResponse)
async def get_ejecucion_resumen(
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    jurisdiccion: str | None = Query(
        None, description="provincial | municipal | fuera_presupuesto"
    ),
    ejercicio: int = Query(2026, ge=2000, le=2100),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregated stats for ejecucion_presupuestaria.

    Canonical vs duplicate totals, commitment vs execution split, top organisms
    contrasted against presupuesto_base.monto_vigente, and monthly breakdown.
    """
    try:
        if jurisdiccion is not None and jurisdiccion not in JURISDICCIONES:
            raise HTTPException(
                status_code=400,
                detail=f"jurisdiccion must be one of {list(JURISDICCIONES)}",
            )

        date_filters = []
        if fecha_desde:
            date_filters.append(EjecucionPresupuestaria.fecha_boletin >= fecha_desde)
        if fecha_hasta:
            date_filters.append(EjecucionPresupuestaria.fecha_boletin <= fecha_hasta)
        if jurisdiccion:
            date_filters.append(EjecucionPresupuestaria.jurisdiccion == jurisdiccion)

        canon_filters = [EjecucionPresupuestaria.is_duplicate == 0] + date_filters

        group_q = (
            select(
                EjecucionPresupuestaria.is_duplicate,
                EjecucionPresupuestaria.etapa_gasto,
                func.count(EjecucionPresupuestaria.id).label("cnt"),
                func.coalesce(func.sum(EjecucionPresupuestaria.monto), 0).label(
                    "total"
                ),
            )
            .group_by(
                EjecucionPresupuestaria.is_duplicate,
                EjecucionPresupuestaria.etapa_gasto,
            )
        )
        if date_filters:
            group_q = group_q.where(and_(*date_filters))
        result = await db.execute(group_q)
        canon_count = dup_count = 0
        canon_monto = dup_monto = 0.0
        monto_compromiso = monto_ejecucion = 0.0
        for row in result.all():
            total = float(row.total)
            if row.is_duplicate == 0:
                canon_count += row.cnt
                canon_monto += total
                bucket = bucket_etapa(row.etapa_gasto)
                if bucket == BUCKET_COMPROMISO:
                    monto_compromiso += total
                elif bucket == BUCKET_EJECUCION:
                    monto_ejecucion += total
            else:
                dup_count += row.cnt
                dup_monto += total

        org_key = func.coalesce(
            PresupuestoBase.organismo, EjecucionPresupuestaria.organismo
        )
        org_q = (
            select(
                org_key.label("org_key"),
                EjecucionPresupuestaria.etapa_gasto,
                func.count(EjecucionPresupuestaria.id).label("cnt"),
                func.coalesce(func.sum(EjecucionPresupuestaria.monto), 0).label(
                    "total"
                ),
            )
            .select_from(EjecucionPresupuestaria)
            .outerjoin(
                PresupuestoBase,
                PresupuestoBase.id == EjecucionPresupuestaria.presupuesto_base_id,
            )
            .where(and_(*canon_filters))
            .group_by(org_key, EjecucionPresupuestaria.etapa_gasto)
        )
        org_rows = await db.execute(org_q)
        # Raw rows, one per programa: the ceiling has to be countable in rows as
        # well as in pesos, because "74 filas sin dueño" is a claim the UI makes.
        # Both consumers below sum by canonical organism, so the totals are the
        # same as the grouped query this replaces.
        vig_q = (
            select(PresupuestoBase.organismo, PresupuestoBase.monto_vigente)
            .where(PresupuestoBase.ejercicio == ejercicio)
        )
        vig_result = await db.execute(vig_q)
        vig_rows = [(r[0], float(r[1] or 0.0)) for r in vig_result.all()]
        vigente_por_org, display_by_canon = vigente_por_organismo_canonico(vig_rows)
        denominador = aggregate_denominador_sin_dueno(vig_rows)
        spend_rows = [
            (
                remap_organismo_key(r.org_key, display_by_canon),
                r.etapa_gasto,
                float(r.total),
                int(r.cnt),
            )
            for r in org_rows.all()
        ]

        contrast = aggregate_organismos(spend_rows, vigente_por_org)
        sobre_compromiso_count = sum(1 for c in contrast if c.sobre_compromiso)
        por_organismo = [
            OrgResumenItem(
                organismo=c.organismo,
                count=c.count,
                monto_total=c.monto_total,
                monto_compromiso=c.monto_compromiso,
                monto_ejecucion=c.monto_ejecucion,
                monto_vigente=c.monto_vigente,
                pct_compromiso=c.pct_compromiso,
                pct_ejecucion=c.pct_ejecucion,
                sobre_compromiso=c.sobre_compromiso,
                sobre_ejecucion=c.sobre_ejecucion,
                matched=c.matched,
                monto_llamado=c.monto_llamado,
            )
            for c in contrast
        ]
        cobertura = aggregate_cobertura(contrast)

        # Period the numerator actually covers.  `presupuesto_base` is the whole
        # year, so the pct below divides three months by twelve unless we say so.
        rango = (
            await db.execute(
                select(
                    func.min(EjecucionPresupuestaria.fecha_boletin),
                    func.max(EjecucionPresupuestaria.fecha_boletin),
                ).where(and_(*canon_filters))
            )
        ).one()
        mes_desde = rango[0].strftime("%Y-%m") if rango[0] else None
        mes_hasta = rango[1].strftime("%Y-%m") if rango[1] else None
        boletin_rows: list[tuple] = []
        if rango[0] and rango[1]:
            # `boletines.date` is a YYYYMMDD string, so compare as strings.
            fecha_desde_s = rango[0].strftime("%Y%m%d")
            fecha_hasta_s = rango[1].strftime("%Y%m%d")
            result = await db.execute(
                select(Boletin.date, Boletin.status, Boletin.error_message).where(
                    Boletin.date >= fecha_desde_s, Boletin.date <= fecha_hasta_s
                )
            )
            boletin_rows = [tuple(r) for r in result.all()]
        temporal = aggregate_cobertura_temporal(
            boletin_rows,
            ejercicio,
            mes_desde,
            mes_hasta,
            mes_actual=date.today().strftime("%Y-%m"),
        )

        result = await db.execute(
            select(
                func.strftime("%Y-%m", EjecucionPresupuestaria.fecha_boletin).label(
                    "mes"
                ),
                func.count(EjecucionPresupuestaria.id).label("cnt"),
                func.coalesce(func.sum(EjecucionPresupuestaria.monto), 0).label(
                    "total"
                ),
            )
            .where(and_(*canon_filters))
            .group_by("mes")
            .order_by("mes")
        )
        por_mes = [
            MesResumenItem(mes=r.mes, count=r.cnt, monto_total=float(r.total))
            for r in result.all()
        ]

        return EjecucionResumenResponse(
            total_canonical=canon_count,
            total_duplicates=dup_count,
            monto_canonical=canon_monto,
            monto_duplicates=dup_monto,
            monto_compromiso=monto_compromiso,
            monto_ejecucion=monto_ejecucion,
            sobre_compromiso_count=sobre_compromiso_count,
            cobertura=CoberturaResumen(
                monto_total=cobertura.monto_total,
                monto_con_denominador=cobertura.monto_con_denominador,
                monto_sin_denominador=cobertura.monto_sin_denominador,
                count_sin_denominador=cobertura.count_sin_denominador,
                pct_sin_denominador=cobertura.pct_sin_denominador,
            ),
            cobertura_temporal=CoberturaTemporalResumen(
                mes_desde=temporal.mes_desde,
                mes_hasta=temporal.mes_hasta,
                meses_cubiertos=temporal.meses_cubiertos,
                meses_del_ejercicio=temporal.meses_del_ejercicio,
                meses_vencidos_sin_ingesta=list(temporal.meses_vencidos_sin_ingesta),
                meses_futuros=list(temporal.meses_futuros),
                dias_con_publicacion=temporal.dias_con_publicacion,
                dias_justificados=temporal.dias_justificados,
                dias_faltantes=temporal.dias_faltantes,
                denominador_es_anual=temporal.denominador_es_anual,
            ),
            denominador=DenominadorSinDuenoResumen(
                monto_total=denominador.monto_total,
                monto_sin_dueno=denominador.monto_sin_dueno,
                monto_verificable=denominador.monto_verificable,
                count_sin_dueno=denominador.count_sin_dueno,
                pct_sin_dueno=denominador.pct_sin_dueno,
                por_organismo=[
                    DenominadorSinDuenoItemResumen(
                        organismo=item.organismo,
                        count=item.count,
                        monto_vigente=item.monto_vigente,
                    )
                    for item in denominador.por_organismo
                ],
            ),
            por_organismo=por_organismo,
            por_mes=por_mes,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ejecucion/", response_model=EjecucionListResponse)
async def get_ejecucion(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    organismo: str | None = Query(None, description="Partial match (case-insensitive)"),
    riesgo: str | None = Query(None, description="alto | medio | bajo | informativo"),
    solo_canonicos: bool = Query(True, description="Exclude duplicate publications"),
    presupuesto_base_id: int | None = Query(None),
    requiere_revision: bool | None = Query(None),
    jurisdiccion: str | None = Query(
        None, description="provincial | municipal | fuera_presupuesto"
    ),
    etapa_gasto: str | None = Query(
        None, description="llamado | adjudicacion | contrato | pago"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Paginated list of ejecucion_presupuestaria rows with optional filters.
    By default excludes duplicate publications (solo_canonicos=true).
    """
    try:
        filters = []
        if fecha_desde:
            filters.append(EjecucionPresupuestaria.fecha_boletin >= fecha_desde)
        if fecha_hasta:
            filters.append(EjecucionPresupuestaria.fecha_boletin <= fecha_hasta)
        if organismo:
            filters.append(EjecucionPresupuestaria.organismo.ilike(f"%{organismo}%"))
        if riesgo:
            filters.append(EjecucionPresupuestaria.riesgo_watcher == riesgo)
        if solo_canonicos:
            filters.append(EjecucionPresupuestaria.is_duplicate == 0)
        if presupuesto_base_id is not None:
            filters.append(EjecucionPresupuestaria.presupuesto_base_id == presupuesto_base_id)
        if requiere_revision is not None:
            filters.append(EjecucionPresupuestaria.requiere_revision == requiere_revision)
        if jurisdiccion:
            if jurisdiccion not in JURISDICCIONES:
                raise HTTPException(
                    status_code=400,
                    detail=f"jurisdiccion must be one of {list(JURISDICCIONES)}",
                )
            filters.append(EjecucionPresupuestaria.jurisdiccion == jurisdiccion)
        if etapa_gasto:
            filters.append(EjecucionPresupuestaria.etapa_gasto == etapa_gasto)

        base_q = select(EjecucionPresupuestaria)
        count_q = select(
            func.count(EjecucionPresupuestaria.id),
            func.coalesce(func.sum(EjecucionPresupuestaria.monto), 0),
        )
        if filters:
            where = and_(*filters)
            base_q = base_q.where(where)
            count_q = count_q.where(where)

        # Total count and monto for current filters
        count_result = await db.execute(count_q)
        total, total_monto = count_result.one()

        # Paginated rows
        result = await db.execute(
            base_q
            .order_by(
                EjecucionPresupuestaria.fecha_boletin.desc(),
                EjecucionPresupuestaria.monto.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
        rows = result.scalars().all()

        return EjecucionListResponse(
            ejecuciones=[EjecucionResponse.model_validate(r) for r in rows],
            total=total or 0,
            total_monto=float(total_monto or 0),
            page=skip // limit + 1,
            page_size=limit,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== NEW ENDPOINTS FOR BUDGET ANALYSIS =====

@router.get("/tendencias/")
async def get_tendencias(
    db: AsyncSession = Depends(get_db)
):
    """Get budget execution trends and forecasts (March-June 2025)"""
    try:
        tendencias_path = DATOS_DIR / "analisis_tendencias_2025.json"
        if not tendencias_path.exists():
            raise HTTPException(status_code=404, detail="Tendencias analysis not found")

        with open(tendencias_path, encoding='utf-8') as f:
            tendencias = json.load(f)

        return {
            "metadata": tendencias.get("metadata", {}),
            "summary": tendencias.get("summary", {}),
            "top_velocities": tendencias.get("velocities", [])[:20],
            "top_efficient": tendencias.get("efficiency", {}).get("top_efficient", [])[:10],
            "forecasts_high_risk": tendencias.get("forecasts", {}).get("high_risk", [])
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalias/")
async def get_anomalias(
    severity: str | None = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Get detected budget execution anomalies with ML classification"""
    try:
        anomalias_path = DATOS_DIR / "clasificacion_anomalias_budget.json"
        if not anomalias_path.exists():
            raise HTTPException(status_code=404, detail="Anomalies not found")

        with open(anomalias_path, encoding='utf-8') as f:
            data = json.load(f)

        programas = data.get("programas", [])
        if severity:
            programas = [p for p in programas if p.get("severity") == severity.upper()]
        anomalies = [p for p in programas if p.get("severity") != "NORMAL"]
        anomalies.sort(key=lambda x: x.get("anomaly_score", 0))

        return {
            "total_anomalies": len(anomalies),
            "anomalies": anomalies[:limit],
            "summary": {
                "CRITICO": len([a for a in anomalies if a.get("severity") == "CRITICO"]),
                "ALTO": len([a for a in anomalies if a.get("severity") == "ALTO"]),
                "MEDIO": len([a for a in anomalies if a.get("severity") == "MEDIO"]),
                "BAJO": len([a for a in anomalies if a.get("severity") == "BAJO"])
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predicciones/")
async def get_predicciones(
    organismo: str | None = Query(None),
    risk_level: str | None = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get Q3/Q4 execution forecasts with confidence intervals"""
    try:
        tendencias_path = DATOS_DIR / "analisis_tendencias_2025.json"
        if not tendencias_path.exists():
            raise HTTPException(status_code=404, detail="Forecasts not found")

        with open(tendencias_path, encoding='utf-8') as f:
            data = json.load(f)

        forecasts = data.get("forecasts", {}).get("forecasts", [])
        if organismo:
            forecasts = [f for f in forecasts if organismo.upper() in f.get("organismo", "").upper()]
        if risk_level:
            forecasts = [f for f in forecasts if f.get("risk_level") == risk_level.upper()]

        return {
            "total_forecasts": len(forecasts),
            "forecasts": forecasts,
            "summary": {
                "high_risk": len([f for f in forecasts if f.get("risk_level") == "ALTO"]),
                "medium_risk": len([f for f in forecasts if f.get("risk_level") == "MEDIO"]),
                "low_risk": len([f for f in forecasts if f.get("risk_level") == "BAJO"])
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparacion/{periodo}")
async def get_comparacion(periodo: str, db: AsyncSession = Depends(get_db)):
    """Get period comparison (marzo vs junio)"""
    try:
        if periodo.lower() != "marzo-junio":
            raise HTTPException(status_code=400, detail="Only 'marzo-junio' available")

        comparison_path = DATOS_DIR / "comparacion_marzo_junio_2025.json"
        if not comparison_path.exists():
            raise HTTPException(status_code=404, detail="Comparison not found")

        with open(comparison_path, encoding='utf-8') as f:
            data = json.load(f)

        return {
            "periodo": "marzo-junio",
            "programas_comunes": data.get("programas_comunes", 0),
            "top_aceleracion": data.get("top_aceleracion", [])[:10],
            "top_desaceleracion": data.get("top_desaceleracion", [])[:10],
            "comparaciones_sample": data.get("comparaciones", [])[:50]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


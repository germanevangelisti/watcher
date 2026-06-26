"""
API endpoints for Presupuesto
"""

import json
from datetime import date
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.db.session import get_db
from app.db.models import PresupuestoBase, EjecucionPresupuestaria
from app.schemas.presupuesto import (
    ProgramaResponse,
    ProgramasListResponse,
    ProgramaDetailResponse,
    EjecucionResponse,
    EjecucionListResponse,
    EjecucionResumenResponse,
    OrgResumenItem,
    MesResumenItem,
    OrganismoResponse,
)

# Paths for analysis data
BASE_DIR = Path(__file__).parent.parent.parent.parent.parent.parent
DATOS_DIR = BASE_DIR / "watcher-doc"

router = APIRouter()

@router.get("/programas/", response_model=ProgramasListResponse)
async def get_programas(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    ejercicio: Optional[int] = None,
    organismo: Optional[str] = None,
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
    ejercicio: Optional[int] = None,
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
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregated stats for ejecucion_presupuestaria.
    Returns canonical vs duplicate totals, top 10 organisms, and monthly breakdown.
    """
    try:
        date_filters = []
        if fecha_desde:
            date_filters.append(EjecucionPresupuestaria.fecha_boletin >= fecha_desde)
        if fecha_hasta:
            date_filters.append(EjecucionPresupuestaria.fecha_boletin <= fecha_hasta)

        # Filters for canonical-only queries (always includes is_duplicate == 0)
        canon_filters = [EjecucionPresupuestaria.is_duplicate == 0] + date_filters

        # Canonical vs duplicate totals
        group_q = (
            select(
                EjecucionPresupuestaria.is_duplicate,
                func.count(EjecucionPresupuestaria.id).label("cnt"),
                func.coalesce(func.sum(EjecucionPresupuestaria.monto), 0).label("total"),
            )
            .group_by(EjecucionPresupuestaria.is_duplicate)
        )
        if date_filters:
            group_q = group_q.where(and_(*date_filters))
        result = await db.execute(group_q)
        canon_count = dup_count = 0
        canon_monto = dup_monto = 0.0
        for row in result.all():
            if row.is_duplicate == 0:
                canon_count, canon_monto = row.cnt, float(row.total)
            else:
                dup_count, dup_monto = row.cnt, float(row.total)

        # Top 15 organisms by canonical monto
        result = await db.execute(
            select(
                EjecucionPresupuestaria.organismo,
                func.count(EjecucionPresupuestaria.id).label("cnt"),
                func.coalesce(func.sum(EjecucionPresupuestaria.monto), 0).label("total"),
            )
            .where(and_(*canon_filters))
            .group_by(EjecucionPresupuestaria.organismo)
            .order_by(func.sum(EjecucionPresupuestaria.monto).desc())
            .limit(15)
        )
        por_organismo = [
            OrgResumenItem(organismo=r.organismo, count=r.cnt, monto_total=float(r.total))
            for r in result.all()
        ]

        # Monthly breakdown (canonical only)
        result = await db.execute(
            select(
                func.strftime("%Y-%m", EjecucionPresupuestaria.fecha_boletin).label("mes"),
                func.count(EjecucionPresupuestaria.id).label("cnt"),
                func.coalesce(func.sum(EjecucionPresupuestaria.monto), 0).label("total"),
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
            por_organismo=por_organismo,
            por_mes=por_mes,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ejecucion/", response_model=EjecucionListResponse)
async def get_ejecucion(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    organismo: Optional[str] = Query(None, description="Partial match (case-insensitive)"),
    riesgo: Optional[str] = Query(None, description="alto | medio | bajo | informativo"),
    solo_canonicos: bool = Query(True, description="Exclude duplicate publications"),
    presupuesto_base_id: Optional[int] = Query(None),
    requiere_revision: Optional[bool] = Query(None),
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
        
        with open(tendencias_path, 'r', encoding='utf-8') as f:
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
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Get detected budget execution anomalies with ML classification"""
    try:
        anomalias_path = DATOS_DIR / "clasificacion_anomalias_budget.json"
        if not anomalias_path.exists():
            raise HTTPException(status_code=404, detail="Anomalies not found")
        
        with open(anomalias_path, 'r', encoding='utf-8') as f:
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
    organismo: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get Q3/Q4 execution forecasts with confidence intervals"""
    try:
        tendencias_path = DATOS_DIR / "analisis_tendencias_2025.json"
        if not tendencias_path.exists():
            raise HTTPException(status_code=404, detail="Forecasts not found")
        
        with open(tendencias_path, 'r', encoding='utf-8') as f:
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
        
        with open(comparison_path, 'r', encoding='utf-8') as f:
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


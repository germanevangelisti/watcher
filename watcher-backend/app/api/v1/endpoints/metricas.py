"""
API endpoints for Métricas
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.db.models import (
    PresupuestoBase, ActoAdministrativo, AlertasGestion,
    VinculoActoPresupuesto, EjecucionPresupuestaria
)
from app.schemas.metricas import (
    MetricasGeneralesResponse,
    MetricasOrganismoResponse,
    DistribucionRiesgoResponse
)

router = APIRouter()

@router.get("/generales", response_model=MetricasGeneralesResponse)
async def get_metricas_generales(
    db: AsyncSession = Depends(get_db)
):
    """
    Get general metrics across the system
    """
    try:
        # Presupuesto metrics
        presupuesto_result = await db.execute(
            select(
                func.count(PresupuestoBase.id),
                func.sum(PresupuestoBase.monto_inicial),
                func.sum(PresupuestoBase.monto_vigente)
            )
        )
        total_programas, monto_inicial, monto_vigente = presupuesto_result.one()
        
        # Ejecución total
        ejecucion_result = await db.execute(
            select(func.sum(EjecucionPresupuestaria.monto))
        )
        monto_ejecutado = ejecucion_result.scalar() or 0
        
        # Actos metrics
        actos_result = await db.execute(select(func.count()).select_from(ActoAdministrativo))
        total_actos = actos_result.scalar() or 0
        
        actos_alto = await db.execute(
            select(func.count()).select_from(ActoAdministrativo)
            .where(ActoAdministrativo.nivel_riesgo == 'ALTO')
        )
        actos_alto_riesgo = actos_alto.scalar() or 0
        
        actos_medio = await db.execute(
            select(func.count()).select_from(ActoAdministrativo)
            .where(ActoAdministrativo.nivel_riesgo == 'MEDIO')
        )
        actos_medio_riesgo = actos_medio.scalar() or 0
        
        actos_bajo = await db.execute(
            select(func.count()).select_from(ActoAdministrativo)
            .where(ActoAdministrativo.nivel_riesgo == 'BAJO')
        )
        actos_bajo_riesgo = actos_bajo.scalar() or 0
        
        # Alertas metrics
        alertas_result = await db.execute(select(func.count()).select_from(AlertasGestion))
        total_alertas = alertas_result.scalar() or 0
        
        alertas_criticas = await db.execute(
            select(func.count()).select_from(AlertasGestion)
            .where(AlertasGestion.nivel_severidad == 'critica')
        )
        criticas = alertas_criticas.scalar() or 0
        
        alertas_altas = await db.execute(
            select(func.count()).select_from(AlertasGestion)
            .where(AlertasGestion.nivel_severidad == 'alta')
        )
        altas = alertas_altas.scalar() or 0
        
        # Vinculación metrics
        vinculos_result = await db.execute(select(func.count()).select_from(VinculoActoPresupuesto))
        total_vinculos = vinculos_result.scalar() or 0
        
        tasa_vinculacion = (total_vinculos / total_actos * 100) if total_actos > 0 else 0
        
        # Top organismos by presupuesto
        top_presupuesto = await db.execute(
            select(PresupuestoBase.organismo, func.sum(PresupuestoBase.monto_vigente))
            .group_by(PresupuestoBase.organismo)
            .order_by(func.sum(PresupuestoBase.monto_vigente).desc())
            .limit(5)
        )
        top_organismos_presupuesto = [
            {"organismo": org, "monto": float(monto)} 
            for org, monto in top_presupuesto.all()
        ]
        
        # Top organismos by riesgo
        top_riesgo = await db.execute(
            select(ActoAdministrativo.organismo, func.count())
            .where(ActoAdministrativo.nivel_riesgo == 'ALTO')
            .group_by(ActoAdministrativo.organismo)
            .order_by(func.count().desc())
            .limit(5)
        )
        top_organismos_riesgo = [
            {"organismo": org, "actos_alto_riesgo": count} 
            for org, count in top_riesgo.all()
        ]
        
        porcentaje_ejecucion = (monto_ejecutado / monto_vigente * 100) if monto_vigente and monto_vigente > 0 else 0
        
        return MetricasGeneralesResponse(
            total_programas=total_programas or 0,
            monto_total_inicial=float(monto_inicial or 0),
            monto_total_vigente=float(monto_vigente or 0),
            monto_total_ejecutado=float(monto_ejecutado),
            porcentaje_ejecucion_global=round(porcentaje_ejecucion, 2),
            total_actos=total_actos,
            actos_alto_riesgo=actos_alto_riesgo,
            actos_medio_riesgo=actos_medio_riesgo,
            actos_bajo_riesgo=actos_bajo_riesgo,
            total_alertas=total_alertas,
            alertas_criticas=criticas,
            alertas_altas=altas,
            total_vinculos=total_vinculos,
            tasa_vinculacion=round(tasa_vinculacion, 2),
            top_organismos_presupuesto=top_organismos_presupuesto,
            top_organismos_riesgo=top_organismos_riesgo
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/por-organismo/{organismo}", response_model=MetricasOrganismoResponse)
async def get_metricas_organismo(
    organismo: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get metrics for specific organismo
    """
    try:
        # Presupuesto
        presupuesto_result = await db.execute(
            select(
                func.count(PresupuestoBase.id),
                func.sum(PresupuestoBase.monto_inicial),
                func.sum(PresupuestoBase.monto_vigente)
            ).where(PresupuestoBase.organismo == organismo)
        )
        total_programas, monto_inicial, monto_vigente = presupuesto_result.one()
        
        # Ejecución
        ejecucion_result = await db.execute(
            select(func.sum(EjecucionPresupuestaria.monto))
            .where(EjecucionPresupuestaria.organismo == organismo)
        )
        monto_ejecutado = ejecucion_result.scalar() or 0
        
        # Actos
        actos_result = await db.execute(
            select(func.count()).select_from(ActoAdministrativo)
            .where(ActoAdministrativo.organismo == organismo)
        )
        total_actos = actos_result.scalar() or 0
        
        actos_alto = await db.execute(
            select(func.count()).select_from(ActoAdministrativo)
            .where(ActoAdministrativo.organismo == organismo)
            .where(ActoAdministrativo.nivel_riesgo == 'ALTO')
        )
        actos_alto_riesgo = actos_alto.scalar() or 0
        
        # Alertas
        alertas_result = await db.execute(
            select(func.count()).select_from(AlertasGestion)
            .where(AlertasGestion.organismo == organismo)
        )
        total_alertas = alertas_result.scalar() or 0
        
        alertas_criticas = await db.execute(
            select(func.count()).select_from(AlertasGestion)
            .where(AlertasGestion.organismo == organismo)
            .where(AlertasGestion.nivel_severidad == 'critica')
        )
        criticas = alertas_criticas.scalar() or 0
        
        porcentaje_ejecucion = (monto_ejecutado / monto_vigente * 100) if monto_vigente and monto_vigente > 0 else 0
        
        return MetricasOrganismoResponse(
            organismo=organismo,
            total_programas=total_programas or 0,
            monto_inicial=float(monto_inicial or 0),
            monto_vigente=float(monto_vigente or 0),
            monto_ejecutado=float(monto_ejecutado),
            porcentaje_ejecucion=round(porcentaje_ejecucion, 2),
            total_actos=total_actos,
            actos_alto_riesgo=actos_alto_riesgo,
            total_alertas=total_alertas,
            alertas_criticas=criticas
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/riesgo", response_model=DistribucionRiesgoResponse)
async def get_distribucion_riesgo(
    db: AsyncSession = Depends(get_db)
):
    """
    Get risk distribution across different dimensions
    """
    try:
        # By nivel
        nivel_result = await db.execute(
            select(ActoAdministrativo.nivel_riesgo, func.count())
            .group_by(ActoAdministrativo.nivel_riesgo)
        )
        por_nivel = dict(nivel_result.all())
        
        # By tipo_acto
        tipo_result = await db.execute(
            select(ActoAdministrativo.tipo_acto, ActoAdministrativo.nivel_riesgo, func.count())
            .group_by(ActoAdministrativo.tipo_acto, ActoAdministrativo.nivel_riesgo)
        )
        por_tipo_acto = {}
        for tipo, riesgo, count in tipo_result.all():
            if tipo not in por_tipo_acto:
                por_tipo_acto[tipo] = {}
            por_tipo_acto[tipo][riesgo] = count
        
        # By organismo (top 10)
        org_result = await db.execute(
            select(ActoAdministrativo.organismo, ActoAdministrativo.nivel_riesgo, func.count())
            .group_by(ActoAdministrativo.organismo, ActoAdministrativo.nivel_riesgo)
        )
        por_organismo = {}
        for org, riesgo, count in org_result.all():
            if org not in por_organismo:
                por_organismo[org] = {}
            por_organismo[org][riesgo] = count
        
        # Top 10 organismos
        por_organismo = dict(sorted(
            por_organismo.items(),
            key=lambda x: sum(x[1].values()),
            reverse=True
        )[:10])
        
        # Monto by nivel
        monto_result = await db.execute(
            select(ActoAdministrativo.nivel_riesgo, func.sum(ActoAdministrativo.monto))
            .where(ActoAdministrativo.monto.isnot(None))
            .group_by(ActoAdministrativo.nivel_riesgo)
        )
        monto_por_nivel = {nivel: float(monto or 0) for nivel, monto in monto_result.all()}
        
        return DistribucionRiesgoResponse(
            por_nivel=por_nivel,
            por_tipo_acto=por_tipo_acto,
            por_organismo=por_organismo,
            monto_por_nivel=monto_por_nivel
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


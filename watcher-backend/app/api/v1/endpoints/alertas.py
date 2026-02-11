"""
API endpoints for Alertas Gestion
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db.session import get_db
from app.db.models import AlertasGestion
from app.schemas.alertas import (
    AlertaResponse,
    AlertasListResponse,
    AlertasStatsResponse,
    AlertaUpdate
)

router = APIRouter()

@router.get("/", response_model=AlertasListResponse)
async def get_alertas(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    nivel_severidad: Optional[str] = None,
    tipo_alerta: Optional[str] = None,
    organismo: Optional[str] = None,
    estado: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of alertas with filters
    """
    try:
        query = select(AlertasGestion)
        
        # Apply filters
        filters = []
        if nivel_severidad:
            filters.append(AlertasGestion.nivel_severidad == nivel_severidad)
        if tipo_alerta:
            filters.append(AlertasGestion.tipo_alerta == tipo_alerta)
        if organismo:
            filters.append(AlertasGestion.organismo == organismo)
        if estado:
            filters.append(AlertasGestion.estado == estado)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Get total count
        count_query = select(func.count()).select_from(AlertasGestion)
        if filters:
            count_query = count_query.where(and_(*filters))
        
        result = await db.execute(count_query)
        total = result.scalar()
        
        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(AlertasGestion.fecha_deteccion.desc())
        result = await db.execute(query)
        alertas = result.scalars().all()
        
        return AlertasListResponse(
            alertas=[AlertaResponse.model_validate(a) for a in alertas],
            total=total or 0,
            page=skip // limit + 1,
            page_size=limit
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/", response_model=AlertasStatsResponse)
async def get_alertas_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get alertas statistics
    """
    try:
        # Total count
        total_result = await db.execute(select(func.count()).select_from(AlertasGestion))
        total = total_result.scalar() or 0
        
        # By severidad
        criticas_result = await db.execute(
            select(func.count()).select_from(AlertasGestion)
            .where(AlertasGestion.nivel_severidad == 'critica')
        )
        criticas = criticas_result.scalar() or 0
        
        altas_result = await db.execute(
            select(func.count()).select_from(AlertasGestion)
            .where(AlertasGestion.nivel_severidad == 'alta')
        )
        altas = altas_result.scalar() or 0
        
        medias_result = await db.execute(
            select(func.count()).select_from(AlertasGestion)
            .where(AlertasGestion.nivel_severidad == 'media')
        )
        medias = medias_result.scalar() or 0
        
        bajas_result = await db.execute(
            select(func.count()).select_from(AlertasGestion)
            .where(AlertasGestion.nivel_severidad == 'baja')
        )
        bajas = bajas_result.scalar() or 0
        
        # By estado
        activas_result = await db.execute(
            select(func.count()).select_from(AlertasGestion)
            .where(AlertasGestion.estado == 'activa')
        )
        activas = activas_result.scalar() or 0
        
        revisadas_result = await db.execute(
            select(func.count()).select_from(AlertasGestion)
            .where(AlertasGestion.estado == 'revisada')
        )
        revisadas = revisadas_result.scalar() or 0
        
        # By tipo
        tipo_result = await db.execute(
            select(AlertasGestion.tipo_alerta, func.count())
            .group_by(AlertasGestion.tipo_alerta)
        )
        por_tipo = dict(tipo_result.all())
        
        # By organismo
        organismo_result = await db.execute(
            select(AlertasGestion.organismo, func.count())
            .group_by(AlertasGestion.organismo)
            .limit(10)
        )
        por_organismo = dict(organismo_result.all())
        
        return AlertasStatsResponse(
            total=total,
            criticas=criticas,
            altas=altas,
            medias=medias,
            bajas=bajas,
            activas=activas,
            revisadas=revisadas,
            por_tipo=por_tipo,
            por_organismo=por_organismo
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{alerta_id}", response_model=AlertaResponse)
async def get_alerta(
    alerta_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific alerta by ID
    """
    try:
        result = await db.execute(
            select(AlertasGestion).where(AlertasGestion.id == alerta_id)
        )
        alerta = result.scalar_one_or_none()
        
        if not alerta:
            raise HTTPException(status_code=404, detail="Alerta not found")
        
        return AlertaResponse.model_validate(alerta)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{alerta_id}/estado", response_model=AlertaResponse)
async def update_alerta_estado(
    alerta_id: int,
    update: AlertaUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update alerta estado
    """
    try:
        result = await db.execute(
            select(AlertasGestion).where(AlertasGestion.id == alerta_id)
        )
        alerta = result.scalar_one_or_none()
        
        if not alerta:
            raise HTTPException(status_code=404, detail="Alerta not found")
        
        if update.estado:
            alerta.estado = update.estado
        if update.observaciones_revision:
            alerta.observaciones_revision = update.observaciones_revision
            
        await db.commit()
        await db.refresh(alerta)
        
        return AlertaResponse.model_validate(alerta)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


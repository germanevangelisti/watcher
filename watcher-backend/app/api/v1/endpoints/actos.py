"""
API endpoints for Actos Administrativos
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import json

from app.db.session import get_db
from app.db.models import ActoAdministrativo, VinculoActoPresupuesto, PresupuestoBase
from app.schemas.actos import (
    ActoResponse,
    ActosListResponse,
    ActoDetailResponse,
    VinculoResponse
)

router = APIRouter()

@router.get("/", response_model=ActosListResponse)
async def get_actos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tipo_acto: Optional[str] = None,
    organismo: Optional[str] = None,
    nivel_riesgo: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of actos administrativos with filters
    """
    try:
        query = select(ActoAdministrativo)
        
        # Apply filters
        filters = []
        if tipo_acto:
            filters.append(ActoAdministrativo.tipo_acto == tipo_acto)
        if organismo:
            filters.append(ActoAdministrativo.organismo == organismo)
        if nivel_riesgo:
            filters.append(ActoAdministrativo.nivel_riesgo == nivel_riesgo)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Get total count
        count_query = select(func.count()).select_from(ActoAdministrativo)
        if filters:
            count_query = count_query.where(and_(*filters))
        
        result = await db.execute(count_query)
        total = result.scalar()
        
        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(ActoAdministrativo.created_at.desc())
        result = await db.execute(query)
        actos = result.scalars().all()
        
        return ActosListResponse(
            actos=[ActoResponse.model_validate(a) for a in actos],
            total=total or 0,
            page=skip // limit + 1,
            page_size=limit
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{acto_id}", response_model=ActoDetailResponse)
async def get_acto(
    acto_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific acto by ID with vinculos
    """
    try:
        # Get acto
        result = await db.execute(
            select(ActoAdministrativo).where(ActoAdministrativo.id == acto_id)
        )
        acto = result.scalar_one_or_none()
        
        if not acto:
            raise HTTPException(status_code=404, detail="Acto not found")
        
        # Get vinculos
        vinculos_result = await db.execute(
            select(VinculoActoPresupuesto, PresupuestoBase)
            .join(PresupuestoBase, VinculoActoPresupuesto.programa_id == PresupuestoBase.id)
            .where(VinculoActoPresupuesto.acto_id == acto_id)
            .order_by(VinculoActoPresupuesto.score_confianza.desc())
        )
        
        vinculos = []
        for vinculo, programa in vinculos_result.all():
            programa_dict = {
                "id": programa.id,
                "organismo": programa.organismo,
                "programa": programa.programa,
                "descripcion": programa.descripcion,
                "monto_vigente": programa.monto_vigente
            }
            
            # Parse detalles_json if it's a string
            detalles_json = vinculo.detalles_json
            if isinstance(detalles_json, str):
                try:
                    detalles_json = json.loads(detalles_json)
                except (json.JSONDecodeError, TypeError):
                    detalles_json = None
            
            vinculo_dict = {
                "id": vinculo.id,
                "acto_id": vinculo.acto_id,
                "programa_id": vinculo.programa_id,
                "score_confianza": vinculo.score_confianza,
                "metodo_matching": vinculo.metodo_matching,
                "detalles_json": detalles_json,
                "programa": programa_dict
            }
            
            vinculos.append(VinculoResponse(**vinculo_dict))
        
        # Create response
        acto_dict = {
            "id": acto.id,
            "tipo_acto": acto.tipo_acto,
            "numero": acto.numero,
            "fecha": acto.fecha,
            "organismo": acto.organismo,
            "beneficiario": acto.beneficiario,
            "monto": acto.monto,
            "partida": acto.partida,
            "descripcion": acto.descripcion,
            "nivel_riesgo": acto.nivel_riesgo,
            "created_at": acto.created_at,
            "keywords": acto.keywords,
            "vinculos": vinculos,
            "fragmento_original": acto.fragmento_original,
            "pagina": acto.pagina
        }
        
        return ActoDetailResponse(**acto_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{acto_id}/vinculos", response_model=list[VinculoResponse])
async def get_acto_vinculos(
    acto_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get vinculos for specific acto
    """
    try:
        # Verify acto exists
        acto_result = await db.execute(
            select(ActoAdministrativo).where(ActoAdministrativo.id == acto_id)
        )
        acto = acto_result.scalar_one_or_none()
        
        if not acto:
            raise HTTPException(status_code=404, detail="Acto not found")
        
        # Get vinculos
        result = await db.execute(
            select(VinculoActoPresupuesto, PresupuestoBase)
            .join(PresupuestoBase, VinculoActoPresupuesto.programa_id == PresupuestoBase.id)
            .where(VinculoActoPresupuesto.acto_id == acto_id)
            .order_by(VinculoActoPresupuesto.score_confianza.desc())
        )
        
        vinculos = []
        for vinculo, programa in result.all():
            programa_dict = {
                "id": programa.id,
                "organismo": programa.organismo,
                "programa": programa.programa,
                "descripcion": programa.descripcion,
                "monto_vigente": programa.monto_vigente
            }
            
            # Parse detalles_json if it's a string
            detalles_json = vinculo.detalles_json
            if isinstance(detalles_json, str):
                try:
                    detalles_json = json.loads(detalles_json)
                except (json.JSONDecodeError, TypeError):
                    detalles_json = None
            
            vinculo_dict = {
                "id": vinculo.id,
                "acto_id": vinculo.acto_id,
                "programa_id": vinculo.programa_id,
                "score_confianza": vinculo.score_confianza,
                "metodo_matching": vinculo.metodo_matching,
                "detalles_json": detalles_json,
                "programa": programa_dict
            }
            
            vinculos.append(VinculoResponse(**vinculo_dict))
        
        return vinculos
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


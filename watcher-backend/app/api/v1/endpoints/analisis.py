"""
API endpoints para consulta de análisis
"""

from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db import crud

router = APIRouter()

@router.get("", include_in_schema=True)
@router.get("/", include_in_schema=False)
async def list_analisis(
    skip: int = 0,
    limit: int = 100,
    boletin_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
) -> List[Dict]:
    """
    Lista análisis realizados.
    
    Args:
        skip: Número de registros a omitir
        limit: Número máximo de registros a devolver
        boletin_id: Filtrar por ID de boletín específico
        db: Sesión de base de datos
    
    Returns:
        Lista de análisis
    """
    try:
        if boletin_id:
            # Obtener análisis de un boletín específico
            analisis_list = await crud.get_analisis_by_boletin(db, boletin_id, limit=limit)
        else:
            # Obtener todos los análisis (con paginación)
            from sqlalchemy import select
            from app.db.models import Analisis
            
            query = select(Analisis).offset(skip).limit(limit).order_by(Analisis.created_at.desc())
            result = await db.execute(query)
            analisis_list = result.scalars().all()
        
        # Convertir a formato de respuesta
        analisis_data = []
        for analisis in analisis_list:
            analisis_data.append({
                "id": analisis.id,
                "boletin_id": analisis.boletin_id if hasattr(analisis, 'boletin_id') else None,
                "agent": analisis.agent if hasattr(analisis, 'agent') else None,
                "categoria": analisis.categoria if hasattr(analisis, 'categoria') else None,
                "resumen": analisis.resumen if hasattr(analisis, 'resumen') else None,
                "riesgo": analisis.riesgo if hasattr(analisis, 'riesgo') else None,
                "created_at": analisis.created_at.isoformat() if hasattr(analisis, 'created_at') and analisis.created_at else None
            })
        
        return analisis_data
        
    except Exception as e:
        import traceback
        print(f"Error in list_analisis: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_analisis_stats(
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Obtiene estadísticas de análisis.
    
    Returns:
        Estadísticas generales de análisis
    """
    try:
        stats = await crud.get_analisis_stats(db)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
API Endpoints para Jurisdicciones de Córdoba
"""

import logging
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db.database import get_db
from app.db.models import Jurisdiccion, Boletin, MencionJurisdiccional

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# SCHEMAS
# ============================================

class JurisdiccionResponse(BaseModel):
    """Schema de respuesta para jurisdicción"""
    id: int
    nombre: str
    tipo: str
    latitud: Optional[float]
    longitud: Optional[float]
    codigo_postal: Optional[str]
    departamento: Optional[str]
    poblacion: Optional[int]
    superficie_km2: Optional[float]
    extra_data: Optional[Dict]
    
    class Config:
        from_attributes = True


class JurisdiccionStats(BaseModel):
    """Estadísticas de una jurisdicción"""
    jurisdiccion_id: int
    nombre: str
    tipo: str
    total_boletines: int
    total_menciones: int
    poblacion: Optional[int]


class JurisdiccionDetailResponse(JurisdiccionResponse):
    """Respuesta detallada con estadísticas"""
    total_boletines: int = 0
    total_menciones: int = 0
    ultima_actividad: Optional[str]


# ============================================
# ENDPOINTS
# ============================================

@router.get("/", response_model=List[JurisdiccionResponse])
async def listar_jurisdicciones(
    tipo: Optional[str] = Query(None, description="Filtrar por tipo: provincia, capital, municipalidad, comuna"),
    departamento: Optional[str] = Query(None, description="Filtrar por departamento"),
    limite: int = Query(100, le=500, description="Número máximo de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    buscar: Optional[str] = Query(None, description="Buscar por nombre"),
    db: AsyncSession = Depends(get_db)
) -> List[JurisdiccionResponse]:
    """
    Lista todas las jurisdicciones con filtros opcionales.
    
    Args:
        tipo: Filtrar por tipo (provincia, capital, municipalidad, comuna)
        departamento: Filtrar por departamento
        limite: Número máximo de resultados
        offset: Offset para paginación
        buscar: Buscar por nombre (case-insensitive)
        db: Sesión de base de datos
        
    Returns:
        Lista de jurisdicciones
    """
    try:
        query = select(Jurisdiccion)
        
        # Aplicar filtros
        if tipo:
            query = query.where(Jurisdiccion.tipo == tipo)
        
        if departamento:
            query = query.where(Jurisdiccion.departamento == departamento)
        
        if buscar:
            query = query.where(Jurisdiccion.nombre.ilike(f"%{buscar}%"))
        
        # Ordenar por población descendente
        query = query.order_by(Jurisdiccion.poblacion.desc().nullslast())
        
        # Paginación
        query = query.limit(limite).offset(offset)
        
        result = await db.execute(query)
        jurisdicciones = result.scalars().all()
        
        return [JurisdiccionResponse.model_validate(j) for j in jurisdicciones]
    
    except Exception as e:
        logger.error(f"Error listando jurisdicciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=List[JurisdiccionStats])
async def estadisticas_jurisdicciones(
    tipo: Optional[str] = Query(None, description="Filtrar por tipo"),
    limite: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db)
) -> List[JurisdiccionStats]:
    """
    Obtiene estadísticas de actividad por jurisdicción.
    
    Muestra cuántos boletines y menciones tiene cada jurisdicción.
    """
    try:
        # Query con joins para contar boletines y menciones
        query = select(
            Jurisdiccion.id,
            Jurisdiccion.nombre,
            Jurisdiccion.tipo,
            Jurisdiccion.poblacion,
            func.count(Boletin.id.distinct()).label("total_boletines"),
            func.count(MencionJurisdiccional.id.distinct()).label("total_menciones")
        ).outerjoin(
            Boletin, Boletin.jurisdiccion_id == Jurisdiccion.id
        ).outerjoin(
            MencionJurisdiccional, MencionJurisdiccional.jurisdiccion_id == Jurisdiccion.id
        ).group_by(
            Jurisdiccion.id, Jurisdiccion.nombre, Jurisdiccion.tipo, Jurisdiccion.poblacion
        )
        
        if tipo:
            query = query.where(Jurisdiccion.tipo == tipo)
        
        # Ordenar por actividad (boletines + menciones)
        query = query.order_by(
            (func.count(Boletin.id) + func.count(MencionJurisdiccional.id)).desc()
        ).limit(limite)
        
        result = await db.execute(query)
        rows = result.all()
        
        return [
            JurisdiccionStats(
                jurisdiccion_id=row.id,
                nombre=row.nombre,
                tipo=row.tipo,
                total_boletines=row.total_boletines,
                total_menciones=row.total_menciones,
                poblacion=row.poblacion
            )
            for row in rows
        ]
    
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{jurisdiccion_id}", response_model=JurisdiccionDetailResponse)
async def obtener_jurisdiccion(
    jurisdiccion_id: int,
    db: AsyncSession = Depends(get_db)
) -> JurisdiccionDetailResponse:
    """
    Obtiene detalles de una jurisdicción específica con estadísticas.
    """
    try:
        # Obtener jurisdicción
        query = select(Jurisdiccion).where(Jurisdiccion.id == jurisdiccion_id)
        result = await db.execute(query)
        jurisdiccion = result.scalar_one_or_none()
        
        if not jurisdiccion:
            raise HTTPException(status_code=404, detail="Jurisdicción no encontrada")
        
        # Contar boletines
        query_boletines = select(func.count(Boletin.id)).where(
            Boletin.jurisdiccion_id == jurisdiccion_id
        )
        result_boletines = await db.execute(query_boletines)
        total_boletines = result_boletines.scalar() or 0
        
        # Contar menciones
        query_menciones = select(func.count(MencionJurisdiccional.id)).where(
            MencionJurisdiccional.jurisdiccion_id == jurisdiccion_id
        )
        result_menciones = await db.execute(query_menciones)
        total_menciones = result_menciones.scalar() or 0
        
        # Última actividad (último boletín o mención)
        query_ultima = select(func.max(Boletin.created_at)).where(
            Boletin.jurisdiccion_id == jurisdiccion_id
        )
        result_ultima = await db.execute(query_ultima)
        ultima_actividad = result_ultima.scalar()
        
        return JurisdiccionDetailResponse(
            id=jurisdiccion.id,
            nombre=jurisdiccion.nombre,
            tipo=jurisdiccion.tipo,
            latitud=jurisdiccion.latitud,
            longitud=jurisdiccion.longitud,
            codigo_postal=jurisdiccion.codigo_postal,
            departamento=jurisdiccion.departamento,
            poblacion=jurisdiccion.poblacion,
            superficie_km2=jurisdiccion.superficie_km2,
            extra_data=jurisdiccion.extra_data,
            total_boletines=total_boletines,
            total_menciones=total_menciones,
            ultima_actividad=ultima_actividad.isoformat() if ultima_actividad else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo jurisdicción {jurisdiccion_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{jurisdiccion_id}/boletines")
async def boletines_por_jurisdiccion(
    jurisdiccion_id: int,
    limite: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Obtiene boletines asociados a una jurisdicción específica.
    """
    try:
        # Verificar que existe
        query_check = select(Jurisdiccion).where(Jurisdiccion.id == jurisdiccion_id)
        result_check = await db.execute(query_check)
        if not result_check.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Jurisdicción no encontrada")
        
        # Obtener boletines
        query = select(Boletin).where(
            Boletin.jurisdiccion_id == jurisdiccion_id
        ).order_by(
            Boletin.date.desc()
        ).limit(limite).offset(offset)
        
        result = await db.execute(query)
        boletines = result.scalars().all()
        
        # Contar total
        query_count = select(func.count(Boletin.id)).where(
            Boletin.jurisdiccion_id == jurisdiccion_id
        )
        result_count = await db.execute(query_count)
        total = result_count.scalar() or 0
        
        return {
            "total": total,
            "limite": limite,
            "offset": offset,
            "boletines": [
                {
                    "id": b.id,
                    "filename": b.filename,
                    "date": b.date,
                    "section": b.section,
                    "seccion_nombre": b.seccion_nombre,
                    "status": b.status,
                    "fuente": b.fuente
                }
                for b in boletines
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo boletines: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cerca/{lat}/{lng}")
async def jurisdicciones_cercanas(
    lat: float,
    lng: float,
    radio_km: float = Query(50.0, description="Radio de búsqueda en kilómetros"),
    limite: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db)
) -> List[Dict]:
    """
    Encuentra jurisdicciones cercanas a unas coordenadas.
    
    Usa fórmula de Haversine para calcular distancia.
    """
    try:
        # Obtener todas las jurisdicciones con coordenadas
        query = select(Jurisdiccion).where(
            and_(
                Jurisdiccion.latitud.isnot(None),
                Jurisdiccion.longitud.isnot(None)
            )
        )
        
        result = await db.execute(query)
        jurisdicciones = result.scalars().all()
        
        # Calcular distancias
        from math import radians, cos, sin, asin, sqrt
        
        def haversine(lat1, lon1, lat2, lon2):
            """Calcula distancia en km entre dos puntos"""
            R = 6371  # Radio de la Tierra en km
            
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            
            return R * c
        
        # Filtrar por distancia
        cercanas = []
        for j in jurisdicciones:
            distancia = haversine(lat, lng, j.latitud, j.longitud)
            if distancia <= radio_km:
                cercanas.append({
                    "jurisdiccion": JurisdiccionResponse.model_validate(j),
                    "distancia_km": round(distancia, 2)
                })
        
        # Ordenar por distancia
        cercanas.sort(key=lambda x: x["distancia_km"])
        
        return cercanas[:limite]
    
    except Exception as e:
        logger.error(f"Error buscando jurisdicciones cercanas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tipos/disponibles")
async def tipos_disponibles(db: AsyncSession = Depends(get_db)) -> Dict:
    """
    Retorna los tipos de jurisdicciones disponibles con conteo.
    """
    try:
        query = select(
            Jurisdiccion.tipo,
            func.count(Jurisdiccion.id).label("cantidad")
        ).group_by(Jurisdiccion.tipo)
        
        result = await db.execute(query)
        tipos = result.all()
        
        return {
            "tipos": [
                {
                    "tipo": row.tipo,
                    "cantidad": row.cantidad,
                    "label": {
                        "provincia": "Provincia",
                        "capital": "Ciudad Capital",
                        "municipalidad": "Municipalidades",
                        "comuna": "Comunas"
                    }.get(row.tipo, row.tipo)
                }
                for row in tipos
            ]
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo tipos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

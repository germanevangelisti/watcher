"""
API Endpoints para Menciones Jurisdiccionales
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime, date
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.db.database import get_db
from app.db.models import MencionJurisdiccional, Boletin, Jurisdiccion
from app.services.mencion_processor import get_mencion_processor

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# SCHEMAS
# ============================================

class MencionResponse(BaseModel):
    """Schema de respuesta para mención."""
    id: int
    boletin_id: int
    jurisdiccion_id: int
    tipo_mencion: str
    fragmento_texto: Optional[str]
    extra_data: Optional[Dict]
    
    # Datos relacionados
    boletin_fecha: Optional[date]
    boletin_filename: Optional[str]
    jurisdiccion_nombre: Optional[str]
    
    class Config:
        from_attributes = True


class ProcesamientoRequest(BaseModel):
    """Request para iniciar procesamiento de menciones."""
    limite: int = Field(default=10, le=100, description="Boletines a procesar")
    forzar: bool = Field(default=False, description="Reprocesar si ya tienen menciones")
    fecha_desde: Optional[str] = Field(None, description="Filtrar desde fecha (YYYY-MM-DD)")
    fecha_hasta: Optional[str] = Field(None, description="Filtrar hasta fecha (YYYY-MM-DD)")


class ProcesamientoResponse(BaseModel):
    """Response del procesamiento de menciones."""
    task_id: str
    message: str
    total_boletines: int
    stats: Optional[Dict] = None


class EstadisticasMenciones(BaseModel):
    """Estadísticas de menciones."""
    total_menciones: int
    total_jurisdicciones_mencionadas: int
    total_boletines_con_menciones: int
    por_tipo_mencion: Dict[str, int]
    top_jurisdicciones: List[Dict]


# ============================================
# ENDPOINTS
# ============================================

@router.get("/", response_model=List[MencionResponse])
async def listar_menciones(
    jurisdiccion_id: Optional[int] = Query(None, description="Filtrar por jurisdicción"),
    boletin_id: Optional[int] = Query(None, description="Filtrar por boletín"),
    tipo_mencion: Optional[str] = Query(None, description="Filtrar por tipo de mención"),
    limite: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
) -> List[MencionResponse]:
    """
    Lista menciones jurisdiccionales con filtros opcionales.
    """
    try:
        query = select(
            MencionJurisdiccional,
            Boletin.date.label("boletin_fecha"),
            Boletin.filename.label("boletin_filename"),
            Jurisdiccion.nombre.label("jurisdiccion_nombre")
        ).join(
            Boletin, Boletin.id == MencionJurisdiccional.boletin_id
        ).join(
            Jurisdiccion, Jurisdiccion.id == MencionJurisdiccional.jurisdiccion_id
        )
        
        # Aplicar filtros
        if jurisdiccion_id:
            query = query.where(MencionJurisdiccional.jurisdiccion_id == jurisdiccion_id)
        
        if boletin_id:
            query = query.where(MencionJurisdiccional.boletin_id == boletin_id)
        
        if tipo_mencion:
            query = query.where(MencionJurisdiccional.tipo_mencion == tipo_mencion)
        
        # Ordenar por fecha del boletín descendente
        query = query.order_by(Boletin.date.desc()).limit(limite).offset(offset)
        
        result = await db.execute(query)
        rows = result.all()
        
        return [
            MencionResponse(
                id=row.MencionJurisdiccional.id,
                boletin_id=row.MencionJurisdiccional.boletin_id,
                jurisdiccion_id=row.MencionJurisdiccional.jurisdiccion_id,
                tipo_mencion=row.MencionJurisdiccional.tipo_mencion,
                fragmento_texto=row.MencionJurisdiccional.fragmento_texto,
                extra_data=row.MencionJurisdiccional.extra_data,
                boletin_fecha=row.boletin_fecha,
                boletin_filename=row.boletin_filename,
                jurisdiccion_nombre=row.jurisdiccion_nombre
            )
            for row in rows
        ]
    
    except Exception as e:
        logger.error(f"Error listando menciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=EstadisticasMenciones)
async def estadisticas_menciones(
    jurisdiccion_id: Optional[int] = Query(None, description="Filtrar por jurisdicción"),
    db: AsyncSession = Depends(get_db)
) -> EstadisticasMenciones:
    """
    Obtiene estadísticas de menciones.
    """
    try:
        # Query base
        query = select(MencionJurisdiccional)
        
        if jurisdiccion_id:
            query = query.where(MencionJurisdiccional.jurisdiccion_id == jurisdiccion_id)
        
        result = await db.execute(query)
        menciones = result.scalars().all()
        
        # Total de menciones
        total_menciones = len(menciones)
        
        # Jurisdicciones únicas mencionadas
        jurisdicciones_unicas = len(set(m.jurisdiccion_id for m in menciones))
        
        # Boletines únicos con menciones
        boletines_unicos = len(set(m.boletin_id for m in menciones))
        
        # Por tipo de mención
        por_tipo = {}
        for m in menciones:
            tipo = m.tipo_mencion or "sin_clasificar"
            por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        
        # Top jurisdicciones mencionadas
        conteo_jurisdicciones = {}
        for m in menciones:
            jid = m.jurisdiccion_id
            if jid not in conteo_jurisdicciones:
                conteo_jurisdicciones[jid] = {"jurisdiccion_id": jid, "count": 0}
            conteo_jurisdicciones[jid]["count"] += 1
        
        # Obtener nombres de jurisdicciones
        if conteo_jurisdicciones:
            query_jurisdicciones = select(Jurisdiccion).where(
                Jurisdiccion.id.in_(conteo_jurisdicciones.keys())
            )
            result_jurisdicciones = await db.execute(query_jurisdicciones)
            jurisdicciones_dict = {
                j.id: j.nombre for j in result_jurisdicciones.scalars().all()
            }
            
            for jid, data in conteo_jurisdicciones.items():
                data["nombre"] = jurisdicciones_dict.get(jid, f"ID {jid}")
        
        top_jurisdicciones = sorted(
            conteo_jurisdicciones.values(),
            key=lambda x: x["count"],
            reverse=True
        )[:10]
        
        return EstadisticasMenciones(
            total_menciones=total_menciones,
            total_jurisdicciones_mencionadas=jurisdicciones_unicas,
            total_boletines_con_menciones=boletines_unicos,
            por_tipo_mencion=por_tipo,
            top_jurisdicciones=top_jurisdicciones
        )
    
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/procesar", response_model=ProcesamientoResponse)
async def procesar_menciones(
    request: ProcesamientoRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> ProcesamientoResponse:
    """
    Inicia el procesamiento de menciones en boletines.
    
    Procesa un lote de boletines para extraer menciones jurisdiccionales.
    El procesamiento se ejecuta en background.
    """
    try:
        # Parsear fechas si se proporcionan
        fecha_desde = None
        fecha_hasta = None
        
        if request.fecha_desde:
            fecha_desde = datetime.fromisoformat(request.fecha_desde)
        
        if request.fecha_hasta:
            fecha_hasta = datetime.fromisoformat(request.fecha_hasta)
        
        # Obtener procesador
        processor = get_mencion_processor()
        
        # Agregar tarea en background
        task_id = f"mencion_proc_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        async def procesar_en_background():
            async with db as session:
                resultado = await processor.procesar_lote(
                    limite=request.limite,
                    db=session,
                    forzar=request.forzar,
                    filtro_fecha_desde=fecha_desde,
                    filtro_fecha_hasta=fecha_hasta
                )
                logger.info(f"Procesamiento {task_id} completado: {resultado}")
        
        background_tasks.add_task(procesar_en_background)
        
        return ProcesamientoResponse(
            task_id=task_id,
            message=f"Procesamiento iniciado para hasta {request.limite} boletines",
            total_boletines=request.limite,
            stats=None
        )
    
    except Exception as e:
        logger.error(f"Error iniciando procesamiento: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tipos")
async def tipos_mencion_disponibles(
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Retorna los tipos de mención disponibles con conteo.
    """
    try:
        query = select(
            MencionJurisdiccional.tipo_mencion,
            func.count(MencionJurisdiccional.id).label("cantidad")
        ).group_by(MencionJurisdiccional.tipo_mencion)
        
        result = await db.execute(query)
        tipos = result.all()
        
        return {
            "tipos": [
                {
                    "tipo": row.tipo_mencion or "sin_clasificar",
                    "cantidad": row.cantidad,
                    "label": {
                        "decreto": "Decretos",
                        "resolucion": "Resoluciones",
                        "ordenanza": "Ordenanzas",
                        "licitacion": "Licitaciones",
                        "contratacion": "Contrataciones",
                        "convenio": "Convenios",
                        "subsidio": "Subsidios",
                        "designacion": "Designaciones",
                        "referencia_general": "Referencias Generales"
                    }.get(row.tipo_mencion, row.tipo_mencion or "Sin Clasificar")
                }
                for row in tipos
            ]
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo tipos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{mencion_id}")
async def eliminar_mencion(
    mencion_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Elimina una mención específica.
    """
    try:
        query = select(MencionJurisdiccional).where(MencionJurisdiccional.id == mencion_id)
        result = await db.execute(query)
        mencion = result.scalar_one_or_none()
        
        if not mencion:
            raise HTTPException(status_code=404, detail="Mención no encontrada")
        
        await db.delete(mencion)
        await db.commit()
        
        return {"message": "Mención eliminada correctamente", "id": mencion_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando mención {mencion_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

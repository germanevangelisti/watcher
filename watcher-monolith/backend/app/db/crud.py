"""
Operaciones CRUD para la base de datos
"""

from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Boletin, Analisis

async def create_boletin(
    db: AsyncSession,
    filename: str,
    date: str,
    section: str,
    status: str = "pending"
) -> Boletin:
    """Crea un nuevo registro de boletín o actualiza existente."""
    # Verificar si ya existe
    query = select(Boletin).where(Boletin.filename == filename)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        # Actualizar existente
        existing.status = status
        existing.updated_at = datetime.utcnow()
        await db.flush()  # Flush para obtener el ID
        return existing
    
    # Crear nuevo
    db_boletin = Boletin(
        filename=filename,
        date=date,
        section=section,
        status=status
    )
    db.add(db_boletin)
    await db.flush()  # Flush para obtener el ID
    return db_boletin

async def get_boletin(db: AsyncSession, boletin_id: int) -> Optional[Boletin]:
    """Obtiene un boletín por ID."""
    query = select(Boletin).where(Boletin.id == boletin_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_boletin_by_filename(db: AsyncSession, filename: str) -> Optional[Boletin]:
    """Obtiene un boletín por nombre de archivo."""
    query = select(Boletin).where(Boletin.filename == filename)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_boletines(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
) -> List[Boletin]:
    """Obtiene lista de boletines con filtros opcionales."""
    query = select(Boletin).offset(skip).limit(limit)
    if status:
        query = query.where(Boletin.status == status)
    result = await db.execute(query)
    return result.scalars().all()

async def update_boletin_status(
    db: AsyncSession,
    boletin_id: int,
    status: str,
    error_message: Optional[str] = None
) -> Optional[Boletin]:
    """Actualiza el estado de un boletín."""
    boletin = await get_boletin(db, boletin_id)
    if boletin:
        boletin.status = status
        boletin.error_message = error_message
        boletin.updated_at = datetime.utcnow()
    return boletin

async def create_analisis(
    db: AsyncSession,
    boletin_id: int,
    fragmento: str,
    analisis_data: Dict
) -> Analisis:
    """Crea un nuevo registro de análisis."""
    db_analisis = Analisis(
        boletin_id=boletin_id,
        fragmento=fragmento,
        categoria=analisis_data.get("categoria"),
        entidad_beneficiaria=analisis_data.get("entidad_beneficiaria"),
        monto_estimado=analisis_data.get("monto_estimado"),
        riesgo=analisis_data.get("riesgo"),
        tipo_curro=analisis_data.get("tipo_curro"),
        accion_sugerida=analisis_data.get("accion_sugerida"),
        datos_extra=analisis_data.get("metadata", {})
    )
    db.add(db_analisis)
    return db_analisis

async def get_analisis_by_boletin(
    db: AsyncSession,
    boletin_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Analisis]:
    """Obtiene análisis de un boletín específico."""
    query = (
        select(Analisis)
        .where(Analisis.boletin_id == boletin_id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()

async def get_analisis_stats(db: AsyncSession) -> Dict:
    """Obtiene estadísticas generales de los análisis."""
    # Total de boletines por estado
    boletines_query = select(Boletin.status, func.count(Boletin.id)).group_by(Boletin.status)
    boletines_result = await db.execute(boletines_query)
    boletines_stats = dict(boletines_result.all())
    
    # Total de análisis por nivel de riesgo
    riesgo_query = select(Analisis.riesgo, func.count(Analisis.id)).group_by(Analisis.riesgo)
    riesgo_result = await db.execute(riesgo_query)
    riesgo_stats = dict(riesgo_result.all())
    
    return {
        "boletines": boletines_stats,
        "riesgos": riesgo_stats
    }
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
    status: str = "pending",
    file_hash: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    origin: str = "downloaded"
) -> Boletin:
    """
    Crea un nuevo registro de boletín o actualiza existente.
    
    Deduplication logic (Epic 1.1):
    1. If file_hash is provided, check for duplicate by hash first
    2. If hash duplicate found, return existing record (even if filename differs)
    3. Otherwise, check by filename as before
    
    Args:
        db: Database session
        filename: Name of the file
        date: Date in YYYYMMDD format
        section: Section number/identifier
        status: Status of the boletin
        file_hash: Optional SHA256 hash for deduplication
        file_size_bytes: Optional file size in bytes
        
    Returns:
        Boletin record (existing or newly created)
    """
    # 1. Check for duplicate by file_hash (if provided)
    if file_hash:
        hash_query = select(Boletin).where(Boletin.file_hash == file_hash)
        result = await db.execute(hash_query)
        existing_by_hash = result.scalar_one_or_none()
        
        if existing_by_hash:
            # Duplicate detected by hash - update if needed
            existing_by_hash.status = status
            existing_by_hash.updated_at = datetime.utcnow()
            # Update hash/size if they were missing
            if not existing_by_hash.file_hash:
                existing_by_hash.file_hash = file_hash
            if not existing_by_hash.file_size_bytes and file_size_bytes:
                existing_by_hash.file_size_bytes = file_size_bytes
            await db.flush()
            return existing_by_hash
    
    # 2. Check for duplicate by filename
    filename_query = select(Boletin).where(Boletin.filename == filename)
    result = await db.execute(filename_query)
    existing_by_filename = result.scalar_one_or_none()
    
    if existing_by_filename:
        # Update existing record
        existing_by_filename.status = status
        existing_by_filename.updated_at = datetime.utcnow()
        # Add hash/size if they were missing
        if file_hash and not existing_by_filename.file_hash:
            existing_by_filename.file_hash = file_hash
        if file_size_bytes and not existing_by_filename.file_size_bytes:
            existing_by_filename.file_size_bytes = file_size_bytes
        await db.flush()
        return existing_by_filename
    
    # 3. Create new record
    db_boletin = Boletin(
        filename=filename,
        date=date,
        section=section,
        status=status,
        file_hash=file_hash,
        file_size_bytes=file_size_bytes,
        origin=origin
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
    from sqlalchemy.orm import selectinload
    query = select(Boletin).options(selectinload(Boletin.jurisdiccion)).offset(skip).limit(limit)
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
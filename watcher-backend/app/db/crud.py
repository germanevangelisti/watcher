"""
Operaciones CRUD para la base de datos
"""

import re
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

def _parse_monto_string(monto_str: str) -> Optional[float]:
    """
    Parse an Argentine monto string to a float.
    
    Handles formats like:
    - "pesos 3.010.523.733,29" -> 3010523733.29
    - "$1.066.200.000,00" -> 1066200000.0
    - "198.731.610,00" -> 198731610.0
    - "PESOS TRES MIL DIEZ MILLONES... (pesos 3.010.523.733,29)" -> 3010523733.29
    """
    if not monto_str:
        return None
    
    # Try to find a numeric amount in parentheses first (often contains the parsed value)
    paren_match = re.search(r'\((?:pesos\s+)?([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)\)', monto_str)
    if paren_match:
        num_str = paren_match.group(1).replace('.', '').replace(',', '.')
        try:
            return float(num_str)
        except ValueError:
            pass
    
    # Try to find a standalone numeric pattern
    num_match = re.search(r'(?:pesos\s+|\$\s*)?([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)', monto_str)
    if num_match:
        num_str = num_match.group(1).replace('.', '').replace(',', '.')
        try:
            return float(num_str)
        except ValueError:
            pass
    
    return None


async def create_analisis(
    db: AsyncSession,
    boletin_id: int,
    fragmento: str,
    analisis_data: Dict
) -> Analisis:
    """
    Crea un nuevo registro de análisis.
    
    Supports both legacy format (v1: single flat dict) and new format
    (v2: ActoExtraido with tipo_acto, numero, organismo, etc.)
    """
    # Detect v2 format (has 'tipo_acto' key)
    is_v2 = "tipo_acto" in analisis_data
    
    # Build beneficiarios string for legacy field
    beneficiarios = analisis_data.get("beneficiarios", [])
    beneficiarios_str = ", ".join(beneficiarios[:3]) if beneficiarios else analisis_data.get("entidad_beneficiaria", "No especificado")
    
    # Build montos string for legacy field
    montos = analisis_data.get("montos", [])
    montos_str = ", ".join(montos[:3]) if montos else analisis_data.get("monto_estimado", "No especificado")
    
    # Map riesgo to uppercase for legacy compat
    riesgo_raw = analisis_data.get("riesgo", "informativo")
    
    # Map tipo_acto to legacy categoria
    tipo_to_categoria = {
        "decreto": "otros",
        "resolucion": "otros",
        "licitacion": "obras sin trazabilidad",
        "designacion": "designaciones políticas",
        "subsidio": "subsidios poco claros",
        "transferencia": "gasto excesivo",
        "otro": "otros",
    }
    
    # Parse monto_numerico: prefer Gemini's monto_total_numerico, fallback to parsing strings
    monto_numerico = None
    gemini_monto = analisis_data.get("monto_total_numerico")
    if gemini_monto and isinstance(gemini_monto, (int, float)) and gemini_monto > 0:
        monto_numerico = float(gemini_monto)
    elif montos:
        # Fallback: parse from monto strings
        for monto_str in montos:
            parsed = _parse_monto_string(monto_str)
            if parsed and parsed > 0:
                monto_numerico = (monto_numerico or 0) + parsed
    
    db_analisis = Analisis(
        boletin_id=boletin_id,
        fragmento=fragmento,
        # Legacy fields (backward compat)
        categoria=tipo_to_categoria.get(analisis_data.get("tipo_acto", ""), analisis_data.get("categoria", "otros")),
        entidad_beneficiaria=beneficiarios_str,
        monto_estimado=montos_str,
        monto_numerico=monto_numerico,
        riesgo=riesgo_raw,
        tipo_curro=analisis_data.get("tipo_curro", analisis_data.get("descripcion", "")),
        accion_sugerida=analisis_data.get("accion_sugerida"),
        datos_extra=analisis_data.get("metadata") or analisis_data.get("datos_extra", {}),
        # v2 fields
        tipo_acto=analisis_data.get("tipo_acto"),
        numero_acto=analisis_data.get("numero") or analisis_data.get("numero_acto"),
        organismo=analisis_data.get("organismo"),
        beneficiarios_json=beneficiarios if is_v2 else None,
        montos_json=montos if is_v2 else None,
        descripcion=analisis_data.get("descripcion"),
        motivo_riesgo=analisis_data.get("motivo_riesgo"),
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
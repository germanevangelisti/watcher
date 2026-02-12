"""
API endpoints para gestión de boletines
"""

from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.services.pdf_service import PDFProcessor
from app.services.watcher_service import WatcherService
from app.services.batch_processor import BatchProcessor
from app.services.processing_logger import processing_logger
from app.db.session import get_db
from app.db import crud
from app.db.models import Boletin
import uuid


def _find_pdf_path(filename: str) -> Optional[Path]:
    """
    Find a PDF file across all known directories.
    Returns the Path if found, None otherwise.
    
    Search order:
    1. boletines/{year}/{month}/ - main download location (organized by date)
    2. data/raw/ - legacy flat directory
    3. data/uploaded_documents/ - manual uploads
    """
    # 1. Search in boletines/{year}/{month}/ based on filename pattern YYYYMMDD_*
    if settings.BOLETINES_DIR.exists() and len(filename) >= 8:
        try:
            year = filename[:4]
            month = filename[4:6]
            candidate = settings.BOLETINES_DIR / year / month / filename
            if candidate.exists():
                return candidate
        except (ValueError, IndexError):
            pass
    
    # 2. Flat directories
    for search_dir in [
        settings.DATA_DIR / "raw",
        settings.DATA_DIR / "uploaded_documents",
    ]:
        candidate = search_dir / filename
        if candidate.exists():
            return candidate
    
    return None

router = APIRouter()
pdf_processor = PDFProcessor()
watcher_service = WatcherService()

@router.get("", include_in_schema=True)
@router.get("/", include_in_schema=False)
async def list_boletines(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    has_file: Optional[bool] = Query(None, description="Filter by file existence on disk"),
    year: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    day: Optional[str] = Query(None),
    jurisdiccion_id: Optional[int] = Query(None, description="Filter by jurisdiccion ID"),
    db: AsyncSession = Depends(get_db)
) -> List[Dict]:
    """
    Lista todos los boletines con información básica.
    
    Args:
        skip: Número de registros a omitir
        limit: Número máximo de registros a devolver
        status: Filtrar por estado específico (pending, processed, failed)
        has_file: Si True, solo retorna boletines con archivo PDF en disco
        year: Filtrar por año (formato YYYY)
        month: Filtrar por mes (formato MM)
        day: Filtrar por día (formato DD)
        db: Sesión de base de datos
    
    Returns:
        Lista de boletines con su información básica
    """
    try:
        # Construir query base
        query = select(Boletin)
        
        # Filtrar por status
        if status:
            query = query.where(Boletin.status == status)
        
        # Filtrar por fecha (YYYYMMDD)
        if year or month or day:
            # Construir patrón de búsqueda
            date_pattern = ""
            if year:
                date_pattern += year
                if month:
                    date_pattern += month.zfill(2)
                    if day:
                        date_pattern += day.zfill(2)
            
            # Usar LIKE para búsqueda de patrón
            query = query.where(Boletin.date.like(f"{date_pattern}%"))
        
        # Filtrar por jurisdiccion
        if jurisdiccion_id is not None:
            query = query.where(Boletin.jurisdiccion_id == jurisdiccion_id)
        
        # If filtering by has_file, we need all records then filter in Python
        # because file existence is a filesystem check, not a DB column
        if has_file is not None:
            # Fetch more to compensate for filtering
            query_all = query
            result = await db.execute(query_all)
            all_boletines = result.scalars().all()
            
            # Filter by file existence
            if has_file:
                boletines = [b for b in all_boletines if _find_pdf_path(b.filename)]
            else:
                boletines = [b for b in all_boletines if not _find_pdf_path(b.filename)]
            
            # Apply pagination manually
            boletines = boletines[skip:skip + limit]
        else:
            # Normal paginated query
            query = query.offset(skip).limit(limit)
            result = await db.execute(query)
            boletines = result.scalars().all()
        
        # Convertir a formato de respuesta simple
        boletines_data = []
        for boletin in boletines:
            # Manejo seguro de fuente
            fuente_value = None
            if hasattr(boletin, 'fuente') and boletin.fuente:
                fuente_value = boletin.fuente.value if hasattr(boletin.fuente, 'value') else str(boletin.fuente)
            
            # Manejo seguro de jurisdiccion
            jurisdiccion_nombre = None
            if hasattr(boletin, 'jurisdiccion') and boletin.jurisdiccion:
                jurisdiccion_nombre = boletin.jurisdiccion.nombre
            
            # Check file existence
            pdf_path = _find_pdf_path(boletin.filename)
            
            boletines_data.append({
                "id": boletin.id,
                "filename": boletin.filename,
                "date": boletin.date,
                "section": boletin.section,
                "status": boletin.status,
                "has_file": pdf_path is not None,
                "file_path": str(pdf_path) if pdf_path else None,
                "created_at": boletin.created_at.isoformat() if boletin.created_at else None,
                "updated_at": boletin.updated_at.isoformat() if boletin.updated_at else None,
                "error_message": boletin.error_message,
                "fuente": fuente_value,
                "jurisdiccion_id": boletin.jurisdiccion_id if hasattr(boletin, 'jurisdiccion_id') else None,
                "jurisdiccion_nombre": jurisdiccion_nombre,
                "seccion_nombre": boletin.seccion_nombre if hasattr(boletin, 'seccion_nombre') else None,
                "origin": getattr(boletin, 'origin', 'downloaded')
            })
        
        return boletines_data
        
    except Exception as e:
        import traceback
        print(f"Error in list_boletines: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{boletin_id}")
async def get_boletin(
    boletin_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Obtiene un boletín específico por ID.
    
    Args:
        boletin_id: ID del boletín
        db: Sesión de base de datos
    
    Returns:
        Información del boletín
    """
    try:
        query = select(Boletin).where(Boletin.id == boletin_id)
        result = await db.execute(query)
        boletin = result.scalar_one_or_none()
        
        if not boletin:
            raise HTTPException(status_code=404, detail=f"Boletín {boletin_id} no encontrado")
        
        # Manejo seguro de fuente
        fuente_value = None
        if hasattr(boletin, 'fuente') and boletin.fuente:
            fuente_value = boletin.fuente.value if hasattr(boletin.fuente, 'value') else str(boletin.fuente)
        
        # Manejo seguro de jurisdiccion
        jurisdiccion_nombre = None
        if hasattr(boletin, 'jurisdiccion') and boletin.jurisdiccion:
            jurisdiccion_nombre = boletin.jurisdiccion.nombre
        
        pdf_path = _find_pdf_path(boletin.filename)
        
        return {
            "id": boletin.id,
            "filename": boletin.filename,
            "date": boletin.date,
            "section": boletin.section,
            "status": boletin.status,
            "has_file": pdf_path is not None,
            "file_path": str(pdf_path) if pdf_path else None,
            "created_at": boletin.created_at.isoformat() if boletin.created_at else None,
            "updated_at": boletin.updated_at.isoformat() if boletin.updated_at else None,
            "error_message": boletin.error_message,
            "fuente": fuente_value,
            "jurisdiccion_id": boletin.jurisdiccion_id,
            "jurisdiccion_nombre": jurisdiccion_nombre,
            "seccion_nombre": boletin.seccion_nombre if hasattr(boletin, 'seccion_nombre') else None,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo boletín: {str(e)}")

@router.post("/import/")
async def import_boletines(
    source_dir: str,
    batch_size: int = 5,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Importa y procesa boletines desde un directorio.
    
    Args:
        source_dir: Ruta al directorio con los PDFs
        batch_size: Tamaño del lote para procesamiento
        db: Sesión de base de datos
    """
    try:
        source_path = Path(source_dir)
        if not source_path.exists():
            raise HTTPException(status_code=404, detail="Directorio no encontrado")
        
        # Crear procesador batch
        processor = BatchProcessor(db)
        
        # Procesar directorio
        stats = await processor.process_directory(
            source_dir=source_path,
            batch_size=batch_size
        )
        
        return {
            "message": "Boletines procesados correctamente",
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/")
async def get_boletines_status(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Obtiene el estado de todos los boletines.
    
    Args:
        skip: Número de registros a omitir
        limit: Número máximo de registros a devolver
        status: Filtrar por estado específico
        db: Sesión de base de datos
    """
    try:
        # Obtener boletines con filtros
        boletines = await crud.get_boletines(
            db=db,
            skip=skip,
            limit=limit,
            status=status
        )
        
        # Obtener estadísticas generales
        stats = await crud.get_analisis_stats(db)
        
        # Convertir a formato de respuesta
        boletines_data = []
        for boletin in boletines:
            # Obtener análisis más reciente para categoría
            analisis_list = await crud.get_analisis_by_boletin(db, boletin.id, limit=1)
            categoria = None
            riesgo = None
            analisis_count = 0
            
            if analisis_list:
                analisis_count = len(await crud.get_analisis_by_boletin(db, boletin.id, limit=100))
                primer_analisis = analisis_list[0]
                categoria = primer_analisis.categoria
                riesgo = primer_analisis.riesgo
            
            boletines_data.append({
                "id": boletin.id,
                "filename": boletin.filename,
                "date": boletin.date,
                "section": boletin.section,
                "status": boletin.status,
                "created_at": boletin.created_at.isoformat() if boletin.created_at else None,
                "updated_at": boletin.updated_at.isoformat() if boletin.updated_at else None,
                "error_message": boletin.error_message,
                "categoria": categoria,
                "riesgo": riesgo,
                "analisis_count": analisis_count,
                "fuente": boletin.fuente.value if boletin.fuente else None,
                "jurisdiccion_id": boletin.jurisdiccion_id,
                "jurisdiccion_nombre": boletin.jurisdiccion.nombre if boletin.jurisdiccion else None,
                "seccion_nombre": boletin.seccion_nombre
            })
        
        return {
            "boletines": boletines_data,
            "total": len(boletines_data),
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{filename}/process")
async def process_boletin(
    filename: str,
    background_tasks: BackgroundTasks
) -> Dict:
    """
    Procesa un boletín específico.
    
    Args:
        filename: Nombre del archivo PDF
        background_tasks: Tareas en segundo plano
    """
    try:
        # Convertir a texto
        txt_path = pdf_processor.process_pdf(filename)
        
        # Analizar con Watcher en segundo plano
        output_path = settings.DATA_DIR / "results" / f"{Path(filename).stem}_analysis.jsonl"
        background_tasks.add_task(
            watcher_service.process_file,
            txt_path,
            output_path
        )
        
        return {
            "message": "Procesamiento iniciado",
            "filename": filename,
            "text_file": str(txt_path),
            "output_file": str(output_path)
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Boletín no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch/process")
async def process_batch(
    filenames: List[str],
    background_tasks: BackgroundTasks
) -> Dict:
    """
    Procesa un lote de boletines.
    
    Args:
        filenames: Lista de nombres de archivo
        background_tasks: Tareas en segundo plano
    """
    try:
        results = []
        for filename in filenames:
            try:
                # Convertir a texto
                txt_path = pdf_processor.process_pdf(filename)
                
                # Analizar con Watcher en segundo plano
                output_path = settings.DATA_DIR / "results" / f"{Path(filename).stem}_analysis.jsonl"
                background_tasks.add_task(
                    watcher_service.process_file,
                    txt_path,
                    output_path
                )
                
                results.append({
                    "filename": filename,
                    "status": "processing",
                    "text_file": str(txt_path),
                    "output_file": str(output_path)
                })
                
            except Exception as e:
                results.append({
                    "filename": filename,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "message": f"Procesando {len(filenames)} boletines",
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monthly-stats/")
async def get_monthly_stats(
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Obtiene estadísticas agrupadas por mes.
    
    Args:
        db: Sesión de base de datos
    """
    try:
        # Obtener todos los boletines
        boletines = await crud.get_boletines(db=db, limit=1000)
        
        # Agrupar por mes
        monthly_stats = {}
        
        for boletin in boletines:
            if boletin.date and boletin.date != 'unknown' and len(boletin.date) >= 6:
                month = boletin.date[:6]  # YYYYMM
                
                if month not in monthly_stats:
                    monthly_stats[month] = {
                        'month': month,
                        'total': 0,
                        'completed': 0,
                        'pending': 0,
                        'failed': 0,
                        'processing': 0
                    }
                
                monthly_stats[month]['total'] += 1
                
                if boletin.status == 'completed':
                    monthly_stats[month]['completed'] += 1
                elif boletin.status == 'pending':
                    monthly_stats[month]['pending'] += 1
                elif boletin.status == 'failed':
                    monthly_stats[month]['failed'] += 1
                elif boletin.status == 'processing':
                    monthly_stats[month]['processing'] += 1
        
        # Convertir a lista ordenada
        stats_list = sorted(monthly_stats.values(), key=lambda x: x['month'])
        
        return {
            "monthly_stats": stats_list,
            "total_months": len(stats_list)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{boletin_id}/analisis/")
async def get_boletin_analisis(
    boletin_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Obtiene los análisis de un boletín específico.
    
    Args:
        boletin_id: ID del boletín
        skip: Número de registros a omitir
        limit: Número máximo de registros a devolver
        db: Sesión de base de datos
    """
    try:
        # Verificar que el boletín existe
        boletin = await crud.get_boletin(db, boletin_id)
        if not boletin:
            raise HTTPException(status_code=404, detail="Boletín no encontrado")
        
        # Obtener análisis
        analisis_list = await crud.get_analisis_by_boletin(
            db=db,
            boletin_id=boletin_id,
            skip=skip,
            limit=limit
        )
        
        # Convertir a formato de respuesta
        analisis_data = []
        for analisis in analisis_list:
            analisis_data.append({
                "id": analisis.id,
                "fragmento": analisis.fragmento,
                "categoria": analisis.categoria,
                "entidad_beneficiaria": analisis.entidad_beneficiaria,
                "monto_estimado": analisis.monto_estimado,
                "riesgo": analisis.riesgo,
                "tipo_curro": analisis.tipo_curro,
                "accion_sugerida": analisis.accion_sugerida,
                "datos_extra": analisis.datos_extra,
                "created_at": analisis.created_at.isoformat() if analisis.created_at else None
            })
        
        return {
            "boletin": {
                "id": boletin.id,
                "filename": boletin.filename,
                "date": boletin.date,
                "section": boletin.section,
                "status": boletin.status
            },
            "analisis": analisis_data,
            "total": len(analisis_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-batch")
async def process_batch_by_date(
    status: Optional[str] = None,  # Hacer status opcional para permitir reprocesamiento
    limit: int = 100,  # Límite de seguridad reducido de 1000 a 100
    year: Optional[str] = None,
    month: Optional[str] = None,
    day: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Procesa boletines por lotes con filtros opcionales de fecha.
    NUEVO: Retorna inmediatamente y procesa en background para evitar timeouts.
    
    Args:
        status: Estado de los boletines a procesar. Si es None, procesa TODOS (permite reprocesar).
        limit: Límite máximo de boletines a procesar por sesión (máx: 100)
        year: Año para filtrar (formato: '2025')
        month: Mes para filtrar (formato: '01', '02', etc.)
        day: Día para filtrar (formato: '01', '02', etc.)
        background_tasks: Tareas en segundo plano
        db: Sesión de base de datos
    
    Returns:
        Respuesta inmediata con session_id para tracking
    """
    # Validar límite de seguridad
    MAX_BATCH_SIZE = 100
    if limit > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"El límite máximo permitido es {MAX_BATCH_SIZE} documentos por sesión. "
                   f"Por favor, usa filtros más específicos (día, mes) para procesar lotes más pequeños."
        )
    
    # Generar ID de sesión para tracking
    session_id = str(uuid.uuid4())[:8]
    
    try:
        from app.db.models import Boletin
        from sqlalchemy import select
        
        # Iniciar sesión de logging
        date_desc = f"{day}/{month}/{year}" if day and month and year else (f"{month}/{year}" if month and year else (year if year else "todos"))
        processing_logger.start_session(session_id, f"Extracción de boletines - {date_desc}")
        print(f"\n{'='*80}")
        print(f"[{session_id}] 🚀 INICIANDO EXTRACCIÓN DE BOLETINES")
        print(f"[{session_id}] 📅 Filtros: {date_desc}")
        print(f"[{session_id}] 📊 Status: {status or 'TODOS (reprocesar)'}")
        print(f"[{session_id}] 🎯 Límite: {limit}")
        print(f"{'='*80}\n")
        
        # Construir query base
        processing_logger.info(f"Construyendo query: status={status}, limit={limit}", session_id)
        
        # Si status es None, permitir reprocesamiento (todos los documentos)
        if status:
            query = select(Boletin).where(Boletin.status == status).limit(limit)
        else:
            # Sin filtro de status = reprocesar todos los documentos que coincidan con otros filtros
            query = select(Boletin).limit(limit)
            processing_logger.info("Modo reprocesamiento: se procesarán todos los documentos que coincidan", session_id)
        
        # Aplicar filtros de fecha si se proporcionan
        if year or month or day:
            # Construir fecha en formato YYYYMMDD para comparar
            date_filter = ""
            if year:
                date_filter = year
            if month:
                date_filter += month
            else:
                date_filter += "%"  # Comodín para cualquier mes
            
            if day:
                date_filter += day
            else:
                date_filter += "%"  # Comodín para cualquier día
            
            query = query.where(Boletin.date.like(f"{date_filter}%"))
            processing_logger.info(f"Filtro de fecha aplicado: {date_filter}", session_id)
        
        # Obtener boletines
        processing_logger.info("Consultando base de datos...", session_id)
        result = await db.execute(query)
        boletines = result.scalars().all()
        
        if not boletines:
            processing_logger.warning("No se encontraron boletines para procesar", session_id)
            processing_logger.end_session(session_id, success=True)
            return {
                "message": "No hay boletines para procesar con los filtros especificados",
                "processed": 0,
                "failed": 0,
                "total": 0,
                "session_id": session_id,
                "status": "completed"
            }
        
        processing_logger.success(f"Encontrados {len(boletines)} boletines para procesar", session_id)
        print(f"[{session_id}] ✅ Encontrados {len(boletines)} boletines:")
        for b in boletines:
            print(f"[{session_id}]    - {b.filename} (status: {b.status})")
        
        # Obtener IDs de los boletines para procesar en background
        boletin_ids = [b.id for b in boletines]
        total_count = len(boletines)
        
        # Agregar tarea en background
        background_tasks.add_task(
            process_boletines_background,
            boletin_ids=boletin_ids,
            session_id=session_id
        )
        
        # Retornar inmediatamente sin esperar el procesamiento
        return {
            "message": f"Procesamiento iniciado en segundo plano",
            "total": total_count,
            "session_id": session_id,
            "status": "processing",
            "filters": {
                "year": year,
                "month": month,
                "day": day,
                "status": status
            }
        }
    except Exception as e:
        processing_logger.error(f"Error al iniciar procesamiento: {str(e)}", session_id)
        processing_logger.end_session(session_id, success=False)
        raise HTTPException(status_code=500, detail=str(e))


async def process_boletines_background(boletin_ids: List[int], session_id: str):
    """
    Procesa boletines en segundo plano.
    Esta función se ejecuta de forma asíncrona sin bloquear la respuesta HTTP.
    """
    from app.db.session import async_session_maker
    
    processed = 0
    failed = 0
    
    async with async_session_maker() as db:
        try:
            # Obtener boletines por IDs
            result = await db.execute(
                select(Boletin).where(Boletin.id.in_(boletin_ids))
            )
            boletines = result.scalars().all()
            
            # Procesar cada boletín
            for idx, boletin in enumerate(boletines, 1):
                try:
                    processing_logger.progress(
                        f"Procesando {boletin.filename}", 
                        idx, 
                        len(boletines), 
                        session_id
                    )
                    print(f"[{session_id}] [{idx}/{len(boletines)}] 📄 Procesando: {boletin.filename}")
                    
                    # Construir ruta al PDF
                    year_str = boletin.date[:4]
                    month_str = boletin.date[4:6]
                    pdf_path = Path(settings.DATA_DIR) / "boletines" / year_str / month_str / boletin.filename
                    
                    if not pdf_path.exists():
                        boletin.status = "failed"
                        boletin.error_message = f"PDF no encontrado: {pdf_path}"
                        failed += 1
                        processing_logger.error(f"PDF no encontrado: {boletin.filename}", session_id)
                        print(f"[{session_id}] ❌ PDF no encontrado: {pdf_path}")
                        continue
                    
                    # Procesar PDF a texto
                    processing_logger.info(f"Extrayendo texto de {boletin.filename}...", session_id)
                    print(f"[{session_id}] 🔄 Extrayendo texto de {boletin.filename}...")
                    txt_path = await pdf_processor.process_pdf(pdf_path)
                    
                    # Actualizar estado del boletín
                    boletin.status = "processed"
                    boletin.error_message = None
                    processed += 1
                    processing_logger.success(f"Completado: {boletin.filename}", session_id)
                    print(f"[{session_id}] ✅ Completado: {boletin.filename} -> {txt_path}")
                    
                except Exception as e:
                    boletin.status = "failed"
                    boletin.error_message = str(e)
                    failed += 1
                    processing_logger.error(f"Error en {boletin.filename}: {str(e)}", session_id)
                    print(f"[{session_id}] ❌ Error en {boletin.filename}: {str(e)}")
            
            # Commit de todos los cambios
            processing_logger.info("Guardando cambios en la base de datos...", session_id)
            print(f"[{session_id}] 💾 Guardando cambios en la base de datos...")
            await db.commit()
            
            # Resumen final
            processing_logger.success(
                f"Procesamiento finalizado: {processed} exitosos, {failed} fallidos", 
                session_id
            )
            processing_logger.end_session(session_id, success=failed == 0)
            print(f"\n{'='*80}")
            print(f"[{session_id}] 🎉 PROCESAMIENTO FINALIZADO")
            print(f"[{session_id}] ✅ Exitosos: {processed}")
            print(f"[{session_id}] ❌ Fallidos: {failed}")
            print(f"[{session_id}] 📊 Total: {len(boletines)}")
            print(f"{'='*80}\n")
            
        except Exception as e:
            processing_logger.error(f"Error fatal en procesamiento background: {str(e)}", session_id)
            processing_logger.end_session(session_id, success=False)
            print(f"[{session_id}] ❌ ERROR FATAL: {str(e)}")


@router.get("/count")
async def get_boletines_count(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    day: Optional[str] = Query(None)
) -> Dict:
    """
    Cuenta boletines que coinciden con filtros específicos.
    Útil para saber cuántos documentos se procesarán antes de iniciar.
    """
    try:
        query = select(func.count(Boletin.id))
        
        # Filtrar por status
        if status:
            query = query.where(Boletin.status == status)
        
        # Filtrar por fecha (YYYYMMDD)
        if year or month or day:
            # Construir patrón de búsqueda
            date_pattern = ""
            if year:
                date_pattern += year
                if month:
                    date_pattern += month.zfill(2)
                    if day:
                        date_pattern += day.zfill(2)
            
            # Usar LIKE para búsqueda de patrón
            query = query.where(Boletin.date.like(f"{date_pattern}%"))
        
        result = await db.execute(query)
        count = result.scalar_one()
        
        return {
            "count": count,
            "filters": {
                "status": status,
                "year": year,
                "month": month,
                "day": day
            }
        }
    except Exception as e:
        import traceback
        print(f"Error in get_boletines_count: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats-wizard")
async def get_wizard_stats(db: AsyncSession = Depends(get_db)) -> Dict:
    """
    Obtiene estadísticas para el wizard de procesamiento.
    
    Returns:
        Estadísticas de boletines por estado (pending, completed, failed)
    """
    try:
        from sqlalchemy import func, select
        from app.db.models import Boletin, Analisis
        
        # Contar por estado
        stats_query = select(
            Boletin.status,
            func.count(Boletin.id).label('count')
        ).group_by(Boletin.status)
        
        result = await db.execute(stats_query)
        status_counts = {row[0]: row[1] for row in result.all()}
        
        # Obtener total
        total = sum(status_counts.values())
        
        # Contar análisis realizados
        analisis_count_query = select(func.count(Analisis.id))
        analisis_result = await db.execute(analisis_count_query)
        total_analisis = analisis_result.scalar() or 0
        
        return {
            "total_bulletins": total,
            "total_pending": status_counts.get('pending', 0),  # Descargados pero sin extraer
            "total_completed": status_counts.get('completed', 0),  # Con texto extraído
            "total_failed": status_counts.get('failed', 0),
            "total_processing": status_counts.get('processing', 0),
            "total_analyses": total_analisis,
            "status_breakdown": status_counts
        }
        
    except Exception as e:
        import traceback
        print(f"Error in get_wizard_stats: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

"""
API endpoints para gestión de boletines
"""

from typing import List, Dict
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.pdf_service import PDFProcessor
from app.services.watcher_service import WatcherService
from app.services.batch_processor import BatchProcessor
from app.db.session import get_db
from app.db import crud

router = APIRouter()
pdf_processor = PDFProcessor()
watcher_service = WatcherService()

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
                "analisis_count": analisis_count
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

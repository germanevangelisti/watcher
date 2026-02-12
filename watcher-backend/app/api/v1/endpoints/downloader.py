"""
🚀 BOLETINES DOWNLOADER API
Endpoints para descargar boletines oficiales de Córdoba de forma automatizada

REFACTORED: Now uses the PDS (Portal Data Scrapers) layer for modular extraction.
"""

import asyncio
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.scrapers.pds_prov import create_provincial_scraper
from app.scrapers.base_scraper import DocumentType
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuración - use centralized settings
BOLETINES_BASE_DIR = settings.BOLETINES_DIR

def get_boletin_path(year: int, month: int, filename: str) -> Path:
    """Retorna la ruta organizada del boletín"""
    return BOLETINES_BASE_DIR / str(year) / f"{month:02d}" / filename

class DownloadRequest(BaseModel):
    """Request para descargar boletines"""
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    sections: Optional[List[int]] = [1, 2, 3, 4, 5]  # Secciones a descargar
    skip_weekends: bool = True
    
class DownloadProgress(BaseModel):
    """Progreso de descarga"""
    total_files: int
    downloaded: int
    failed: int
    current_file: Optional[str]
    status: str  # 'downloading', 'completed', 'failed'
    errors: List[str] = []

class CalendarDay(BaseModel):
    """Información de un día en el calendario"""
    date: str
    is_weekend: bool
    sections_available: List[int]
    sections_downloaded: List[int]
    sections_analyzed: List[int]
    total_size_mb: Optional[float] = 0.0

# Estado global para tracking de descargas (en producción usar Redis/DB)
download_status: Dict[str, DownloadProgress] = {}

def daterange(start_date: date, end_date: date):
    """Generador de rango de fechas"""
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(n)

async def download_single_boletin(
    year: int,
    month: int,
    day: int,
    section: int,
    output_dir: Path = None
) -> Dict:
    """
    Descarga un boletín específico usando el Provincial Scraper.
    
    This function now delegates to the PDS-PROV scraper for actual downloading.
    """
    scraper = create_provincial_scraper(output_dir=output_dir or BOLETINES_BASE_DIR)
    
    target_date = date(year, month, day)
    result = await scraper.download_single(
        target_date=target_date,
        document_type=DocumentType.BOLETIN,
        section=section
    )
    
    # Convert ScraperResult to dict for backward compatibility
    return {
        "filename": result.filename,
        "status": result.status,
        "size": result.size,
        "path": result.path,
        "url": result.url,
        "error": result.error
    }

async def download_boletines_task(
    task_id: str,
    start_date: date,
    end_date: date,
    sections: List[int],
    skip_weekends: bool
):
    """
    Tarea en background para descargar boletines usando el Provincial Scraper.
    
    Refactored to use PDS-PROV for better modularity and maintainability.
    """
    # Asegurar que existe el directorio base
    BOLETINES_BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Calcular total de archivos a descargar
    total_files = 0
    for single_date in daterange(start_date, end_date):
        if skip_weekends and single_date.weekday() >= 5:
            continue
        total_files += len(sections)
    
    # Inicializar estado
    download_status[task_id] = DownloadProgress(
        total_files=total_files,
        downloaded=0,
        failed=0,
        current_file=None,
        status="downloading"
    )
    
    try:
        # Create scraper instance
        scraper = create_provincial_scraper(output_dir=BOLETINES_BASE_DIR)
        
        # Use scraper's download_range method
        results = await scraper.download_range(
            start_date=start_date,
            end_date=end_date,
            document_type=DocumentType.BOLETIN,
            sections=sections
        )
        
        # Update download status based on results
        for result in results:
            if result.status in ['downloaded', 'exists']:
                download_status[task_id].downloaded += 1
            else:
                download_status[task_id].failed += 1
                if result.error:
                    download_status[task_id].errors.append(
                        f"{result.filename}: {result.error}"
                    )
        
        # Completado exitosamente
        download_status[task_id].status = "completed"
        download_status[task_id].current_file = None
        
        logger.info(f"✅ Descarga completada: {task_id}")
        logger.info(f"   Downloaded: {download_status[task_id].downloaded}")
        logger.info(f"   Failed: {download_status[task_id].failed}")
        
    except Exception as e:
        logger.error(f"❌ Error en tarea de descarga {task_id}: {e}")
        download_status[task_id].status = "failed"
        download_status[task_id].errors.append(f"Fatal error: {str(e)}")

@router.post("/download/start")
async def start_download(
    request: DownloadRequest,
    background_tasks: BackgroundTasks
):
    """
    Inicia la descarga de boletines en background
    """
    try:
        # Validar fechas
        start_date = date.fromisoformat(request.start_date)
        end_date = date.fromisoformat(request.end_date)
        
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="start_date debe ser menor que end_date")
        
        # Generar ID único para la tarea
        task_id = f"download_{start_date.isoformat()}_{end_date.isoformat()}"
        
        # Verificar si ya existe una tarea en progreso
        if task_id in download_status and download_status[task_id].status == "downloading":
            raise HTTPException(status_code=409, detail="Ya existe una descarga en progreso para este rango")
        
        # Agregar tarea en background
        background_tasks.add_task(
            download_boletines_task,
            task_id=task_id,
            start_date=start_date,
            end_date=end_date,
            sections=request.sections,
            skip_weekends=request.skip_weekends
        )
        
        return {
            "task_id": task_id,
            "message": "Descarga iniciada",
            "start_date": request.start_date,
            "end_date": request.end_date,
            "sections": request.sections
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Formato de fecha inválido: {str(e)}")
    except Exception as e:
        logger.error(f"Error iniciando descarga: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/status/{task_id}")
async def get_download_status(task_id: str) -> DownloadProgress:
    """
    Obtiene el estado de una descarga en progreso
    """
    if task_id not in download_status:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    return download_status[task_id]

@router.get("/download/active")
async def get_active_downloads() -> List[Dict]:
    """
    Lista todas las descargas activas
    """
    active = []
    for task_id, status in download_status.items():
        if status.status == "downloading":
            active.append({
                "task_id": task_id,
                "progress": status
            })
    
    return active

@router.get("/calendar")
async def get_calendar(
    year: int,
    month: int
) -> Dict:
    """
    Obtiene el calendario de boletines para un mes específico
    Muestra qué está disponible, descargado y analizado
    """
    try:
        # Calcular rango de fechas del mes
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        calendar_days = []
        
        for single_date in daterange(start_date, end_date):
            is_weekend = single_date.weekday() >= 5
            
            # Verificar qué secciones están descargadas
            sections_downloaded = []
            total_size = 0
            
            for section in [1, 2, 3, 4, 5]:
                filename = f"{single_date.year}{single_date.month:02d}{single_date.day:02d}_{section}_Secc.pdf"
                filepath = get_boletin_path(single_date.year, single_date.month, filename)
                
                if filepath.exists():
                    sections_downloaded.append(section)
                    total_size += filepath.stat().st_size
            
            # TODO: Integrar con DS Lab para ver qué está analizado
            sections_analyzed = []  # Placeholder
            
            calendar_days.append(CalendarDay(
                date=single_date.isoformat(),
                is_weekend=is_weekend,
                sections_available=[1, 2, 3, 4, 5] if not is_weekend else [],
                sections_downloaded=sections_downloaded,
                sections_analyzed=sections_analyzed,
                total_size_mb=total_size / (1024 * 1024) if total_size > 0 else 0.0
            ))
        
        # Estadísticas del mes
        total_available = sum(len(day.sections_available) for day in calendar_days)
        total_downloaded = sum(len(day.sections_downloaded) for day in calendar_days)
        total_size_mb = sum(day.total_size_mb for day in calendar_days)
        
        return {
            "year": year,
            "month": month,
            "days": [day.dict() for day in calendar_days],
            "stats": {
                "total_available": total_available,
                "total_downloaded": total_downloaded,
                "total_size_mb": round(total_size_mb, 2),
                "completion_percentage": round((total_downloaded / total_available * 100) if total_available > 0 else 0, 1)
            }
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo calendario: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/summary")
async def get_download_summary() -> Dict:
    """
    Resumen general de todos los boletines descargados
    """
    try:
        if not BOLETINES_BASE_DIR.exists():
            return {
                "total_files": 0,
                "total_size_mb": 0,
                "by_month": {},
                "by_section": {}
            }
        
        # Recorrer estructura organizada año/mes
        pdf_files = []
        for year_dir in BOLETINES_BASE_DIR.iterdir():
            if year_dir.is_dir() and year_dir.name.isdigit():
                for month_dir in year_dir.iterdir():
                    if month_dir.is_dir():
                        pdf_files.extend(list(month_dir.glob("*.pdf")))
        
        total_size = sum(f.stat().st_size for f in pdf_files)
        
        # Agrupar por mes
        by_month = {}
        by_section = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for pdf_file in pdf_files:
            # Parsear filename: YYYYMMDD_N_Secc.pdf
            try:
                name = pdf_file.stem
                date_part = name.split('_')[0]  # YYYYMMDD
                section = int(name.split('_')[1])  # N
                
                month_key = date_part[:6]  # YYYYMM
                
                by_month[month_key] = by_month.get(month_key, 0) + 1
                by_section[section] = by_section.get(section, 0) + 1
                
            except Exception as e:
                logger.warning(f"Error parseando {pdf_file.name}: {e}")
                continue
        
        return {
            "total_files": len(pdf_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_month": by_month,
            "by_section": by_section
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo resumen: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/download/{task_id}")
async def cancel_download(task_id: str):
    """
    Cancela una descarga en progreso (marca como cancelada)
    """
    if task_id not in download_status:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    if download_status[task_id].status != "downloading":
        raise HTTPException(status_code=400, detail="La tarea no está en progreso")
    
    # Marcar como cancelada
    download_status[task_id].status = "cancelled"
    
    return {
        "message": "Descarga cancelada",
        "task_id": task_id
    }


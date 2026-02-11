"""
API Endpoints para sincronización automática de boletines.
"""

import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.sync_service import SyncService
from app.core.scheduler import reconfigure_scheduler

logger = logging.getLogger(__name__)

router = APIRouter()


class SyncScheduleConfig(BaseModel):
    """Configuración del scheduler de sincronización."""
    enabled: bool = Field(description="Si el sync automático está habilitado")
    frequency: str = Field(default="daily", description="Frecuencia: daily, weekly, manual")
    hour: int = Field(default=6, ge=0, le=23, description="Hora del día para ejecutar (0-23)")


class SyncStartRequest(BaseModel):
    """Request para iniciar sincronización."""
    process_after_download: bool = Field(
        default=True, 
        description="Si debe procesar los boletines después de descargar"
    )


@router.get("/status")
async def get_sync_status(db: AsyncSession = Depends(get_db)) -> Dict:
    """
    Obtiene el estado actual de sincronización.
    
    Returns:
        Estado completo de sincronización incluyendo:
        - status: Estado actual (idle, syncing, processing, error)
        - last_synced_date: Última fecha sincronizada
        - last_detected_date: Última fecha detectada en filesystem
        - boletines_pending: Número de boletines pendientes
        - boletines_downloaded/processed/failed: Estadísticas
        - auto_sync_enabled: Si está habilitado el scheduler
        - next_scheduled_sync: Próxima ejecución programada
    """
    try:
        sync_service = SyncService(db)
        status = await sync_service.get_sync_status()
        return status
    
    except Exception as e:
        logger.error(f"Error obteniendo estado de sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_sync(
    request: SyncStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Inicia una sincronización manual.
    
    La sincronización se ejecuta en background:
    1. Detecta el último boletín descargado
    2. Calcula fechas faltantes hasta hoy
    3. Descarga los boletines faltantes
    4. Opcionalmente los procesa con IA
    
    Args:
        request: Configuración de la sincronización
        background_tasks: Tareas en background de FastAPI
        db: Sesión de base de datos
        
    Returns:
        Mensaje de confirmación
    """
    try:
        sync_service = SyncService(db)
        
        # Verificar si ya hay una sync en progreso
        if sync_service.is_syncing:
            raise HTTPException(
                status_code=409, 
                detail="Ya hay una sincronización en progreso"
            )
        
        # Iniciar sync en background
        background_tasks.add_task(
            sync_service.sync_to_today,
            process_after_download=request.process_after_download
        )
        
        return {
            "message": "Sincronización iniciada",
            "process_after_download": request.process_after_download
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error iniciando sincronización: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_sync(db: AsyncSession = Depends(get_db)) -> Dict:
    """
    Cancela la sincronización en progreso.
    
    La cancelación es "graceful": el sistema terminará la operación
    actual antes de detenerse completamente.
    
    Returns:
        Mensaje de confirmación
    """
    try:
        sync_service = SyncService(db)
        
        if not sync_service.is_syncing:
            raise HTTPException(
                status_code=400,
                detail="No hay sincronización en progreso"
            )
        
        await sync_service.cancel_sync()
        
        return {
            "message": "Cancelación solicitada. La sincronización se detendrá en breve."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelando sincronización: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/schedule")
async def update_schedule(
    config: SyncScheduleConfig,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Actualiza la configuración del scheduler automático.
    
    Permite configurar:
    - Si el sync automático está habilitado
    - Frecuencia: daily (diario) o weekly (semanal)
    - Hora del día para ejecutar (0-23)
    
    Args:
        config: Configuración del scheduler
        db: Sesión de base de datos
        
    Returns:
        Configuración actualizada y próxima ejecución
    """
    try:
        # Validar frecuencia
        if config.frequency not in ["daily", "weekly", "manual"]:
            raise HTTPException(
                status_code=400,
                detail="Frecuencia inválida. Debe ser: daily, weekly, o manual"
            )
        
        sync_service = SyncService(db)
        
        await sync_service.update_schedule_config(
            enabled=config.enabled,
            frequency=config.frequency,
            hour=config.hour
        )
        
        # Reconfigurar el scheduler para aplicar cambios
        await reconfigure_scheduler()
        
        # Obtener estado actualizado
        status = await sync_service.get_sync_status()
        
        return {
            "message": "Configuración de scheduler actualizada",
            "config": {
                "enabled": config.enabled,
                "frequency": config.frequency,
                "hour": config.hour
            },
            "next_scheduled_sync": status["next_scheduled_sync"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_sync_history(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Obtiene el historial de sincronizaciones.
    
    Args:
        limit: Número máximo de registros a retornar
        db: Sesión de base de datos
        
    Returns:
        Lista de sincronizaciones históricas
    """
    try:
        # Por ahora, retornar solo el estado actual
        # En el futuro, podríamos crear una tabla sync_history
        sync_service = SyncService(db)
        current_status = await sync_service.get_sync_status()
        
        history = []
        if current_status.get("last_sync_timestamp"):
            history.append({
                "timestamp": current_status["last_sync_timestamp"],
                "status": "completed",
                "boletines_downloaded": current_status["boletines_downloaded"],
                "boletines_processed": current_status["boletines_processed"],
                "boletines_failed": current_status["boletines_failed"]
            })
        
        return {
            "history": history,
            "total": len(history)
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        raise HTTPException(status_code=500, detail=str(e))

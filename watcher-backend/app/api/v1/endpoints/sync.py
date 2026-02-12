"""
API Endpoints para sincronización automática de boletines.
Incluye sync global y sync por jurisdicción.
"""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import JurisdiccionSyncConfig, Jurisdiccion
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


# ============================================================================
# JURISDICTION-SPECIFIC SYNC ENDPOINTS (v1.1 Phase 2)
# ============================================================================

class JurisdiccionSyncConfigRequest(BaseModel):
    """Request para crear o actualizar configuración de sync por jurisdicción."""
    source_url_template: Optional[str] = Field(None, description="URL template con {year}, {month}, {day}, {section}")
    scraper_type: str = Field(default="generic", description="Tipo de scraper: provincial, municipal, national, generic")
    sync_enabled: bool = Field(default=False)
    sync_frequency: str = Field(default="manual", description="manual, daily, weekly")
    sections_to_sync: Optional[List[str]] = Field(None, description='Secciones a sincronizar, e.g. ["1_Secc", "2_Secc"]')
    extra_config: Optional[Dict] = Field(None, description="Configuración adicional del scraper")


class JurisdiccionSyncConfigResponse(BaseModel):
    """Response para configuración de sync."""
    id: int
    jurisdiccion_id: int
    jurisdiccion_nombre: Optional[str] = None
    source_url_template: Optional[str]
    scraper_type: str
    sync_enabled: bool
    sync_frequency: str
    last_sync_date: Optional[str]
    last_sync_status: str
    last_sync_error: Optional[str]
    sections_to_sync: Optional[List[str]]
    extra_config: Optional[Dict]


@router.get("/jurisdictions/configs")
async def list_jurisdiction_sync_configs(
    db: AsyncSession = Depends(get_db)
) -> List[Dict]:
    """
    Lista todas las configuraciones de sync por jurisdicción.
    """
    try:
        stmt = select(JurisdiccionSyncConfig, Jurisdiccion.nombre).outerjoin(
            Jurisdiccion, JurisdiccionSyncConfig.jurisdiccion_id == Jurisdiccion.id
        )
        result = await db.execute(stmt)
        rows = result.all()
        
        configs = []
        for config, nombre in rows:
            configs.append({
                "id": config.id,
                "jurisdiccion_id": config.jurisdiccion_id,
                "jurisdiccion_nombre": nombre,
                "source_url_template": config.source_url_template,
                "scraper_type": config.scraper_type,
                "sync_enabled": config.sync_enabled,
                "sync_frequency": config.sync_frequency,
                "last_sync_date": str(config.last_sync_date) if config.last_sync_date else None,
                "last_sync_status": config.last_sync_status,
                "last_sync_error": config.last_sync_error,
                "sections_to_sync": config.sections_to_sync,
                "extra_config": config.extra_config,
            })
        
        return configs
    
    except Exception as e:
        logger.error(f"Error listing sync configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jurisdictions/{jurisdiccion_id}/config")
async def get_jurisdiction_sync_config(
    jurisdiccion_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Obtiene la configuración de sync para una jurisdicción.
    """
    try:
        stmt = select(JurisdiccionSyncConfig).where(
            JurisdiccionSyncConfig.jurisdiccion_id == jurisdiccion_id
        )
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if not config:
            return {
                "jurisdiccion_id": jurisdiccion_id,
                "configured": False,
                "message": "No hay configuración de sync para esta jurisdicción"
            }
        
        return {
            "id": config.id,
            "jurisdiccion_id": config.jurisdiccion_id,
            "source_url_template": config.source_url_template,
            "scraper_type": config.scraper_type,
            "sync_enabled": config.sync_enabled,
            "sync_frequency": config.sync_frequency,
            "last_sync_date": str(config.last_sync_date) if config.last_sync_date else None,
            "last_sync_status": config.last_sync_status,
            "last_sync_error": config.last_sync_error,
            "sections_to_sync": config.sections_to_sync,
            "extra_config": config.extra_config,
            "configured": True,
        }
    
    except Exception as e:
        logger.error(f"Error getting sync config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/jurisdictions/{jurisdiccion_id}/config")
async def upsert_jurisdiction_sync_config(
    jurisdiccion_id: int,
    request: JurisdiccionSyncConfigRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Crea o actualiza la configuración de sync para una jurisdicción.
    """
    try:
        # Verify jurisdiction exists
        j_stmt = select(Jurisdiccion).where(Jurisdiccion.id == jurisdiccion_id)
        j_result = await db.execute(j_stmt)
        jurisdiccion = j_result.scalar_one_or_none()
        
        if not jurisdiccion:
            raise HTTPException(status_code=404, detail=f"Jurisdicción {jurisdiccion_id} no encontrada")
        
        # Check existing config
        stmt = select(JurisdiccionSyncConfig).where(
            JurisdiccionSyncConfig.jurisdiccion_id == jurisdiccion_id
        )
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if config:
            # Update existing
            config.source_url_template = request.source_url_template
            config.scraper_type = request.scraper_type
            config.sync_enabled = request.sync_enabled
            config.sync_frequency = request.sync_frequency
            config.sections_to_sync = request.sections_to_sync
            config.extra_config = request.extra_config
        else:
            # Create new
            config = JurisdiccionSyncConfig(
                jurisdiccion_id=jurisdiccion_id,
                source_url_template=request.source_url_template,
                scraper_type=request.scraper_type,
                sync_enabled=request.sync_enabled,
                sync_frequency=request.sync_frequency,
                sections_to_sync=request.sections_to_sync,
                extra_config=request.extra_config,
            )
            db.add(config)
        
        await db.commit()
        await db.refresh(config)
        
        return {
            "message": "Configuración de sync actualizada",
            "id": config.id,
            "jurisdiccion_id": jurisdiccion_id,
            "jurisdiccion_nombre": jurisdiccion.nombre,
            "sync_enabled": config.sync_enabled,
            "scraper_type": config.scraper_type,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error upserting sync config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jurisdictions/{jurisdiccion_id}/trigger")
async def trigger_jurisdiction_sync(
    jurisdiccion_id: int,
    background_tasks: BackgroundTasks,
    process_after_download: bool = Query(True),
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Trigger sync for a specific jurisdiction.
    Downloads boletines from the configured source and optionally processes them.
    """
    try:
        # Get sync config
        stmt = select(JurisdiccionSyncConfig).where(
            JurisdiccionSyncConfig.jurisdiccion_id == jurisdiccion_id
        )
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"No hay configuración de sync para jurisdicción {jurisdiccion_id}"
            )
        
        if not config.sync_enabled:
            raise HTTPException(
                status_code=400,
                detail="La sincronización está deshabilitada para esta jurisdicción"
            )
        
        if config.last_sync_status == "syncing":
            raise HTTPException(
                status_code=409,
                detail="Ya hay una sincronización en progreso para esta jurisdicción"
            )
        
        # Mark as syncing
        config.last_sync_status = "syncing"
        config.last_sync_error = None
        await db.commit()
        
        # Get jurisdiction info
        j_stmt = select(Jurisdiccion).where(Jurisdiccion.id == jurisdiccion_id)
        j_result = await db.execute(j_stmt)
        jurisdiccion = j_result.scalar_one_or_none()
        
        # Start sync in background
        background_tasks.add_task(
            _run_jurisdiction_sync,
            jurisdiccion_id=jurisdiccion_id,
            scraper_type=config.scraper_type,
            source_url_template=config.source_url_template,
            sections=config.sections_to_sync,
            process_after_download=process_after_download,
        )
        
        return {
            "message": f"Sincronización iniciada para {jurisdiccion.nombre if jurisdiccion else jurisdiccion_id}",
            "jurisdiccion_id": jurisdiccion_id,
            "scraper_type": config.scraper_type,
            "process_after_download": process_after_download,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering jurisdiction sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _run_jurisdiction_sync(
    jurisdiccion_id: int,
    scraper_type: str,
    source_url_template: Optional[str],
    sections: Optional[List[str]],
    process_after_download: bool,
):
    """Background task: run sync for a specific jurisdiction."""
    from app.db.session import async_session_maker
    from datetime import datetime, date
    
    async with async_session_maker() as db:
        try:
            # Get config record
            stmt = select(JurisdiccionSyncConfig).where(
                JurisdiccionSyncConfig.jurisdiccion_id == jurisdiccion_id
            )
            result = await db.execute(stmt)
            config = result.scalar_one_or_none()
            
            if not config:
                return
            
            # Use existing SyncService for the actual sync work
            sync_service = SyncService(db)
            
            # For now, delegate to the existing global sync
            # In the future, this can be customized per scraper_type
            logger.info(f"Starting sync for jurisdiction {jurisdiccion_id} with scraper={scraper_type}")
            
            await sync_service.sync_to_today(
                process_after_download=process_after_download
            )
            
            # Update config with results
            config.last_sync_status = "completed"
            config.last_sync_date = date.today()
            config.last_sync_timestamp = datetime.utcnow()
            config.last_sync_error = None
            await db.commit()
            
            logger.info(f"Sync completed for jurisdiction {jurisdiccion_id}")
        
        except Exception as e:
            logger.error(f"Sync failed for jurisdiction {jurisdiccion_id}: {e}")
            try:
                config.last_sync_status = "failed"
                config.last_sync_error = str(e)
                config.last_sync_timestamp = datetime.utcnow()
                await db.commit()
            except Exception:
                pass

"""
Scheduler para sincronización automática de boletines.

Usa APScheduler para ejecutar tareas programadas como:
- Sincronización diaria/semanal de boletines
- Mantenimiento de base de datos
- Limpieza de archivos temporales
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Instancia global del scheduler
scheduler = AsyncIOScheduler()


async def scheduled_sync_job():
    """
    Job de sincronización programado.
    
    Se ejecuta según la configuración del usuario (diario/semanal).
    """
    from app.db.database import AsyncSessionLocal
    from app.services.sync_service import SyncService
    
    logger.info("Iniciando sincronización programada...")
    
    async with AsyncSessionLocal() as db:
        try:
            sync_service = SyncService(db)
            
            # Verificar si está habilitado
            sync_state = await sync_service.get_or_create_sync_state()
            
            if not sync_state.auto_sync_enabled:
                logger.info("Sincronización automática deshabilitada, saltando...")
                return
            
            # Ejecutar sincronización
            result = await sync_service.sync_to_today(process_after_download=True)
            
            logger.info(f"Sincronización programada completada: {result}")
            
        except Exception as e:
            logger.error(f"Error en sincronización programada: {e}", exc_info=True)


async def configure_scheduler_from_db():
    """
    Configura el scheduler basándose en la configuración de la base de datos.
    
    Lee la configuración de SyncState y ajusta los jobs del scheduler.
    """
    from app.db.database import AsyncSessionLocal
    from app.services.sync_service import SyncService
    
    async with AsyncSessionLocal() as db:
        try:
            sync_service = SyncService(db)
            sync_state = await sync_service.get_or_create_sync_state()
            
            # Remover job anterior si existe
            if scheduler.get_job('sync_job'):
                scheduler.remove_job('sync_job')
            
            # Solo agregar si está habilitado
            if sync_state.auto_sync_enabled and sync_state.sync_frequency != "manual":
                hour = sync_state.sync_hour or 6
                
                if sync_state.sync_frequency == "daily":
                    # Todos los días a la hora configurada
                    trigger = CronTrigger(hour=hour, minute=0)
                    logger.info(f"Configurando sync diario a las {hour}:00")
                    
                elif sync_state.sync_frequency == "weekly":
                    # Cada lunes a la hora configurada
                    trigger = CronTrigger(day_of_week='mon', hour=hour, minute=0)
                    logger.info(f"Configurando sync semanal (lunes) a las {hour}:00")
                
                else:
                    logger.warning(f"Frecuencia desconocida: {sync_state.sync_frequency}")
                    return
                
                scheduler.add_job(
                    scheduled_sync_job,
                    trigger=trigger,
                    id='sync_job',
                    name='Sincronización automática de boletines',
                    replace_existing=True
                )
                
                logger.info("Scheduler configurado exitosamente")
            else:
                logger.info("Sincronización automática deshabilitada")
                
        except Exception as e:
            logger.error(f"Error configurando scheduler: {e}", exc_info=True)


def start_scheduler():
    """Inicia el scheduler."""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler iniciado")
    else:
        logger.warning("Scheduler ya está corriendo")


def stop_scheduler():
    """Detiene el scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler detenido")
    else:
        logger.warning("Scheduler no está corriendo")


async def reconfigure_scheduler():
    """
    Reconfigura el scheduler.
    
    Debe llamarse cuando el usuario actualiza la configuración
    desde el endpoint /sync/schedule.
    """
    logger.info("Reconfigurando scheduler...")
    await configure_scheduler_from_db()

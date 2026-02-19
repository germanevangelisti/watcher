"""
Servicio de sincronización automática de boletines.

Este servicio detecta el último boletín procesado, calcula los faltantes
hasta hoy, los descarga y procesa automáticamente.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import SyncState
from app.api.v1.endpoints.downloader import download_boletines_task, download_status
from app.services.batch_processor import BatchProcessor

logger = logging.getLogger(__name__)

# Configuración
BOLETINES_BASE_DIR = Path("/Users/germanevangelisti/watcher-agent/boletines")
SECTIONS = [1, 2, 3, 4, 5]


class SyncService:
    """Servicio de sincronización automática de boletines."""
    
    def __init__(self, db: AsyncSession):
        """
        Inicializa el servicio de sincronización.
        
        Args:
            db: Sesión de base de datos
        """
        self.db = db
        self.is_syncing = False
        self.cancel_requested = False
    
    async def get_or_create_sync_state(self) -> SyncState:
        """Obtiene o crea el estado de sincronización."""
        result = await self.db.execute(select(SyncState).limit(1))
        sync_state = result.scalar_one_or_none()
        
        if not sync_state:
            sync_state = SyncState(
                status="idle",
                last_synced_date=None,
                boletines_pending=0,
                boletines_downloaded=0,
                boletines_processed=0
            )
            self.db.add(sync_state)
            await self.db.commit()
            await self.db.refresh(sync_state)
        
        return sync_state
    
    async def detect_last_synced_date(self) -> Optional[date]:
        """
        Detecta la última fecha con boletines descargados escaneando el filesystem.
        
        Returns:
            La fecha más reciente encontrada o None si no hay boletines
        """
        logger.info("Detectando último boletín descargado...")
        
        latest_date = None
        pattern = re.compile(r'^(\d{4})(\d{2})(\d{2})_\d+_Secc\.pdf$')
        
        try:
            # Escanear directorio de boletines
            for year_dir in sorted(BOLETINES_BASE_DIR.glob("*"), reverse=True):
                if not year_dir.is_dir():
                    continue
                    
                for month_dir in sorted(year_dir.glob("*"), reverse=True):
                    if not month_dir.is_dir():
                        continue
                    
                    # Obtener archivos PDF ordenados por nombre (descendente)
                    pdf_files = sorted(month_dir.glob("*.pdf"), reverse=True)
                    
                    for pdf_file in pdf_files:
                        match = pattern.match(pdf_file.name)
                        if match:
                            year, month, day = match.groups()
                            file_date = date(int(year), int(month), int(day))
                            
                            if latest_date is None or file_date > latest_date:
                                latest_date = file_date
                    
                    # Si encontramos algo en este mes, no necesitamos buscar más atrás
                    if latest_date:
                        break
                
                # Si encontramos algo en este año, no necesitamos buscar más atrás
                if latest_date:
                    break
            
            if latest_date:
                logger.info(f"Último boletín encontrado: {latest_date}")
            else:
                logger.warning("No se encontraron boletines descargados")
            
            return latest_date
            
        except Exception as e:
            logger.error(f"Error detectando último boletín: {e}")
            return None
    
    def calculate_missing_dates(self, start_date: date, end_date: date = None) -> List[date]:
        """
        Calcula las fechas faltantes entre start_date y end_date (o hoy).
        Excluye fines de semana.
        
        Args:
            start_date: Fecha de inicio (no incluida)
            end_date: Fecha de fin (incluida), por defecto hoy
            
        Returns:
            Lista de fechas faltantes (días hábiles)
        """
        if end_date is None:
            end_date = date.today()
        
        missing_dates = []
        current_date = start_date + timedelta(days=1)
        
        while current_date <= end_date:
            # Excluir fines de semana (5=sábado, 6=domingo)
            if current_date.weekday() < 5:
                missing_dates.append(current_date)
            current_date += timedelta(days=1)
        
        return missing_dates
    
    async def sync_to_today(self, process_after_download: bool = True) -> Dict:
        """
        Sincroniza boletines hasta hoy: detecta faltantes, descarga y procesa.
        
        Args:
            process_after_download: Si debe procesar los boletines después de descargar
            
        Returns:
            Estadísticas de la sincronización
        """
        if self.is_syncing:
            raise ValueError("Ya hay una sincronización en progreso")
        
        self.is_syncing = True
        self.cancel_requested = False
        
        sync_state = await self.get_or_create_sync_state()
        
        try:
            # Actualizar estado
            sync_state.status = "syncing"
            sync_state.current_operation = "Detectando último boletín"
            sync_state.error_message = None
            await self.db.commit()
            
            # 1. Detectar última fecha sincronizada
            last_synced = await self.detect_last_synced_date()
            
            if last_synced is None:
                # Si no hay boletines, empezar desde hace 1 mes
                last_synced = date.today() - timedelta(days=30)
                logger.info(f"No hay boletines previos, iniciando desde {last_synced}")
            
            # 2. Calcular fechas faltantes
            sync_state.current_operation = "Calculando fechas faltantes"
            await self.db.commit()
            
            missing_dates = self.calculate_missing_dates(last_synced)
            
            if not missing_dates:
                logger.info("No hay boletines faltantes")
                sync_state.status = "idle"
                sync_state.boletines_pending = 0
                sync_state.current_operation = None
                sync_state.last_sync_timestamp = datetime.utcnow()
                await self.db.commit()
                
                return {
                    "status": "up_to_date",
                    "message": "No hay boletines faltantes",
                    "last_synced_date": last_synced.isoformat(),
                    "missing_dates": 0
                }
            
            logger.info(f"Encontradas {len(missing_dates)} fechas faltantes")
            sync_state.boletines_pending = len(missing_dates) * len(SECTIONS)
            await self.db.commit()
            
            # 3. Descargar boletines por lotes (1 semana a la vez para evitar timeouts)
            sync_state.current_operation = "Descargando boletines"
            await self.db.commit()
            
            total_downloaded = 0
            total_failed = 0
            
            # Agrupar fechas en semanas
            week_batches = self._group_dates_by_week(missing_dates)
            
            for batch_idx, week_dates in enumerate(week_batches, 1):
                if self.cancel_requested:
                    logger.info("Sincronización cancelada por el usuario")
                    break
                
                logger.info(f"Descargando lote {batch_idx}/{len(week_batches)}: {week_dates[0]} a {week_dates[-1]}")
                
                # Descargar semana
                start_date_str = week_dates[0].isoformat()
                end_date_str = week_dates[-1].isoformat()
                
                task_id = f"sync_{start_date_str}_{end_date_str}"
                
                # Ejecutar descarga
                await download_boletines_task(
                    task_id=task_id,
                    start_date=week_dates[0],
                    end_date=week_dates[-1],
                    sections=SECTIONS,
                    skip_weekends=True
                )
                
                # Obtener resultado del download_status global
                if task_id in download_status:
                    batch_result = download_status[task_id]
                    total_downloaded += batch_result.downloaded
                    total_failed += batch_result.failed
                    
                    # Actualizar sync_state con contadores reales
                    sync_state.boletines_downloaded = total_downloaded
                    sync_state.boletines_failed = total_failed
                    sync_state.boletines_pending = sync_state.boletines_pending - batch_result.downloaded
                    await self.db.commit()
                    
                    logger.info(f"Lote {batch_idx} completado: {batch_result.downloaded} descargados, {batch_result.failed} fallidos")
                
                # Pequeña pausa entre lotes
                await asyncio.sleep(2)
            
            # Actualizar totales finales (ya se fueron actualizando durante el loop)
            sync_state.boletines_downloaded = total_downloaded
            sync_state.boletines_failed = total_failed
            await self.db.commit()
            
            # 4. Procesar boletines si está habilitado
            total_processed = 0
            if process_after_download and not self.cancel_requested:
                sync_state.status = "processing"
                sync_state.current_operation = "Procesando boletines"
                await self.db.commit()
                
                logger.info("Iniciando procesamiento de boletines descargados...")
                
                # Procesar cada mes descargado
                months_to_process = set((d.year, d.month) for d in missing_dates)
                
                for year, month in sorted(months_to_process):
                    if self.cancel_requested:
                        break
                    
                    month_dir = BOLETINES_BASE_DIR / str(year) / f"{month:02d}"
                    
                    if month_dir.exists():
                        logger.info(f"Procesando mes {year}-{month:02d}")
                        
                        try:
                            # Usar BatchProcessor
                            processor = BatchProcessor(self.db, use_mock=True)
                            result = await processor.process_directory(
                                source_dir=month_dir,
                                batch_size=5
                            )
                            total_processed += result.get("processed", 0)
                            
                        except Exception as e:
                            logger.error(f"Error procesando {month_dir}: {e}")
            
            sync_state.boletines_processed = total_processed
            
            # 5. Actualizar estado final
            if self.cancel_requested:
                sync_state.status = "cancelled"
                sync_state.current_operation = None
            else:
                sync_state.status = "idle"
                sync_state.current_operation = None
                sync_state.last_synced_date = missing_dates[-1] if missing_dates else last_synced
                sync_state.last_sync_timestamp = datetime.utcnow()
                sync_state.boletines_pending = 0
            
            await self.db.commit()
            
            result = {
                "status": "completed" if not self.cancel_requested else "cancelled",
                "last_synced_date": last_synced.isoformat(),
                "missing_dates": len(missing_dates),
                "boletines_downloaded": total_downloaded,
                "boletines_processed": total_processed,
                "boletines_failed": total_failed
            }
            
            logger.info(f"Sincronización completada: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error en sincronización: {e}", exc_info=True)
            
            sync_state.status = "error"
            sync_state.error_message = str(e)
            sync_state.current_operation = None
            await self.db.commit()
            
            raise
        
        finally:
            self.is_syncing = False
            self.cancel_requested = False
    
    def _group_dates_by_week(self, dates: List[date]) -> List[List[date]]:
        """Agrupa fechas en lotes de una semana."""
        if not dates:
            return []
        
        batches = []
        current_batch = []
        
        for d in dates:
            current_batch.append(d)
            
            # Cada 5 días hábiles (1 semana) o si es el último
            if len(current_batch) >= 5 or d == dates[-1]:
                batches.append(current_batch)
                current_batch = []
        
        # Agregar último batch si quedó algo
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    async def cancel_sync(self):
        """Cancela la sincronización en progreso."""
        if self.is_syncing:
            logger.info("Solicitando cancelación de sincronización...")
            self.cancel_requested = True
            
            sync_state = await self.get_or_create_sync_state()
            sync_state.current_operation = "Cancelando..."
            await self.db.commit()
    
    async def get_sync_status(self) -> Dict:
        """
        Obtiene el estado actual de sincronización.
        
        Returns:
            Diccionario con el estado completo
        """
        sync_state = await self.get_or_create_sync_state()
        
        # Detectar última fecha para información actualizada
        last_detected = await self.detect_last_synced_date()
        
        # Calcular boletines pendientes
        pending_count = 0
        if last_detected:
            missing_dates = self.calculate_missing_dates(last_detected)
            pending_count = len(missing_dates) * len(SECTIONS)
        
        return {
            "status": sync_state.status,
            "last_synced_date": sync_state.last_synced_date.isoformat() if sync_state.last_synced_date else None,
            "last_detected_date": last_detected.isoformat() if last_detected else None,
            "last_sync_timestamp": sync_state.last_sync_timestamp.isoformat() if sync_state.last_sync_timestamp else None,
            "next_scheduled_sync": sync_state.next_scheduled_sync.isoformat() if sync_state.next_scheduled_sync else None,
            "boletines_pending": pending_count,
            "boletines_downloaded": sync_state.boletines_downloaded,
            "boletines_processed": sync_state.boletines_processed,
            "boletines_failed": sync_state.boletines_failed,
            "auto_sync_enabled": sync_state.auto_sync_enabled,
            "sync_frequency": sync_state.sync_frequency,
            "sync_hour": sync_state.sync_hour,
            "current_operation": sync_state.current_operation,
            "error_message": sync_state.error_message,
            "is_syncing": self.is_syncing
        }
    
    async def update_schedule_config(
        self, 
        enabled: bool, 
        frequency: str = "daily", 
        hour: int = 6
    ):
        """
        Actualiza la configuración del scheduler.
        
        Args:
            enabled: Si está habilitado el sync automático
            frequency: Frecuencia (daily, weekly, manual)
            hour: Hora del día (0-23)
        """
        sync_state = await self.get_or_create_sync_state()
        
        sync_state.auto_sync_enabled = enabled
        sync_state.sync_frequency = frequency
        sync_state.sync_hour = hour
        
        # Calcular próxima ejecución
        if enabled and frequency != "manual":
            now = datetime.now()
            next_run = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            # Si la hora ya pasó hoy, programar para mañana
            if next_run <= now:
                next_run += timedelta(days=1)
            
            # Si es weekly, ajustar al próximo lunes
            if frequency == "weekly":
                days_until_monday = (7 - next_run.weekday()) % 7
                if days_until_monday == 0 and next_run <= now:
                    days_until_monday = 7
                next_run += timedelta(days=days_until_monday)
            
            sync_state.next_scheduled_sync = next_run
        else:
            sync_state.next_scheduled_sync = None
        
        await self.db.commit()
        
        logger.info(f"Configuración de scheduler actualizada: enabled={enabled}, frequency={frequency}, hour={hour}")

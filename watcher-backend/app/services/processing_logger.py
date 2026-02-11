"""
Sistema de logging para procesamiento de boletines en tiempo real
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from collections import deque
import threading

logger = logging.getLogger(__name__)

class ProcessingLogger:
    """
    Logger centralizado para el procesamiento de boletines.
    Mantiene un buffer de logs en memoria para consulta en tiempo real.
    """
    
    def __init__(self, max_logs: int = 1000):
        self.max_logs = max_logs
        self.logs: deque = deque(maxlen=max_logs)
        self.lock = threading.Lock()
        self.current_session_id: Optional[str] = None
        
    def start_session(self, session_id: str, operation: str):
        """Inicia una nueva sesión de procesamiento"""
        with self.lock:
            self.current_session_id = session_id
            self.add_log("info", f"🚀 Iniciando {operation}", session_id)
    
    def add_log(self, level: str, message: str, session_id: Optional[str] = None):
        """Agrega un log al buffer"""
        with self.lock:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": level,
                "message": message,
                "session_id": session_id or self.current_session_id
            }
            self.logs.append(log_entry)
            
            # También loguear en el sistema estándar
            log_func = getattr(logger, level, logger.info)
            log_func(f"[{session_id}] {message}")
    
    def info(self, message: str, session_id: Optional[str] = None):
        """Log de nivel INFO"""
        self.add_log("info", message, session_id)
    
    def success(self, message: str, session_id: Optional[str] = None):
        """Log de éxito"""
        self.add_log("success", f"✅ {message}", session_id)
    
    def warning(self, message: str, session_id: Optional[str] = None):
        """Log de advertencia"""
        self.add_log("warning", f"⚠️ {message}", session_id)
    
    def error(self, message: str, session_id: Optional[str] = None):
        """Log de error"""
        self.add_log("error", f"❌ {message}", session_id)
    
    def progress(self, message: str, current: int, total: int, session_id: Optional[str] = None):
        """Log de progreso"""
        percentage = (current / total * 100) if total > 0 else 0
        self.add_log("info", f"📊 {message} ({current}/{total} - {percentage:.1f}%)", session_id)
    
    def get_logs(self, session_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Obtiene los logs más recientes"""
        with self.lock:
            if session_id:
                # Filtrar por sesión
                filtered = [log for log in self.logs if log["session_id"] == session_id]
                return list(filtered)[-limit:]
            else:
                # Todos los logs
                return list(self.logs)[-limit:]
    
    def clear_session(self, session_id: str):
        """Limpia los logs de una sesión específica"""
        with self.lock:
            self.logs = deque(
                [log for log in self.logs if log["session_id"] != session_id],
                maxlen=self.max_logs
            )
    
    def end_session(self, session_id: str, success: bool = True):
        """Finaliza una sesión de procesamiento"""
        with self.lock:
            if success:
                self.success(f"Procesamiento completado exitosamente", session_id)
            else:
                self.error(f"Procesamiento finalizado con errores", session_id)
            
            if self.current_session_id == session_id:
                self.current_session_id = None

# Instancia global del logger
processing_logger = ProcessingLogger()

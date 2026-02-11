"""
API endpoints para logs de procesamiento en tiempo real
"""

from typing import List, Dict, Optional
from fastapi import APIRouter, Query
from app.services.processing_logger import processing_logger

router = APIRouter()

@router.get("/logs")
async def get_processing_logs(
    session_id: Optional[str] = Query(None, description="ID de sesión para filtrar logs"),
    limit: int = Query(100, description="Número máximo de logs a retornar")
) -> List[Dict]:
    """
    Obtiene los logs de procesamiento más recientes.
    
    Args:
        session_id: ID de sesión opcional para filtrar
        limit: Número máximo de logs (default: 100)
    
    Returns:
        Lista de logs con timestamp, level, message y session_id
    """
    logs = processing_logger.get_logs(session_id=session_id, limit=limit)
    return logs

@router.delete("/logs/{session_id}")
async def clear_session_logs(session_id: str) -> Dict:
    """
    Limpia los logs de una sesión específica.
    
    Args:
        session_id: ID de la sesión a limpiar
    
    Returns:
        Mensaje de confirmación
    """
    processing_logger.clear_session(session_id)
    return {"message": f"Logs de sesión {session_id} eliminados"}

@router.get("/logs/sessions")
async def get_active_sessions() -> Dict:
    """
    Obtiene información sobre las sesiones activas.
    
    Returns:
        Información de sesiones
    """
    # Obtener todas las sesiones únicas de los logs
    all_logs = processing_logger.get_logs(limit=1000)
    sessions = {}
    
    for log in all_logs:
        session_id = log.get("session_id")
        if session_id:
            if session_id not in sessions:
                sessions[session_id] = {
                    "session_id": session_id,
                    "first_log": log["timestamp"],
                    "last_log": log["timestamp"],
                    "log_count": 0,
                    "errors": 0,
                    "warnings": 0
                }
            
            sessions[session_id]["last_log"] = log["timestamp"]
            sessions[session_id]["log_count"] += 1
            
            if log["level"] == "error":
                sessions[session_id]["errors"] += 1
            elif log["level"] == "warning":
                sessions[session_id]["warnings"] += 1
    
    return {
        "total_sessions": len(sessions),
        "sessions": list(sessions.values())
    }

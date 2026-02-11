"""
API endpoints para observability y telemetría
"""
from fastapi import APIRouter
from typing import Optional

from app.core.observability import observability
from app.core.events import event_bus

router = APIRouter()


@router.get("/health")
async def get_system_health():
    """
    Obtiene estado de salud del sistema
    """
    return observability.get_system_health()


@router.get("/metrics")
async def get_metrics_summary():
    """
    Obtiene resumen de métricas
    """
    return observability.metrics.get_metrics_summary()


@router.get("/metrics/{metric_name}")
async def get_metric_history(metric_name: str, hours: int = 1):
    """
    Obtiene historial de una métrica específica
    """
    return {
        "metric_name": metric_name,
        "history": observability.metrics.get_metric_history(metric_name, hours)
    }


@router.get("/traces")
async def get_recent_traces(limit: int = 50):
    """
    Obtiene traces recientes
    """
    return {
        "traces": observability.get_recent_traces(limit)
    }


@router.get("/traces/{operation_name}")
async def get_operation_stats(operation_name: str):
    """
    Obtiene estadísticas de una operación específica
    """
    return observability.get_operation_stats(operation_name)


@router.get("/events")
async def get_event_history(event_type: Optional[str] = None, limit: int = 100):
    """
    Obtiene historial de eventos
    """
    return {
        "events": event_bus.get_event_history(event_type, limit)
    }


@router.post("/events/clear")
async def clear_event_history():
    """
    Limpia el historial de eventos
    """
    event_bus.clear_history()
    return {"message": "Event history cleared"}


@router.post("/metrics/cleanup")
async def cleanup_old_metrics():
    """
    Limpia métricas antiguas
    """
    observability.metrics.cleanup_old_metrics()
    return {"message": "Old metrics cleaned up"}


@router.get("/dashboard")
async def get_dashboard_data():
    """
    Obtiene datos consolidados para dashboard de observability
    """
    health = observability.get_system_health()
    events = event_bus.get_event_history(limit=20)
    traces = observability.get_recent_traces(limit=20)
    
    return {
        "health": health,
        "recent_events": events,
        "recent_traces": traces,
        "timestamp": health["timestamp"]
    }


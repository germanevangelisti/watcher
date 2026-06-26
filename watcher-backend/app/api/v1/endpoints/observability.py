"""
API endpoints para observability y telemetría
"""
from fastapi import APIRouter
from typing import Optional, Dict
from pydantic import BaseModel, ConfigDict

from app.core.observability import observability, traced_operation
from app.core.events import event_bus

router = APIRouter()


class VCPMetrics(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    vcp_score_current: float
    vcp_score_by_boletin: Dict[str, float]
    aius_total: int
    aius_verified: int
    aius_unverifiable: int
    aius_contradicted: int
    verification_latency_p50_ms: Optional[float]
    verification_latency_p95_ms: Optional[float]
    requires_attention: bool  # True if contradicted > 0 or vcp_score < 0.85


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

    gauges = observability.metrics.gauges
    counters = observability.metrics.counters

    return {
        "health": health,
        "recent_events": events,
        "recent_traces": traces,
        "timestamp": health["timestamp"],
        "vcp": {
            "current_score": gauges.get("vcp.score", 0.0),
            "aius_total": counters.get("vcp.aius_total", 0),
            "aius_verified": counters.get("vcp.aius_verified", 0),
            "aius_contradicted": counters.get("vcp.aius_contradicted", 0),
        },
    }


@router.get("/vcp", response_model=VCPMetrics)
@traced_operation("vcp_dashboard")
async def get_vcp_dashboard():
    """VCP dashboard: current score, historical breakdown, AIU counts."""
    try:
        gauges = observability.metrics.gauges
        counters = observability.metrics.counters
        latency_values = observability.metrics.histograms.get("verification.latency_ms", [])

        vcp_score_current = float(gauges.get("vcp.score", 0.0))
        aius_total = int(counters.get("vcp.aius_total", 0))
        aius_verified = int(counters.get("vcp.aius_verified", 0))
        aius_unverifiable = int(counters.get("vcp.aius_unverifiable", 0))
        aius_contradicted = int(counters.get("vcp.aius_contradicted", 0))

        # Collect per-boletin scores from gauges
        vcp_score_by_boletin: Dict[str, float] = {
            key.replace("vcp.score.boletin_", ""): float(val)
            for key, val in gauges.items()
            if key.startswith("vcp.score.boletin_")
        }

        # Compute latency percentiles from histogram
        p50: Optional[float] = None
        p95: Optional[float] = None
        if latency_values:
            p50 = observability.metrics._percentile(latency_values, 50)
            p95 = observability.metrics._percentile(latency_values, 95)

        requires_attention = aius_contradicted > 0 or vcp_score_current < 0.85

        return VCPMetrics(
            vcp_score_current=vcp_score_current,
            vcp_score_by_boletin=vcp_score_by_boletin,
            aius_total=aius_total,
            aius_verified=aius_verified,
            aius_unverifiable=aius_unverifiable,
            aius_contradicted=aius_contradicted,
            verification_latency_p50_ms=p50,
            verification_latency_p95_ms=p95,
            requires_attention=requires_attention,
        )
    except Exception:
        return VCPMetrics(
            vcp_score_current=0.0,
            vcp_score_by_boletin={},
            aius_total=0,
            aius_verified=0,
            aius_unverifiable=0,
            aius_contradicted=0,
            verification_latency_p50_ms=None,
            verification_latency_p95_ms=None,
            requires_attention=False,
        )


@router.get("/vcp/{boletin_id}")
@traced_operation("vcp_by_boletin")
async def get_vcp_by_boletin(boletin_id: int):
    """VCP for a specific boletin."""
    try:
        gauge_key = f"vcp.score.boletin_{boletin_id}"
        score = observability.metrics.gauges.get(gauge_key)
        return {
            "boletin_id": boletin_id,
            "vcp_score": float(score) if score is not None else None,
            "recorded": score is not None,
        }
    except Exception:
        return {
            "boletin_id": boletin_id,
            "vcp_score": None,
            "recorded": False,
        }


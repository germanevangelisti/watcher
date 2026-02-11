"""
Sistema de observability y telemetría para agentes
"""
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Recolector de métricas del sistema"""
    
    def __init__(self):
        self.metrics: Dict[str, List[Dict]] = defaultdict(list)
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Configuración
        self.max_history_size = 1000
        self.retention_hours = 24
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict] = None):
        """Incrementa un contador"""
        self.counters[name] += value
        self._record_metric('counter', name, value, tags)
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict] = None):
        """Establece un gauge"""
        self.gauges[name] = value
        self._record_metric('gauge', name, value, tags)
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict] = None):
        """Registra un valor en un histograma"""
        self.histograms[name].append(value)
        
        # Limitar tamaño
        if len(self.histograms[name]) > self.max_history_size:
            self.histograms[name] = self.histograms[name][-self.max_history_size:]
        
        self._record_metric('histogram', name, value, tags)
    
    def _record_metric(self, metric_type: str, name: str, value: Any, tags: Optional[Dict] = None):
        """Registra una métrica con timestamp"""
        metric = {
            'type': metric_type,
            'name': name,
            'value': value,
            'tags': tags or {},
            'timestamp': datetime.utcnow()
        }
        
        self.metrics[name].append(metric)
        
        # Limitar tamaño del historial
        if len(self.metrics[name]) > self.max_history_size:
            self.metrics[name] = self.metrics[name][-self.max_history_size:]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de métricas"""
        return {
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'histograms_stats': {
                name: {
                    'count': len(values),
                    'mean': sum(values) / len(values) if values else 0,
                    'min': min(values) if values else 0,
                    'max': max(values) if values else 0,
                    'p95': self._percentile(values, 95) if values else 0,
                    'p99': self._percentile(values, 99) if values else 0
                }
                for name, values in self.histograms.items()
            }
        }
    
    def get_metric_history(self, name: str, hours: int = 1) -> List[Dict]:
        """Obtiene historial de una métrica"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        if name not in self.metrics:
            return []
        
        return [
            {
                'type': m['type'],
                'value': m['value'],
                'tags': m['tags'],
                'timestamp': m['timestamp'].isoformat()
            }
            for m in self.metrics[name]
            if m['timestamp'] >= cutoff
        ]
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calcula percentil"""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * (percentile / 100))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def cleanup_old_metrics(self):
        """Limpia métricas antiguas"""
        cutoff = datetime.utcnow() - timedelta(hours=self.retention_hours)
        
        for name in list(self.metrics.keys()):
            self.metrics[name] = [
                m for m in self.metrics[name]
                if m['timestamp'] >= cutoff
            ]


class TraceSpan:
    """Span de tracing para operaciones"""
    
    def __init__(self, operation_name: str, parent_span_id: Optional[str] = None):
        self.operation_name = operation_name
        self.span_id = f"{operation_name}_{time.time()}"
        self.parent_span_id = parent_span_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.tags: Dict[str, Any] = {}
        self.logs: List[Dict] = []
        self.status = 'in_progress'
    
    def set_tag(self, key: str, value: Any):
        """Establece un tag"""
        self.tags[key] = value
    
    def log(self, message: str, level: str = 'info'):
        """Agrega un log al span"""
        self.logs.append({
            'timestamp': time.time(),
            'message': message,
            'level': level
        })
    
    def finish(self, status: str = 'completed'):
        """Finaliza el span"""
        self.end_time = time.time()
        self.status = status
    
    def duration_ms(self) -> float:
        """Obtiene duración en milisegundos"""
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario"""
        return {
            'span_id': self.span_id,
            'parent_span_id': self.parent_span_id,
            'operation_name': self.operation_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_ms': self.duration_ms(),
            'status': self.status,
            'tags': self.tags,
            'logs': self.logs
        }


class ObservabilityManager:
    """Gestor central de observability"""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.active_spans: Dict[str, TraceSpan] = {}
        self.completed_spans: List[TraceSpan] = []
        
        # Límite de spans completados
        self.max_completed_spans = 1000
    
    @contextmanager
    def trace_operation(self, operation_name: str, tags: Optional[Dict] = None):
        """Context manager para tracing de operaciones"""
        span = TraceSpan(operation_name)
        
        if tags:
            for key, value in tags.items():
                span.set_tag(key, value)
        
        self.active_spans[span.span_id] = span
        
        try:
            yield span
            span.finish('completed')
            self.metrics.increment_counter(f'operation.{operation_name}.success')
        except Exception as e:
            span.finish('failed')
            span.log(f'Error: {str(e)}', level='error')
            self.metrics.increment_counter(f'operation.{operation_name}.failure')
            raise
        finally:
            # Mover a completed
            if span.span_id in self.active_spans:
                del self.active_spans[span.span_id]
            
            self.completed_spans.append(span)
            
            # Limitar tamaño
            if len(self.completed_spans) > self.max_completed_spans:
                self.completed_spans = self.completed_spans[-self.max_completed_spans:]
            
            # Registrar duración
            self.metrics.record_histogram(
                f'operation.{operation_name}.duration_ms',
                span.duration_ms(),
                tags={'status': span.status}
            )
    
    def get_system_health(self) -> Dict[str, Any]:
        """Obtiene estado de salud del sistema"""
        metrics_summary = self.metrics.get_metrics_summary()
        
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'active_operations': len(self.active_spans),
            'total_operations_completed': len(self.completed_spans),
            'metrics': metrics_summary,
            'recent_failures': self._get_recent_failures()
        }
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Obtiene estadísticas de una operación"""
        # Buscar spans de esta operación
        operation_spans = [
            s for s in self.completed_spans
            if s.operation_name == operation_name
        ]
        
        if not operation_spans:
            return {
                'operation_name': operation_name,
                'count': 0
            }
        
        durations = [s.duration_ms() for s in operation_spans]
        
        return {
            'operation_name': operation_name,
            'count': len(operation_spans),
            'success_count': sum(1 for s in operation_spans if s.status == 'completed'),
            'failure_count': sum(1 for s in operation_spans if s.status == 'failed'),
            'avg_duration_ms': sum(durations) / len(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'p95_duration_ms': self.metrics._percentile(durations, 95),
            'p99_duration_ms': self.metrics._percentile(durations, 99)
        }
    
    def get_recent_traces(self, limit: int = 50) -> List[Dict]:
        """Obtiene traces recientes"""
        recent = self.completed_spans[-limit:] if len(self.completed_spans) > limit else self.completed_spans
        return [s.to_dict() for s in reversed(recent)]
    
    def _get_recent_failures(self, minutes: int = 5) -> List[Dict]:
        """Obtiene fallos recientes"""
        cutoff = time.time() - (minutes * 60)
        
        failures = [
            {
                'operation': s.operation_name,
                'timestamp': s.start_time,
                'duration_ms': s.duration_ms(),
                'error': next((log['message'] for log in s.logs if log['level'] == 'error'), None)
            }
            for s in self.completed_spans
            if s.status == 'failed' and s.start_time >= cutoff
        ]
        
        return failures


# Instancia global
observability = ObservabilityManager()


def traced_operation(operation_name: str):
    """Decorator para operaciones trazadas"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with observability.trace_operation(operation_name) as span:
                span.set_tag('function', func.__name__)
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with observability.trace_operation(operation_name) as span:
                span.set_tag('function', func.__name__)
                return func(*args, **kwargs)
        
        # Retornar wrapper apropiado
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator






"""
Sistema de eventos para comunicación entre agentes
"""
import asyncio
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Tipos de eventos en el sistema"""
    # Workflow events
    WORKFLOW_CREATED = "workflow.created"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    
    # Task events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_WAITING_APPROVAL = "task.waiting_approval"
    TASK_APPROVED = "task.approved"
    TASK_REJECTED = "task.rejected"
    
    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"
    
    # Document events
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_ANALYZED = "document.analyzed"
    DOCUMENT_FAILED = "document.failed"
    
    # Red flag events
    RED_FLAG_DETECTED = "redflag.detected"
    RED_FLAG_VALIDATED = "redflag.validated"
    RED_FLAG_DISMISSED = "redflag.dismissed"
    
    # System events
    SYSTEM_HEALTH_CHECK = "system.health_check"
    SYSTEM_ALERT = "system.alert"


class Event:
    """Evento del sistema"""
    
    def __init__(self, event_type: EventType, data: Dict[str, Any], 
                 source: Optional[str] = None):
        self.event_type = event_type
        self.data = data
        self.source = source or "system"
        self.timestamp = datetime.utcnow()
        self.event_id = f"{event_type}_{self.timestamp.timestamp()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el evento a diccionario"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }


class EventBus:
    """
    Bus de eventos para comunicación asíncrona entre componentes
    
    Patrón Pub/Sub para desacoplar agentes y permitir observabilidad
    """
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000
        
    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """
        Suscribe un callback a un tipo de evento
        
        Args:
            event_type: Tipo de evento a escuchar
            callback: Función callback (puede ser sync o async)
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(callback)
        logger.debug(f"Callback suscrito a {event_type}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        """
        Desuscribe un callback de un tipo de evento
        
        Args:
            event_type: Tipo de evento
            callback: Función callback a remover
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Callback desuscrito de {event_type}")
            except ValueError:
                pass
    
    async def emit(self, event_type: EventType, data: Dict[str, Any],
                   source: Optional[str] = None) -> None:
        """
        Emite un evento a todos los suscriptores
        
        Args:
            event_type: Tipo de evento
            data: Datos del evento
            source: Fuente que emite el evento
        """
        event = Event(event_type, data, source)
        
        # Guardar en historial
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        logger.info(f"Evento emitido: {event_type} from {source}")
        
        # Notificar suscriptores
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error en callback de {event_type}: {e}", 
                               exc_info=True)
    
    def get_event_history(self, event_type: Optional[EventType] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de eventos
        
        Args:
            event_type: Filtrar por tipo de evento (opcional)
            limit: Límite de eventos a retornar
        
        Returns:
            Lista de eventos como diccionarios
        """
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        # Retornar los más recientes
        recent = events[-limit:] if len(events) > limit else events
        return [e.to_dict() for e in recent]
    
    def clear_history(self) -> None:
        """Limpia el historial de eventos"""
        self._event_history.clear()
        logger.info("Historial de eventos limpiado")


# Instancia global del event bus
event_bus = EventBus()






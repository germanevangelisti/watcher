"""
Estado compartido para workflows de agentes
"""
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class AgentType(str, Enum):
    """Tipos de agentes en el sistema"""
    ORCHESTRATOR = "orchestrator"
    DOCUMENT_INTELLIGENCE = "document_intelligence"
    ANOMALY_DETECTION = "anomaly_detection"
    INSIGHT_REPORTING = "insight_reporting"
    LEARNING_FEEDBACK = "learning_feedback"
    HISTORICAL_INTELLIGENCE = "historical_intelligence"


class TaskStatus(str, Enum):
    """Estados de una tarea"""
    PENDING = "pending"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentMessage(BaseModel):
    """Mensaje entre agentes"""
    from_agent: AgentType
    to_agent: AgentType
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    requires_approval: bool = False


class TaskDefinition(BaseModel):
    """Definición de una tarea en el workflow"""
    task_id: str
    task_type: str
    agent: AgentType
    parameters: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    requires_approval: bool = False
    approval_status: Optional[str] = None


class WorkflowState(BaseModel):
    """Estado del workflow completo"""
    workflow_id: str
    workflow_name: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Configuración
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # Tareas del workflow
    tasks: List[TaskDefinition] = Field(default_factory=list)
    
    # Mensajes entre agentes
    messages: List[AgentMessage] = Field(default_factory=list)
    
    # Estado compartido entre agentes
    shared_state: Dict[str, Any] = Field(default_factory=dict)
    
    # Métricas
    metrics: Dict[str, Any] = Field(default_factory=dict)
    
    # Logs para observabilidad
    logs: List[str] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def add_log(self, message: str) -> None:
        """Agrega un log con timestamp"""
        timestamp = datetime.utcnow().isoformat()
        self.logs.append(f"[{timestamp}] {message}")
    
    def get_task(self, task_id: str) -> Optional[TaskDefinition]:
        """Obtiene una tarea por ID"""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          result: Optional[Dict[str, Any]] = None,
                          error: Optional[str] = None) -> None:
        """Actualiza el estado de una tarea"""
        task = self.get_task(task_id)
        if task:
            task.status = status
            if result:
                task.result = result
            if error:
                task.error = error
            if status == TaskStatus.IN_PROGRESS:
                task.started_at = datetime.utcnow()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.utcnow()
    
    def get_pending_tasks(self) -> List[TaskDefinition]:
        """Obtiene tareas pendientes ordenadas por prioridad"""
        pending = [t for t in self.tasks if t.status == TaskStatus.PENDING]
        return sorted(pending, key=lambda x: x.priority, reverse=True)
    
    def get_tasks_awaiting_approval(self) -> List[TaskDefinition]:
        """Obtiene tareas esperando aprobación"""
        return [t for t in self.tasks if t.status == TaskStatus.WAITING_APPROVAL]
    
    def is_completed(self) -> bool:
        """Verifica si el workflow está completo"""
        if not self.tasks:
            return False
        return all(t.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED] for t in self.tasks)
    
    def has_failed_tasks(self) -> bool:
        """Verifica si hay tareas fallidas"""
        return any(t.status == TaskStatus.FAILED for t in self.tasks)
    
    def progress_percentage(self) -> float:
        """Calcula el porcentaje de progreso"""
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        return (completed / len(self.tasks)) * 100






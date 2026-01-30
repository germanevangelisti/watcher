"""
API endpoints para workflows supervisados
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agents.orchestrator.state import TaskStatus, AgentType
from .agents import orchestrator
from app.core.events import event_bus, EventType

router = APIRouter()


# Schemas
class TaskDefinitionRequest(BaseModel):
    task_type: str
    agent: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    requires_approval: bool = False


class CreateWorkflowRequest(BaseModel):
    workflow_name: str
    tasks: List[TaskDefinitionRequest]
    config: Optional[Dict[str, Any]] = None


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    workflow_name: str
    status: str
    progress_percentage: float
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    pending_tasks: int
    awaiting_approval: int
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]


class ApproveTaskRequest(BaseModel):
    modifications: Optional[Dict[str, Any]] = None


class RejectTaskRequest(BaseModel):
    reason: Optional[str] = None


# Endpoints
@router.post("", response_model=Dict[str, Any])
async def create_workflow(request: CreateWorkflowRequest):
    """
    Crea un nuevo workflow
    """
    try:
        # Convertir tasks a formato interno
        tasks = []
        for task_req in request.tasks:
            tasks.append({
                "task_type": task_req.task_type,
                "agent": task_req.agent,
                "parameters": task_req.parameters,
                "priority": task_req.priority,
                "requires_approval": task_req.requires_approval
            })
        
        # Crear workflow
        workflow = await orchestrator.create_workflow(
            workflow_name=request.workflow_name,
            tasks=tasks,
            config=request.config
        )
        
        # Emitir evento
        await event_bus.emit(
            EventType.WORKFLOW_CREATED,
            {"workflow_id": workflow.workflow_id, "workflow_name": workflow.workflow_name},
            source="api"
        )
        
        return {
            "workflow_id": workflow.workflow_id,
            "workflow_name": workflow.workflow_name,
            "status": workflow.status,
            "total_tasks": len(workflow.tasks)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, background_tasks: BackgroundTasks):
    """
    Ejecuta un workflow
    """
    workflow = orchestrator.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    
    # Ejecutar en background
    background_tasks.add_task(orchestrator.execute_workflow, workflow_id)
    
    # Emitir evento
    await event_bus.emit(
        EventType.WORKFLOW_STARTED,
        {"workflow_id": workflow_id},
        source="api"
    )
    
    return {
        "message": "Workflow iniciado",
        "workflow_id": workflow_id
    }


@router.get("/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str):
    """
    Obtiene el estado de un workflow
    """
    status = orchestrator.get_workflow_status(workflow_id)
    if not status:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    
    return WorkflowStatusResponse(
        workflow_id=status["workflow_id"],
        workflow_name=status["workflow_name"],
        status=status["status"],
        progress_percentage=status["progress_percentage"],
        total_tasks=status["total_tasks"],
        completed_tasks=status["completed_tasks"],
        failed_tasks=status["failed_tasks"],
        pending_tasks=status["pending_tasks"],
        awaiting_approval=status["awaiting_approval"],
        created_at=status["created_at"].isoformat(),
        started_at=status["started_at"].isoformat() if status["started_at"] else None,
        completed_at=status["completed_at"].isoformat() if status["completed_at"] else None
    )


@router.get("/{workflow_id}/details")
async def get_workflow_details(workflow_id: str):
    """
    Obtiene los detalles completos de un workflow
    """
    workflow = orchestrator.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    
    return workflow.model_dump()


@router.get("", response_model=List[WorkflowStatusResponse])
async def list_workflows(status_filter: Optional[str] = None):
    """
    Lista todos los workflows
    """
    status_enum = None
    if status_filter:
        try:
            status_enum = TaskStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail="Estado inválido")
    
    workflows = orchestrator.list_workflows(status_filter=status_enum)
    
    return [
        WorkflowStatusResponse(
            workflow_id=wf["workflow_id"],
            workflow_name=wf["workflow_name"],
            status=wf["status"],
            progress_percentage=wf["progress_percentage"],
            total_tasks=wf["total_tasks"],
            completed_tasks=wf["completed_tasks"],
            failed_tasks=wf["failed_tasks"],
            pending_tasks=wf["pending_tasks"],
            awaiting_approval=wf["awaiting_approval"],
            created_at=wf["created_at"].isoformat(),
            started_at=wf["started_at"].isoformat() if wf["started_at"] else None,
            completed_at=wf["completed_at"].isoformat() if wf["completed_at"] else None
        )
        for wf in workflows
    ]


@router.post("/{workflow_id}/tasks/{task_id}/approve")
async def approve_task(workflow_id: str, task_id: str, request: ApproveTaskRequest):
    """
    Aprueba una tarea que está esperando aprobación
    """
    success = await orchestrator.approve_task(
        workflow_id,
        task_id,
        modifications=request.modifications
    )
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Workflow o tarea no encontrada, o tarea no está esperando aprobación"
        )
    
    # Emitir evento
    await event_bus.emit(
        EventType.TASK_APPROVED,
        {"workflow_id": workflow_id, "task_id": task_id},
        source="api"
    )
    
    return {"message": "Tarea aprobada", "task_id": task_id}


@router.post("/{workflow_id}/tasks/{task_id}/reject")
async def reject_task(workflow_id: str, task_id: str, request: RejectTaskRequest):
    """
    Rechaza una tarea que está esperando aprobación
    """
    success = await orchestrator.reject_task(
        workflow_id,
        task_id,
        reason=request.reason
    )
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Workflow o tarea no encontrada"
        )
    
    # Emitir evento
    await event_bus.emit(
        EventType.TASK_REJECTED,
        {"workflow_id": workflow_id, "task_id": task_id, "reason": request.reason},
        source="api"
    )
    
    return {"message": "Tarea rechazada", "task_id": task_id}


@router.get("/{workflow_id}/tasks")
async def get_workflow_tasks(workflow_id: str):
    """
    Obtiene las tareas de un workflow
    """
    workflow = orchestrator.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    
    return {
        "workflow_id": workflow_id,
        "tasks": [task.model_dump() for task in workflow.tasks]
    }


@router.get("/{workflow_id}/logs")
async def get_workflow_logs(workflow_id: str):
    """
    Obtiene los logs de un workflow
    """
    workflow = orchestrator.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    
    return {
        "workflow_id": workflow_id,
        "logs": workflow.logs
    }


@router.get("/{workflow_id}/tasks/awaiting-approval")
async def get_tasks_awaiting_approval(workflow_id: str):
    """
    Obtiene las tareas que están esperando aprobación
    """
    workflow = orchestrator.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    
    awaiting_tasks = workflow.get_tasks_awaiting_approval()
    
    return {
        "workflow_id": workflow_id,
        "awaiting_approval_count": len(awaiting_tasks),
        "tasks": [task.model_dump() for task in awaiting_tasks]
    }


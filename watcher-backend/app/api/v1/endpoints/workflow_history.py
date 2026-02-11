"""
API endpoints para historial de workflows
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import csv
import io

from app.db.sync_session import get_sync_db
from app.db.workflow_crud import workflow_crud, task_crud, log_crud
from pydantic import BaseModel


router = APIRouter()


# Schemas
class WorkflowHistoryResponse(BaseModel):
    id: str
    workflow_name: str
    workflow_type: str
    status: str
    parameters: Optional[dict]
    results: Optional[dict]
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    progress_percentage: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class WorkflowDetailResponse(BaseModel):
    id: str
    workflow_name: str
    workflow_type: str
    status: str
    parameters: Optional[dict]
    config: Optional[dict]
    results: Optional[dict]
    error_message: Optional[str]
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    progress_percentage: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    updated_at: datetime
    tasks: List[dict]
    logs: List[dict]
    
    class Config:
        from_attributes = True


class WorkflowStatsResponse(BaseModel):
    total_workflows: int
    active_workflows: int
    completed_workflows: int
    failed_workflows: int
    total_tasks: int
    average_completion_time: Optional[float]


# Endpoints
@router.get("/history", response_model=List[WorkflowHistoryResponse])
def get_workflow_history(
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    workflow_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db)
):
    """Obtiene el historial de workflows"""
    workflows = workflow_crud.list_workflows(
        db=db,
        status=status,
        workflow_type=workflow_type,
        limit=limit,
        offset=offset
    )
    return workflows


@router.get("/history/{workflow_id}", response_model=WorkflowDetailResponse)
def get_workflow_detail(
    workflow_id: str,
    db: Session = Depends(get_sync_db)
):
    """Obtiene el detalle completo de un workflow"""
    workflow = workflow_crud.get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    
    # Obtener tareas
    tasks = task_crud.get_workflow_tasks(db, workflow_id)
    task_list = [
        {
            "id": t.id,
            "task_type": t.task_type,
            "agent_type": t.agent_type,
            "status": t.status,
            "parameters": t.parameters,
            "result": t.result,
            "error_message": t.error_message,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None
        }
        for t in tasks
    ]
    
    # Obtener logs
    logs = log_crud.get_workflow_logs(db, workflow_id)
    log_list = [
        {
            "id": l.id,
            "level": l.level,
            "message": l.message,
            "source": l.source,
            "created_at": l.created_at.isoformat()
        }
        for l in logs
    ]
    
    # Construir respuesta
    return WorkflowDetailResponse(
        id=workflow.id,
        workflow_name=workflow.workflow_name,
        workflow_type=workflow.workflow_type,
        status=workflow.status,
        parameters=workflow.parameters,
        config=workflow.config,
        results=workflow.results,
        error_message=workflow.error_message,
        total_tasks=workflow.total_tasks,
        completed_tasks=workflow.completed_tasks,
        failed_tasks=workflow.failed_tasks,
        progress_percentage=workflow.progress_percentage,
        created_at=workflow.created_at,
        started_at=workflow.started_at,
        completed_at=workflow.completed_at,
        updated_at=workflow.updated_at,
        tasks=task_list,
        logs=log_list
    )


@router.get("/stats", response_model=WorkflowStatsResponse)
def get_workflow_stats(
    days: int = Query(30, ge=1, le=365, description="Días hacia atrás"),
    db: Session = Depends(get_sync_db)
):
    """Obtiene estadísticas de workflows"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    from sqlalchemy import func
    from app.db.models import AgentWorkflow, AgentTask
    
    # Total workflows
    total = db.query(func.count(AgentWorkflow.id)).filter(
        AgentWorkflow.created_at >= cutoff_date
    ).scalar()
    
    # Por estado
    active = db.query(func.count(AgentWorkflow.id)).filter(
        AgentWorkflow.created_at >= cutoff_date,
        AgentWorkflow.status.in_(['pending', 'in_progress', 'waiting_approval'])
    ).scalar()
    
    completed = db.query(func.count(AgentWorkflow.id)).filter(
        AgentWorkflow.created_at >= cutoff_date,
        AgentWorkflow.status == 'completed'
    ).scalar()
    
    failed = db.query(func.count(AgentWorkflow.id)).filter(
        AgentWorkflow.created_at >= cutoff_date,
        AgentWorkflow.status == 'failed'
    ).scalar()
    
    # Total tareas
    total_tasks = db.query(func.count(AgentTask.id)).filter(
        AgentTask.created_at >= cutoff_date
    ).scalar()
    
    # Tiempo promedio de completitud
    completed_workflows = db.query(
        AgentWorkflow.created_at,
        AgentWorkflow.completed_at
    ).filter(
        AgentWorkflow.created_at >= cutoff_date,
        AgentWorkflow.status == 'completed',
        AgentWorkflow.completed_at.isnot(None)
    ).all()
    
    avg_time = None
    if completed_workflows:
        times = [
            (w.completed_at - w.created_at).total_seconds()
            for w in completed_workflows
        ]
        avg_time = sum(times) / len(times) if times else None
    
    return WorkflowStatsResponse(
        total_workflows=total or 0,
        active_workflows=active or 0,
        completed_workflows=completed or 0,
        failed_workflows=failed or 0,
        total_tasks=total_tasks or 0,
        average_completion_time=avg_time
    )


@router.get("/export/{workflow_id}")
def export_workflow_results(
    workflow_id: str,
    format: str = Query("json", regex="^(json|csv)$"),
    db: Session = Depends(get_sync_db)
):
    """Exporta los resultados de un workflow"""
    workflow = workflow_crud.get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    
    if format == "csv":
        # Exportar como CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            "Workflow ID", "Workflow Name", "Type", "Status",
            "Total Tasks", "Completed", "Failed",
            "Created At", "Completed At"
        ])
        
        # Data
        writer.writerow([
            workflow.id,
            workflow.workflow_name,
            workflow.workflow_type,
            workflow.status,
            workflow.total_tasks,
            workflow.completed_tasks,
            workflow.failed_tasks,
            workflow.created_at.isoformat() if workflow.created_at else "",
            workflow.completed_at.isoformat() if workflow.completed_at else ""
        ])
        
        # Tasks
        writer.writerow([])
        writer.writerow(["Task ID", "Type", "Agent", "Status", "Created At"])
        
        tasks = task_crud.get_workflow_tasks(db, workflow_id)
        for task in tasks:
            writer.writerow([
                task.id,
                task.task_type,
                task.agent_type,
                task.status,
                task.created_at.isoformat() if task.created_at else ""
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=workflow_{workflow_id}.csv"
            }
        )
    
    else:  # JSON
        tasks = task_crud.get_workflow_tasks(db, workflow_id)
        logs = log_crud.get_workflow_logs(db, workflow_id)
        
        return {
            "workflow": {
                "id": workflow.id,
                "name": workflow.workflow_name,
                "type": workflow.workflow_type,
                "status": workflow.status,
                "parameters": workflow.parameters,
                "results": workflow.results,
                "created_at": workflow.created_at.isoformat(),
                "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None
            },
            "tasks": [
                {
                    "id": t.id,
                    "type": t.task_type,
                    "status": t.status,
                    "result": t.result
                }
                for t in tasks
            ],
            "logs": [
                {
                    "level": l.level,
                    "message": l.message,
                    "created_at": l.created_at.isoformat()
                }
                for l in logs
            ]
        }


@router.delete("/history/{workflow_id}")
def delete_workflow(
    workflow_id: str,
    db: Session = Depends(get_sync_db)
):
    """Elimina un workflow del historial"""
    success = workflow_crud.delete_workflow(db, workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    
    return {"message": "Workflow eliminado exitosamente"}




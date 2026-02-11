"""
CRUD operations para Agent Workflows
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from datetime import datetime, timedelta

from .models import AgentWorkflow, AgentTask, WorkflowLog


class WorkflowCRUD:
    """Operaciones CRUD para workflows"""
    
    @staticmethod
    def create_workflow(
        db: Session,
        workflow_id: str,
        workflow_name: str,
        workflow_type: str,
        parameters: Optional[Dict] = None,
        config: Optional[Dict] = None,
        created_by: Optional[str] = None
    ) -> AgentWorkflow:
        """Crea un nuevo workflow en la base de datos"""
        workflow = AgentWorkflow(
            id=workflow_id,
            workflow_name=workflow_name,
            workflow_type=workflow_type,
            status="pending",
            parameters=parameters,
            config=config,
            created_by=created_by,
            total_tasks=0,
            completed_tasks=0,
            failed_tasks=0,
            progress_percentage=0.0
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        return workflow
    
    @staticmethod
    def get_workflow(db: Session, workflow_id: str) -> Optional[AgentWorkflow]:
        """Obtiene un workflow por ID"""
        return db.query(AgentWorkflow).filter(AgentWorkflow.id == workflow_id).first()
    
    @staticmethod
    def list_workflows(
        db: Session,
        status: Optional[str] = None,
        workflow_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AgentWorkflow]:
        """Lista workflows con filtros opcionales"""
        query = db.query(AgentWorkflow)
        
        if status:
            query = query.filter(AgentWorkflow.status == status)
        if workflow_type:
            query = query.filter(AgentWorkflow.workflow_type == workflow_type)
        
        return query.order_by(desc(AgentWorkflow.created_at)).limit(limit).offset(offset).all()
    
    @staticmethod
    def update_workflow(
        db: Session,
        workflow_id: str,
        **updates
    ) -> Optional[AgentWorkflow]:
        """Actualiza un workflow"""
        workflow = db.query(AgentWorkflow).filter(AgentWorkflow.id == workflow_id).first()
        if not workflow:
            return None
        
        for key, value in updates.items():
            if hasattr(workflow, key):
                setattr(workflow, key, value)
        
        workflow.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(workflow)
        return workflow
    
    @staticmethod
    def delete_workflow(db: Session, workflow_id: str) -> bool:
        """Elimina un workflow y sus tareas/logs asociados"""
        workflow = db.query(AgentWorkflow).filter(AgentWorkflow.id == workflow_id).first()
        if not workflow:
            return False
        
        db.delete(workflow)
        db.commit()
        return True
    
    @staticmethod
    def count_workflows(
        db: Session,
        status: Optional[str] = None,
        workflow_type: Optional[str] = None
    ) -> int:
        """Cuenta workflows con filtros opcionales"""
        query = db.query(AgentWorkflow)
        
        if status:
            query = query.filter(AgentWorkflow.status == status)
        if workflow_type:
            query = query.filter(AgentWorkflow.workflow_type == workflow_type)
        
        return query.count()


class TaskCRUD:
    """Operaciones CRUD para tareas"""
    
    @staticmethod
    def create_task(
        db: Session,
        task_id: str,
        workflow_id: str,
        task_type: str,
        agent_type: str,
        parameters: Optional[Dict] = None,
        priority: int = 0,
        requires_approval: bool = False
    ) -> AgentTask:
        """Crea una nueva tarea"""
        task = AgentTask(
            id=task_id,
            workflow_id=workflow_id,
            task_type=task_type,
            agent_type=agent_type,
            parameters=parameters,
            priority=priority,
            requires_approval=requires_approval,
            status="pending"
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    
    @staticmethod
    def get_task(db: Session, task_id: str) -> Optional[AgentTask]:
        """Obtiene una tarea por ID"""
        return db.query(AgentTask).filter(AgentTask.id == task_id).first()
    
    @staticmethod
    def get_workflow_tasks(db: Session, workflow_id: str) -> List[AgentTask]:
        """Obtiene todas las tareas de un workflow"""
        return db.query(AgentTask).filter(AgentTask.workflow_id == workflow_id).all()
    
    @staticmethod
    def update_task(
        db: Session,
        task_id: str,
        **updates
    ) -> Optional[AgentTask]:
        """Actualiza una tarea"""
        task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
        if not task:
            return None
        
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        db.commit()
        db.refresh(task)
        return task


class LogCRUD:
    """Operaciones CRUD para logs"""
    
    @staticmethod
    def create_log(
        db: Session,
        workflow_id: str,
        level: str,
        message: str,
        source: Optional[str] = None,
        extra_data: Optional[Dict] = None
    ) -> WorkflowLog:
        """Crea un nuevo log"""
        log = WorkflowLog(
            workflow_id=workflow_id,
            level=level,
            message=message,
            source=source,
            extra_data=extra_data
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    
    @staticmethod
    def get_workflow_logs(
        db: Session,
        workflow_id: str,
        level: Optional[str] = None,
        limit: int = 100
    ) -> List[WorkflowLog]:
        """Obtiene logs de un workflow"""
        query = db.query(WorkflowLog).filter(WorkflowLog.workflow_id == workflow_id)
        
        if level:
            query = query.filter(WorkflowLog.level == level)
        
        return query.order_by(desc(WorkflowLog.created_at)).limit(limit).all()
    
    @staticmethod
    def delete_old_logs(db: Session, days: int = 30) -> int:
        """Elimina logs antiguos"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = db.query(WorkflowLog).filter(
            WorkflowLog.created_at < cutoff_date
        ).delete()
        db.commit()
        return deleted


# Instancias singleton
workflow_crud = WorkflowCRUD()
task_crud = TaskCRUD()
log_crud = LogCRUD()


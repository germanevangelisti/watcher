"""
CRUD operations para Agent Workflows
"""
from datetime import datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from .models import AgentTask, AgentWorkflow, WorkflowLog


class WorkflowCRUD:
    """Operaciones CRUD para workflows"""

    @staticmethod
    def create_workflow(
        db: Session,
        workflow_id: str,
        workflow_name: str,
        workflow_type: str,
        parameters: dict | None = None,
        config: dict | None = None,
        created_by: str | None = None
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
    def get_workflow(db: Session, workflow_id: str) -> AgentWorkflow | None:
        """Obtiene un workflow por ID"""
        return db.query(AgentWorkflow).filter(AgentWorkflow.id == workflow_id).first()

    @staticmethod
    def list_workflows(
        db: Session,
        status: str | None = None,
        workflow_type: str | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[AgentWorkflow]:
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
    ) -> AgentWorkflow | None:
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
        status: str | None = None,
        workflow_type: str | None = None
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
        parameters: dict | None = None,
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
    def get_task(db: Session, task_id: str) -> AgentTask | None:
        """Obtiene una tarea por ID"""
        return db.query(AgentTask).filter(AgentTask.id == task_id).first()

    @staticmethod
    def get_workflow_tasks(db: Session, workflow_id: str) -> list[AgentTask]:
        """Obtiene todas las tareas de un workflow"""
        return db.query(AgentTask).filter(AgentTask.workflow_id == workflow_id).all()

    @staticmethod
    def update_task(
        db: Session,
        task_id: str,
        **updates
    ) -> AgentTask | None:
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
        source: str | None = None,
        extra_data: dict | None = None
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
        level: str | None = None,
        limit: int = 100
    ) -> list[WorkflowLog]:
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


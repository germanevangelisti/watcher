"""
Agent Orchestrator - Coordinador central del sistema
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from uuid import uuid4

from .state import (
    WorkflowState, 
    TaskDefinition, 
    TaskStatus, 
    AgentType,
    AgentMessage
)
from app.db.workflow_crud import workflow_crud, task_crud, log_crud
from app.db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Coordinador central que gestiona el flujo de trabajo entre agentes
    
    Responsabilidades:
    - Gestionar cola de tareas y prioridades
    - Decidir qué agente debe actuar en cada momento
    - Mantener contexto compartido entre agentes
    - Solicitar aprobación humana en puntos críticos
    - Monitorear salud y performance de agentes
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el orquestador
        
        Args:
            config: Configuración del orquestador
        """
        self.config = config or {}
        self.active_workflows: Dict[str, WorkflowState] = {}
        self.agent_handlers: Dict[AgentType, Callable] = {}
        self.approval_callback: Optional[Callable] = None
        self.persist_enabled = config.get('persist_enabled', True) if config else True
        
        logger.info("AgentOrchestrator inicializado (persistencia: %s)", self.persist_enabled)
    
    def register_agent_handler(self, agent_type: AgentType, 
                               handler: Callable) -> None:
        """
        Registra un handler para un tipo de agente
        
        Args:
            agent_type: Tipo de agente
            handler: Función handler asíncrona
        """
        self.agent_handlers[agent_type] = handler
        logger.info(f"Handler registrado para agente: {agent_type}")
    
    def set_approval_callback(self, callback: Callable) -> None:
        """
        Configura callback para solicitar aprobaciones humanas
        
        Args:
            callback: Función callback asíncrona que devuelve (approved, modifications)
        """
        self.approval_callback = callback
    
    async def create_workflow(self, 
                             workflow_name: str,
                             tasks: List[Dict[str, Any]],
                             config: Optional[Dict[str, Any]] = None) -> WorkflowState:
        """
        Crea un nuevo workflow
        
        Args:
            workflow_name: Nombre descriptivo del workflow
            tasks: Lista de definiciones de tareas
            config: Configuración específica del workflow
        
        Returns:
            WorkflowState inicializado
        """
        workflow_id = str(uuid4())
        
        # Crear tareas
        task_definitions = []
        for idx, task_data in enumerate(tasks):
            task = TaskDefinition(
                task_id=f"{workflow_id}_{idx}",
                task_type=task_data.get("task_type", "unknown"),
                agent=AgentType(task_data.get("agent", AgentType.ORCHESTRATOR)),
                parameters=task_data.get("parameters", {}),
                priority=task_data.get("priority", 0),
                requires_approval=task_data.get("requires_approval", False)
            )
            task_definitions.append(task)
        
        # Crear workflow
        workflow = WorkflowState(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            config=config or {},
            tasks=task_definitions
        )
        
        workflow.add_log(f"Workflow creado: {workflow_name}")
        self.active_workflows[workflow_id] = workflow
        
        # Persistir en base de datos
        if self.persist_enabled:
            await self._persist_workflow(workflow, task_definitions)
        
        logger.info(f"Workflow creado: {workflow_id} - {workflow_name}")
        return workflow
    
    async def execute_workflow(self, workflow_id: str) -> WorkflowState:
        """
        Ejecuta un workflow completo
        
        Args:
            workflow_id: ID del workflow a ejecutar
        
        Returns:
            WorkflowState actualizado
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow no encontrado: {workflow_id}")
        
        workflow.status = TaskStatus.IN_PROGRESS
        workflow.started_at = datetime.utcnow()
        workflow.add_log("Iniciando ejecución del workflow")
        
        # Actualizar estado en DB
        await self._update_workflow_status(workflow)
        await self._persist_log(workflow.workflow_id, "Iniciando ejecución del workflow")
        
        try:
            # Ejecutar tareas en orden de prioridad
            while not workflow.is_completed():
                pending_tasks = workflow.get_pending_tasks()
                
                if not pending_tasks:
                    # Verificar si hay tareas esperando aprobación
                    awaiting = workflow.get_tasks_awaiting_approval()
                    if awaiting:
                        workflow.add_log(f"{len(awaiting)} tareas esperando aprobación")
                        break
                    else:
                        # No hay tareas pendientes ni esperando aprobación
                        break
                
                # Ejecutar siguiente tarea
                task = pending_tasks[0]
                await self._execute_task(workflow, task)
                
                # Pequeña pausa para evitar sobrecarga
                await asyncio.sleep(0.1)
            
            # Verificar estado final
            if workflow.is_completed():
                workflow.status = TaskStatus.COMPLETED
                workflow.completed_at = datetime.utcnow()
                workflow.add_log("Workflow completado exitosamente")
                
                # Persistir resultado final
                await self._persist_workflow_result(workflow)
                await self._persist_log(workflow.workflow_id, "Workflow completado exitosamente")
                
            elif workflow.has_failed_tasks():
                workflow.status = TaskStatus.FAILED
                workflow.add_log("Workflow falló - hay tareas con errores")
                
                # Persistir estado de fallo
                await self._persist_log(workflow.workflow_id, "Workflow falló - hay tareas con errores", level="error")
                
            else:
                workflow.status = TaskStatus.WAITING_APPROVAL
                workflow.add_log("Workflow esperando aprobación")
                
                # Persistir estado de espera
                await self._persist_log(workflow.workflow_id, "Workflow esperando aprobación", level="warning")
            
            # Actualizar estado final en DB
            await self._update_workflow_status(workflow)
            
        except Exception as e:
            workflow.status = TaskStatus.FAILED
            workflow.add_log(f"Error en ejecución: {str(e)}")
            logger.error(f"Error ejecutando workflow {workflow_id}: {e}", exc_info=True)
            
            # Persistir error crítico
            await self._update_workflow_status(workflow)
            await self._persist_log(workflow.workflow_id, f"Error en ejecución: {str(e)}", level="error")
        
        return workflow
    
    async def _execute_task(self, workflow: WorkflowState, 
                           task: TaskDefinition) -> None:
        """
        Ejecuta una tarea individual
        
        Args:
            workflow: Estado del workflow
            task: Tarea a ejecutar
        """
        task_log = f"Ejecutando tarea: {task.task_type} (agente: {task.agent})"
        workflow.add_log(task_log)
        logger.info(task_log)
        
        try:
            # Verificar si requiere aprobación previa
            if task.requires_approval and task.status == TaskStatus.PENDING:
                workflow.update_task_status(task.task_id, TaskStatus.WAITING_APPROVAL)
                
                if self.approval_callback:
                    # Solicitar aprobación
                    approved, modifications = await self.approval_callback(workflow, task)
                    
                    if not approved:
                        workflow.update_task_status(task.task_id, TaskStatus.CANCELLED)
                        workflow.add_log(f"Tarea {task.task_id} rechazada por usuario")
                        return
                    
                    # Aplicar modificaciones si las hay
                    if modifications:
                        task.parameters.update(modifications)
                        workflow.add_log(f"Parámetros modificados por usuario")
                
                # Cambiar a aprobado
                task.status = TaskStatus.APPROVED
            
            # Ejecutar tarea
            workflow.update_task_status(task.task_id, TaskStatus.IN_PROGRESS)
            
            # Obtener handler del agente
            handler = self.agent_handlers.get(task.agent)
            if not handler:
                raise ValueError(f"No hay handler registrado para agente: {task.agent}")
            
            # Ejecutar handler
            result = await handler(workflow, task)
            
            # Guardar resultado
            workflow.update_task_status(
                task.task_id, 
                TaskStatus.COMPLETED,
                result=result
            )
            workflow.add_log(f"Tarea {task.task_id} completada")
            
            # Persistir resultado
            await self._persist_task_result(workflow.workflow_id, task.task_id, result, "completed")
            await self._persist_log(workflow.workflow_id, f"Tarea {task.task_id} completada")
            
        except Exception as e:
            error_msg = f"Error en tarea {task.task_id}: {str(e)}"
            workflow.update_task_status(
                task.task_id,
                TaskStatus.FAILED,
                error=error_msg
            )
            workflow.add_log(error_msg)
            logger.error(error_msg, exc_info=True)
            
            # Persistir error
            await self._persist_task_result(workflow.workflow_id, task.task_id, {"error": error_msg}, "failed")
            await self._persist_log(workflow.workflow_id, error_msg, level="error")
    
    async def approve_task(self, workflow_id: str, task_id: str,
                          modifications: Optional[Dict[str, Any]] = None) -> bool:
        """
        Aprueba una tarea manualmente
        
        Args:
            workflow_id: ID del workflow
            task_id: ID de la tarea
            modifications: Modificaciones a aplicar a los parámetros
        
        Returns:
            True si la aprobación fue exitosa
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return False
        
        task = workflow.get_task(task_id)
        if not task or task.status != TaskStatus.WAITING_APPROVAL:
            return False
        
        # Aplicar modificaciones
        if modifications:
            task.parameters.update(modifications)
        
        # Cambiar estado
        task.status = TaskStatus.APPROVED
        workflow.add_log(f"Tarea {task_id} aprobada manualmente")
        
        return True
    
    async def reject_task(self, workflow_id: str, task_id: str, 
                         reason: Optional[str] = None) -> bool:
        """
        Rechaza una tarea manualmente
        
        Args:
            workflow_id: ID del workflow
            task_id: ID de la tarea
            reason: Razón del rechazo
        
        Returns:
            True si el rechazo fue exitoso
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return False
        
        task = workflow.get_task(task_id)
        if not task:
            return False
        
        # Cambiar estado
        workflow.update_task_status(task_id, TaskStatus.REJECTED)
        if reason:
            workflow.add_log(f"Tarea {task_id} rechazada: {reason}")
        else:
            workflow.add_log(f"Tarea {task_id} rechazada por usuario")
        
        return True
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowState]:
        """Obtiene un workflow por ID"""
        return self.active_workflows.get(workflow_id)
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado resumido de un workflow
        
        Returns:
            Diccionario con estado resumido
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return None
        
        return {
            "workflow_id": workflow.workflow_id,
            "workflow_name": workflow.workflow_name,
            "status": workflow.status,
            "progress_percentage": workflow.progress_percentage(),
            "total_tasks": len(workflow.tasks),
            "completed_tasks": sum(1 for t in workflow.tasks if t.status == TaskStatus.COMPLETED),
            "failed_tasks": sum(1 for t in workflow.tasks if t.status == TaskStatus.FAILED),
            "pending_tasks": sum(1 for t in workflow.tasks if t.status == TaskStatus.PENDING),
            "awaiting_approval": sum(1 for t in workflow.tasks if t.status == TaskStatus.WAITING_APPROVAL),
            "created_at": workflow.created_at,
            "started_at": workflow.started_at,
            "completed_at": workflow.completed_at
        }
    
    def list_workflows(self, status_filter: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
        """
        Lista todos los workflows activos
        
        Args:
            status_filter: Filtrar por estado (opcional)
        
        Returns:
            Lista de workflows con estado resumido
        """
        workflows = []
        for workflow in self.active_workflows.values():
            if status_filter and workflow.status != status_filter:
                continue
            
            status = self.get_workflow_status(workflow.workflow_id)
            if status:
                workflows.append(status)
        
        return workflows
    
    # =============================================================================
    # MÉTODOS DE PERSISTENCIA
    # =============================================================================
    
    async def _persist_workflow(self, workflow: WorkflowState, task_definitions: List[TaskDefinition]) -> None:
        """Persiste un workflow en la base de datos"""
        try:
            async with AsyncSessionLocal() as db:
                # Crear workflow en DB
                workflow_crud.create_workflow(
                    db=db,
                    workflow_id=workflow.workflow_id,
                    workflow_name=workflow.workflow_name,
                    workflow_type=task_definitions[0].task_type if task_definitions else "unknown",
                    parameters={"tasks": [t.task_type for t in task_definitions]},
                    config=workflow.config,
                    created_by=None
                )
                
                # Crear tareas en DB
                for task in task_definitions:
                    task_crud.create_task(
                        db=db,
                        task_id=task.task_id,
                        workflow_id=workflow.workflow_id,
                        task_type=task.task_type,
                        agent_type=task.agent.value,
                        parameters=task.parameters,
                        priority=task.priority,
                        requires_approval=task.requires_approval
                    )
                
                # Crear log inicial
                log_crud.create_log(
                    db=db,
                    workflow_id=workflow.workflow_id,
                    level="info",
                    message=f"Workflow creado: {workflow.workflow_name}",
                    source="orchestrator"
                )
                
                await db.commit()
                logger.info(f"Workflow persistido: {workflow.workflow_id}")
        except Exception as e:
            logger.error(f"Error persistiendo workflow: {e}")
    
    async def _update_workflow_status(self, workflow: WorkflowState) -> None:
        """Actualiza el estado de un workflow en la base de datos"""
        if not self.persist_enabled:
            return
        
        try:
            async with AsyncSessionLocal() as db:
                workflow_crud.update_workflow(
                    db=db,
                    workflow_id=workflow.workflow_id,
                    status=workflow.status,
                    progress_percentage=workflow.progress_percentage(),
                    completed_tasks=sum(1 for t in workflow.tasks if t.status == TaskStatus.COMPLETED),
                    failed_tasks=sum(1 for t in workflow.tasks if t.status == TaskStatus.FAILED),
                    started_at=workflow.started_at,
                    completed_at=workflow.completed_at
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Error actualizando workflow: {e}")
    
    async def _persist_task_result(self, workflow_id: str, task_id: str, result: Dict[str, Any], status: str) -> None:
        """Persiste el resultado de una tarea"""
        if not self.persist_enabled:
            return
        
        try:
            async with AsyncSessionLocal() as db:
                task_crud.update_task(
                    db=db,
                    task_id=task_id,
                    status=status,
                    result=result,
                    completed_at=datetime.utcnow() if status in ["completed", "failed"] else None
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Error persistiendo resultado de tarea: {e}")
    
    async def _persist_workflow_result(self, workflow: WorkflowState) -> None:
        """Persiste el resultado final del workflow"""
        if not self.persist_enabled:
            return
        
        try:
            async with AsyncSessionLocal() as db:
                # Recopilar resultados de todas las tareas
                results = {}
                for task in workflow.tasks:
                    if task.result:
                        results[task.task_id] = {
                            "task_type": task.task_type,
                            "status": task.status,
                            "result": task.result
                        }
                
                workflow_crud.update_workflow(
                    db=db,
                    workflow_id=workflow.workflow_id,
                    results=results,
                    completed_at=workflow.completed_at
                )
                
                await db.commit()
                logger.info(f"Resultado del workflow persistido: {workflow.workflow_id}")
        except Exception as e:
            logger.error(f"Error persistiendo resultado del workflow: {e}")
    
    async def _persist_log(self, workflow_id: str, message: str, level: str = "info", source: str = "orchestrator") -> None:
        """Persiste un log en la base de datos"""
        if not self.persist_enabled:
            return
        
        try:
            async with AsyncSessionLocal() as db:
                log_crud.create_log(
                    db=db,
                    workflow_id=workflow_id,
                    level=level,
                    message=message,
                    source=source
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Error persistiendo log: {e}")




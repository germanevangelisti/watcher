"""
Script de migración para crear tablas de workflows de agentes

Ejecutar: python migrate_agent_workflows.py
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine
from app.db.sync_session import SQLALCHEMY_DATABASE_URL
from app.db.models import AgentWorkflow, AgentTask, WorkflowLog
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Ejecuta la migración de base de datos"""
    logger.info("🚀 Iniciando migración de tablas de Agent Workflows...")
    
    # Crear engine síncrono para la migración
    logger.info(f"📁 Conectando a base de datos: {SQLALCHEMY_DATABASE_URL}")
    sync_engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)
    
    try:
        # Crear tablas solo para los modelos de workflows
        logger.info("📋 Creando tablas: agent_workflows, agent_tasks, workflow_logs")
        
        # Crear las tablas
        AgentWorkflow.__table__.create(sync_engine, checkfirst=True)
        logger.info("✅ Tabla 'agent_workflows' creada")
        
        AgentTask.__table__.create(sync_engine, checkfirst=True)
        logger.info("✅ Tabla 'agent_tasks' creada")
        
        WorkflowLog.__table__.create(sync_engine, checkfirst=True)
        logger.info("✅ Tabla 'workflow_logs' creada")
        
        logger.info("🎉 Migración completada exitosamente")
        
        # Verificar tablas
        from sqlalchemy import inspect
        inspector = inspect(sync_engine)
        tables = inspector.get_table_names()
        
        workflow_tables = [t for t in tables if 'agent' in t or 'workflow' in t]
        logger.info(f"📊 Tablas de workflows encontradas: {workflow_tables}")
        
    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        sync_engine.dispose()


if __name__ == "__main__":
    run_migration()


"""
Router principal de la API v1
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    watcher, boletines, batch, boletines_selector, alertas, actos, 
    presupuesto, metricas, redflags, downloader, dashboard,
    dslab_documents, dslab_configs, dslab_executions, dslab_results,
    agents, workflows, websocket, feedback, observability, workflow_history,
    sync, jurisdicciones, menciones, processing_logs, analisis, entidades,
    search, documentos, compliance, upload, pipeline
)

api_router = APIRouter()
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(search.router, tags=["search"])
api_router.include_router(documentos.router, tags=["documentos"])
api_router.include_router(compliance.router, prefix="/compliance", tags=["compliance"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(watcher.router, prefix="/watcher", tags=["watcher"])
api_router.include_router(boletines.router, prefix="/boletines", tags=["boletines"])
api_router.include_router(batch.router, prefix="/batch", tags=["batch"])
api_router.include_router(boletines_selector.router, tags=["boletines-selector"])
api_router.include_router(downloader.router, prefix="/downloader", tags=["downloader"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(jurisdicciones.router, prefix="/jurisdicciones", tags=["jurisdicciones"])
api_router.include_router(menciones.router, prefix="/menciones", tags=["menciones"])
api_router.include_router(entidades.router, prefix="/entidades", tags=["entidades"])
api_router.include_router(processing_logs.router, prefix="/processing", tags=["processing-logs"])
api_router.include_router(analisis.router, prefix="/analisis", tags=["analisis"])
api_router.include_router(alertas.router, prefix="/alertas", tags=["alertas"])
api_router.include_router(actos.router, prefix="/actos", tags=["actos"])
api_router.include_router(presupuesto.router, prefix="/presupuesto", tags=["presupuesto"])
api_router.include_router(metricas.router, prefix="/metricas", tags=["metricas"])
api_router.include_router(redflags.router, prefix="/redflags", tags=["redflags"])

# DS Lab
api_router.include_router(dslab_documents.router, prefix="/dslab", tags=["dslab-documents"])
api_router.include_router(dslab_configs.router, prefix="/dslab", tags=["dslab-configs"])
api_router.include_router(dslab_executions.router, prefix="/dslab", tags=["dslab-executions"])
api_router.include_router(dslab_results.router, prefix="/dslab", tags=["dslab-results"])

# Agentic AI
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
# IMPORTANTE: workflow_history debe ir ANTES que workflows para evitar que {workflow_id} capture "history"
api_router.include_router(workflow_history.router, prefix="/workflows", tags=["workflow-history"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(websocket.router, tags=["websocket"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(observability.router, prefix="/observability", tags=["observability"])

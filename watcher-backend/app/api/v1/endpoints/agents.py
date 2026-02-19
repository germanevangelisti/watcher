"""
API endpoints para gestión de agentes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agents.orchestrator import AgentOrchestrator
from agents.orchestrator.state import AgentType
from agents.document_intelligence import DocumentIntelligenceAgent
from agents.anomaly_detection import AnomalyDetectionAgent
from agents.insight_reporting import InsightReportingAgent
from agents.historical_intelligence import HistoricalIntelligenceAgent
from app.core.agent_config import DEFAULT_AGENT_CONFIG
from app.core.events import event_bus, EventType
from app.db.session import get_db

router = APIRouter()

# Instancia global del orquestador
orchestrator = AgentOrchestrator(config=DEFAULT_AGENT_CONFIG.orchestrator.model_dump())

# Instancias de agentes
doc_agent = DocumentIntelligenceAgent(config=DEFAULT_AGENT_CONFIG.document_intelligence)
anomaly_agent = AnomalyDetectionAgent(config=DEFAULT_AGENT_CONFIG.anomaly_detection)
insight_agent = InsightReportingAgent(config=DEFAULT_AGENT_CONFIG.insight_reporting)
historical_agent = HistoricalIntelligenceAgent()

# Registrar handlers en el orquestador
async def document_handler(workflow, task):
    """Handler para Document Intelligence Agent"""
    result = await doc_agent.execute(workflow, task)
    await event_bus.emit(
        EventType.TASK_COMPLETED,
        {"task_id": task.task_id, "agent": "document_intelligence"},
        source="document_agent"
    )
    return result

async def anomaly_handler(workflow, task):
    """Handler para Anomaly Detection Agent"""
    result = await anomaly_agent.execute(workflow, task)
    await event_bus.emit(
        EventType.TASK_COMPLETED,
        {"task_id": task.task_id, "agent": "anomaly_detection"},
        source="anomaly_agent"
    )
    return result

async def insight_handler(workflow, task):
    """Handler para Insight Reporting Agent"""
    result = await insight_agent.execute(workflow, task)
    await event_bus.emit(
        EventType.TASK_COMPLETED,
        {"task_id": task.task_id, "agent": "insight_reporting"},
        source="insight_agent"
    )
    return result

async def historical_handler(workflow, task):
    """Handler para Historical Intelligence Agent"""
    result = await historical_agent.execute(workflow, task)
    await event_bus.emit(
        EventType.TASK_COMPLETED,
        {"task_id": task.task_id, "agent": "historical_intelligence"},
        source="historical_agent"
    )
    return result

orchestrator.register_agent_handler(AgentType.DOCUMENT_INTELLIGENCE, document_handler)
orchestrator.register_agent_handler(AgentType.ANOMALY_DETECTION, anomaly_handler)
orchestrator.register_agent_handler(AgentType.INSIGHT_REPORTING, insight_handler)
orchestrator.register_agent_handler(AgentType.HISTORICAL_INTELLIGENCE, historical_handler)


# Schemas
class AgentStatusResponse(BaseModel):
    agent_type: str
    status: str
    is_available: bool
    tasks_processed: int = 0

class AgentHealthResponse(BaseModel):
    system_status: str
    agents: List[AgentStatusResponse]
    active_workflows: int
    total_tasks_completed: int


# Endpoints
@router.get("/health", response_model=AgentHealthResponse)
async def get_agents_health():
    """
    Obtiene el estado de salud de todos los agentes
    """
    agents_status = [
        AgentStatusResponse(
            agent_type="document_intelligence",
            status="active",
            is_available=True
        ),
        AgentStatusResponse(
            agent_type="anomaly_detection",
            status="active",
            is_available=True
        ),
        AgentStatusResponse(
            agent_type="insight_reporting",
            status="active",
            is_available=True
        ),
        AgentStatusResponse(
            agent_type="historical_intelligence",
            status="active",
            is_available=True
        )
    ]
    
    return AgentHealthResponse(
        system_status="healthy",
        agents=agents_status,
        active_workflows=len(orchestrator.active_workflows),
        total_tasks_completed=0
    )


@router.get("/status/{agent_type}")
async def get_agent_status(agent_type: str):
    """
    Obtiene el estado de un agente específico
    """
    valid_agents = ["document_intelligence", "anomaly_detection", "insight_reporting"]
    
    if agent_type not in valid_agents:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    
    return {
        "agent_type": agent_type,
        "status": "active",
        "is_available": True,
        "capabilities": {
            "document_intelligence": ["extract_document", "classify_content", "extract_entities"],
            "anomaly_detection": ["analyze_document", "calculate_transparency_score", "detect_red_flags"],
            "insight_reporting": ["generate_report", "answer_query", "generate_summary"]
        }.get(agent_type, [])
    }


class ChatRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None


@router.post("/chat")
async def chat_with_agent(request: ChatRequest):
    """
    Interactúa con el Insight Agent mediante chat con datos reales
    """
    try:
        # Usar el nuevo método que consulta datos reales
        result = await insight_agent.query_with_data(request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/clear")
async def clear_chat_history():
    """
    Limpia el historial de conversación
    """
    insight_agent.clear_conversation()
    return {"message": "Historial de conversación limpiado"}


@router.get("/insights/statistics")
async def get_system_statistics(db: AsyncSession = Depends(get_db)):
    """
    Obtiene estadísticas generales del sistema
    """
    try:
        from agents.tools.database_tools import DatabaseTools
        stats = await DatabaseTools.get_statistics(db)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/top-risk")
async def get_top_risk_documents(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """
    Obtiene documentos con mayor riesgo
    """
    try:
        from agents.tools.analysis_tools import AnalysisTools
        top_risk = await AnalysisTools.get_top_risk_documents(db, limit=limit)
        return {"documents": top_risk}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/trends")
async def get_transparency_trends(
    start_year: int = 2025,
    start_month: int = 1,
    end_year: int = 2025,
    end_month: int = 11,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene tendencias de transparencia en un período
    """
    try:
        from agents.tools.analysis_tools import AnalysisTools
        trends = await AnalysisTools.get_transparency_trends(
            db, start_year, start_month, end_year, end_month
        )
        return {"trends": trends}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/monthly-summary/{year}/{month}")
async def get_monthly_summary(year: int, month: int, db: AsyncSession = Depends(get_db)):
    """
    Genera un resumen mensual completo
    """
    try:
        from agents.tools.analysis_tools import AnalysisTools
        summary = await AnalysisTools.get_monthly_summary(db, year, month)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/red-flag-distribution")
async def get_red_flag_distribution(
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene la distribución de red flags
    """
    try:
        from agents.tools.analysis_tools import AnalysisTools
        distribution = await AnalysisTools.get_red_flag_distribution(db, year, month)
        return distribution
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


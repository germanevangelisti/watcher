"""
API endpoints para gestión de agentes
"""
from typing import Any

from agents.anomaly_detection import AnomalyDetectionAgent
from agents.document_intelligence import DocumentIntelligenceAgent
from agents.historical_intelligence import HistoricalIntelligenceAgent
from agents.insight_reporting import InsightReportingAgent
from agents.orchestrator import AgentOrchestrator
from agents.orchestrator.state import AgentType
from agents.tools.presupuesto_tools import budget_tool_names
from app.core.agent_config import DEFAULT_AGENT_CONFIG
from app.core.events import EventType, event_bus
from app.db.session import get_db
from app.services.llm_provider import (
    build_provider,
    configured_provider,
    estado_de_ollama,
    provider_catalog,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

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
    agents: list[AgentStatusResponse]
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
            # Las tools de presupuesto se derivan de `PRESUPUESTO_TOOLS`, que es la
            # misma tabla que usa el router del chat: la lista no puede quedar
            # desincronizada de lo que el agente realmente puede invocar.
            "insight_reporting": [
                "generate_report", "answer_query", "generate_summary",
                *budget_tool_names(),
            ],
        }.get(agent_type, [])
    }


class ChatRequest(BaseModel):
    query: str
    context: dict[str, Any] | None = None
    # Elección explícita de proveedor para **este** turno, desde el panel de
    # agentes.  `None` = el que resolvió el entorno, que es el comportamiento
    # de siempre.
    provider: str | None = None
    model: str | None = None


@router.get("/llm/providers")
async def list_llm_providers():
    """Qué proveedores de LLM se pueden usar, con cuál arranca el chat y por qué.

    El proveedor del chat sale de `LLM_PROVIDER` en el `.env`, que no se ve
    desde ninguna pantalla: hasta ahora la única forma de saber si las
    respuestas las escribía Gemini o el modelo local era leer el log.  El
    catálogo dice, para cada uno, si está disponible y **qué le falta** — un
    selector que ofrece opciones que van a fallar no sirve para comparar nada.
    """
    return {
        "providers": await provider_catalog(),
        "configured": configured_provider(),
    }


@router.post("/chat")
async def chat_with_agent(request: ChatRequest):
    """
    Interactúa con el Insight Agent mediante chat con datos reales
    """
    proveedor = None
    if request.provider:
        # Se construye antes de tocar la base: si el proveedor elegido no se
        # puede usar, el turno no gasta una consulta para después fallar.
        try:
            proveedor = build_provider(request.provider, request.model)
            if request.provider.strip().lower() == "ollama":
                await _exigir_modelo_local(request.model)
        except ValueError as exc:
            # **Sin fallback.**  Acá el usuario eligió un proveedor para
            # compararlo: contestarle con Ollama le haría comparar Ollama contra
            # Ollama y concluir algo falso sobre Gemini.  Mejor un error que
            # dice qué falta.
            raise HTTPException(status_code=400, detail=str(exc))

    try:
        # Usar el nuevo método que consulta datos reales
        result = await insight_agent.query_with_data(request.query, provider=proveedor)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _exigir_modelo_local(model: str | None) -> None:
    """Un modelo local elegido a mano tiene que estar descargado.

    `OllamaProvider` no hace I/O al construirse (a propósito), así que un modelo
    que ya no está en el servidor —el valor recordado en el navegador después de
    borrarlo, por ejemplo— no falla al elegirlo: falla en cada turno, con un
    error de HTTP que no dice cuál es el problema.
    """
    if not model:
        return

    estado = await estado_de_ollama()
    if not estado["responde"]:
        raise ValueError(estado["motivo"])
    if model not in estado["modelos"]:
        disponibles = ", ".join(estado["modelos"]) or "ninguno"
        raise ValueError(
            f"el modelo «{model}» no está descargado en el servidor local "
            f"(hay: {disponibles})"
        )


@router.post("/chat/clear")
async def clear_chat_history():
    """
    Limpia el historial de conversación del Insight Agent.

    Idempotente: sobre un historial ya vacío responde igual (200) con
    `cleared: 0`. El campo `cleared` son los mensajes borrados (2 por turno),
    para que el FE pueda distinguir "limpié" de "ya estaba limpio" sin adivinar.
    """
    cleared = insight_agent.clear_conversation()
    return {"message": "Historial de conversación limpiado", "cleared": cleared}


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
    year: int | None = None,
    month: int | None = None,
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


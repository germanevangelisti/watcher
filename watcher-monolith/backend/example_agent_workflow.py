"""
Ejemplo de uso del sistema de Agentes

Este script demuestra cómo crear y ejecutar workflows con los agentes implementados.
"""
import asyncio
import sys
from pathlib import Path

# Agregar el directorio al path
sys.path.insert(0, str(Path(__file__).parent))

from agents.orchestrator import AgentOrchestrator
from agents.orchestrator.state import AgentType
from agents.document_intelligence import DocumentIntelligenceAgent
from agents.anomaly_detection import AnomalyDetectionAgent
from agents.insight_reporting import InsightReportingAgent
from app.core.agent_config import DEFAULT_AGENT_CONFIG
from app.core.events import event_bus, EventType


async def example_document_analysis():
    """
    Ejemplo 1: Análisis completo de un documento
    """
    print("\n" + "="*60)
    print("EJEMPLO 1: Análisis Completo de Documento")
    print("="*60 + "\n")
    
    # Inicializar agentes
    orchestrator = AgentOrchestrator()
    doc_agent = DocumentIntelligenceAgent(DEFAULT_AGENT_CONFIG.document_intelligence)
    anomaly_agent = AnomalyDetectionAgent(DEFAULT_AGENT_CONFIG.anomaly_detection)
    
    # Registrar handlers
    async def doc_handler(workflow, task):
        return await doc_agent.execute(workflow, task)
    
    async def anomaly_handler(workflow, task):
        return await anomaly_agent.execute(workflow, task)
    
    orchestrator.register_agent_handler(AgentType.DOCUMENT_INTELLIGENCE, doc_handler)
    orchestrator.register_agent_handler(AgentType.ANOMALY_DETECTION, anomaly_handler)
    
    # Crear workflow
    workflow = await orchestrator.create_workflow(
        workflow_name="Análisis de Boletín de Prueba",
        tasks=[
            {
                "task_type": "extract_document",
                "agent": AgentType.DOCUMENT_INTELLIGENCE,
                "parameters": {
                    "file_path": "data/raw/20250801_1_Secc.pdf",
                    "document_id": "test_doc_001"
                },
                "priority": 10,
                "requires_approval": False
            },
            # La segunda tarea usará los resultados de la primera
            {
                "task_type": "analyze_document",
                "agent": AgentType.ANOMALY_DETECTION,
                "parameters": {
                    "text": "",  # Se llenará con resultados de la tarea anterior
                    "entities": {},
                    "document_id": "test_doc_001"
                },
                "priority": 9,
                "requires_approval": True  # Requiere aprobación humana
            }
        ]
    )
    
    print(f"✅ Workflow creado: {workflow.workflow_id}")
    print(f"   Nombre: {workflow.workflow_name}")
    print(f"   Total de tareas: {len(workflow.tasks)}")
    
    # Ejecutar workflow
    print("\n⏳ Ejecutando workflow...\n")
    
    result = await orchestrator.execute_workflow(workflow.workflow_id)
    
    # Mostrar resultados
    print(f"\n📊 Resultados del Workflow:")
    print(f"   Estado final: {result.status}")
    print(f"   Progreso: {result.progress_percentage():.1f}%")
    print(f"   Tareas completadas: {sum(1 for t in result.tasks if t.status.value == 'completed')}")
    print(f"   Tareas fallidas: {sum(1 for t in result.tasks if t.status.value == 'failed')}")
    
    # Mostrar logs
    print(f"\n📝 Logs del workflow:")
    for log in result.logs[-5:]:  # Últimos 5 logs
        print(f"   {log}")
    
    return workflow


async def example_chat_interaction():
    """
    Ejemplo 2: Interacción con el Insight Agent via Chat
    """
    print("\n" + "="*60)
    print("EJEMPLO 2: Chat con Insight Agent")
    print("="*60 + "\n")
    
    insight_agent = InsightReportingAgent(DEFAULT_AGENT_CONFIG.insight_reporting)
    
    queries = [
        "¿Qué es el sistema Watcher?",
        "¿Cómo funciona el análisis de transparencia?",
        "Dame un resumen de las capacidades del sistema"
    ]
    
    for query in queries:
        print(f"👤 Usuario: {query}")
        
        response = await insight_agent.answer_query(query)
        
        if response["success"]:
            print(f"🤖 Agente: {response['response']}\n")
        else:
            print(f"❌ Error: {response['error']}\n")
        
        await asyncio.sleep(1)  # Pequeña pausa entre queries


async def example_feedback_loop():
    """
    Ejemplo 3: Sistema de Feedback y Mejora Continua
    """
    print("\n" + "="*60)
    print("EJEMPLO 3: Feedback y Learning Loop")
    print("="*60 + "\n")
    
    from agents.learning import LearningAgent
    
    learning_agent = LearningAgent()
    
    # Simular feedback de usuario
    print("📝 Registrando feedback de usuario...\n")
    
    # Caso 1: Validar una red flag como verdadero positivo
    result1 = learning_agent.validate_red_flag(
        red_flag_id="rf_001",
        is_valid=True,
        user_notes="Confirmado: monto excesivo sin justificación"
    )
    print(f"✅ Red flag validada: {result1['feedback_id']}")
    
    # Caso 2: Marcar una red flag como falso positivo
    result2 = learning_agent.validate_red_flag(
        red_flag_id="rf_002",
        is_valid=False,
        user_notes="Falso positivo: monto normal para este tipo de contrato"
    )
    print(f"✅ Red flag validada: {result2['feedback_id']}")
    
    # Caso 3: Corregir clasificación
    result3 = learning_agent.rate_classification(
        document_id="doc_001",
        predicted_class="licitacion",
        actual_class="decreto",
        user_notes="Clasificación incorrecta"
    )
    print(f"✅ Clasificación corregida: {result3['feedback_id']}")
    
    # Obtener métricas actuales
    print("\n📊 Métricas de Performance:")
    metrics = learning_agent.get_performance_metrics()
    print(f"   Total de feedback recibido: {metrics['total_feedback_count']}")
    print(f"   Red Flags - Precision: {metrics['metrics']['red_flags']['precision']:.2f}")
    print(f"   Clasificaciones - Accuracy: {metrics['metrics']['classifications']['accuracy']:.2f}")
    
    # Ver ajustes sugeridos
    adjustments = learning_agent.get_suggested_adjustments()
    if adjustments:
        print(f"\n💡 Ajustes Sugeridos:")
        for i, adj in enumerate(adjustments):
            print(f"   {i+1}. {adj['suggestion']}")
            print(f"      Razón: {adj['reason']}")


async def example_event_system():
    """
    Ejemplo 4: Sistema de Eventos en Tiempo Real
    """
    print("\n" + "="*60)
    print("EJEMPLO 4: Sistema de Eventos")
    print("="*60 + "\n")
    
    # Callback para eventos
    async def on_workflow_created(event):
        print(f"🔔 Evento: Workflow creado - {event.data['workflow_name']}")
    
    async def on_task_completed(event):
        print(f"✅ Evento: Tarea completada - {event.data['task_id']}")
    
    # Suscribirse a eventos
    event_bus.subscribe(EventType.WORKFLOW_CREATED, on_workflow_created)
    event_bus.subscribe(EventType.TASK_COMPLETED, on_task_completed)
    
    print("👂 Escuchando eventos...\n")
    
    # Emitir algunos eventos de prueba
    await event_bus.emit(
        EventType.WORKFLOW_CREATED,
        {"workflow_name": "Test Workflow", "workflow_id": "wf_123"},
        source="demo"
    )
    
    await event_bus.emit(
        EventType.TASK_COMPLETED,
        {"task_id": "task_001", "agent": "document_intelligence"},
        source="demo"
    )
    
    await asyncio.sleep(0.5)
    
    # Obtener historial de eventos
    print("\n📜 Historial de Eventos (últimos 5):")
    history = event_bus.get_event_history(limit=5)
    for event in history:
        print(f"   [{event['timestamp']}] {event['event_type']} - {event['source']}")


async def example_observability():
    """
    Ejemplo 5: Observability y Telemetría
    """
    print("\n" + "="*60)
    print("EJEMPLO 5: Observability y Telemetría")
    print("="*60 + "\n")
    
    from app.core.observability import observability
    
    # Simular una operación con tracing
    print("⏱️  Ejecutando operación trazada...\n")
    
    with observability.trace_operation("example_operation", tags={"type": "demo"}) as span:
        span.log("Iniciando procesamiento")
        await asyncio.sleep(0.5)
        span.log("Procesamiento a mitad de camino")
        await asyncio.sleep(0.5)
        span.log("Procesamiento completado")
    
    # Obtener estado de salud del sistema
    health = observability.get_system_health()
    print(f"🏥 Estado de Salud del Sistema:")
    print(f"   Estado: {health['status']}")
    print(f"   Operaciones activas: {health['active_operations']}")
    print(f"   Total operaciones completadas: {health['total_operations_completed']}")
    
    # Obtener métricas
    print(f"\n📈 Métricas del Sistema:")
    metrics = observability.metrics.get_metrics_summary()
    print(f"   Contadores: {len(metrics['counters'])} métricas")
    print(f"   Gauges: {len(metrics['gauges'])} métricas")
    print(f"   Histogramas: {len(metrics['histograms_stats'])} métricas")


async def main():
    """
    Función principal que ejecuta todos los ejemplos
    """
    print("\n" + "="*60)
    print("🤖 DEMOSTRACIÓN DEL SISTEMA AGENTIC AI")
    print("="*60)
    
    try:
        # Ejecutar ejemplos
        await example_document_analysis()
        await example_chat_interaction()
        await example_feedback_loop()
        await example_event_system()
        await example_observability()
        
        print("\n" + "="*60)
        print("✅ DEMOSTRACIÓN COMPLETADA")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error en demostración: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n💡 Este script demuestra las capacidades del sistema de Agentes.")
    print("   Asegúrate de que el servidor FastAPI esté corriendo en puerto 8001\n")
    
    asyncio.run(main())






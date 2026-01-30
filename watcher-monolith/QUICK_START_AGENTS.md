# 🚀 Quick Start - Sistema de Agentes

## ✅ Sistema Corriendo

El sistema Agentic AI está completamente implementado y funcionando.

## 🌐 Acceso Rápido

### Frontend
- **Agent Dashboard**: http://localhost:3001/agents
- **Dashboard Principal**: http://localhost:3001
- **DS Lab Manager**: http://localhost:3001/dslab

### Backend
- **API Docs (Swagger)**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/api/v1/agents/health
- **Observability**: http://localhost:8001/api/v1/observability/health

## 🤖 Agentes Disponibles

| Agente | Función | Endpoint Status |
|--------|---------|-----------------|
| **Document Intelligence** | Extrae información de PDFs | `/api/v1/agents/status/document_intelligence` |
| **Anomaly Detection** | Detecta irregularidades | `/api/v1/agents/status/anomaly_detection` |
| **Insight & Reporting** | Chat y reportes | `/api/v1/agents/status/insight_reporting` |
| **Learning & Feedback** | Mejora continua | `/api/v1/feedback/metrics` |

## 📝 Uso Rápido

### 1. Verificar Estado de Agentes

```bash
curl http://localhost:8001/api/v1/agents/health
```

### 2. Crear un Workflow

```bash
curl -X POST http://localhost:8001/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "Análisis de Prueba",
    "tasks": [
      {
        "task_type": "extract_document",
        "agent": "document_intelligence",
        "parameters": {
          "file_path": "data/raw/20250801_1_Secc.pdf"
        }
      }
    ]
  }'
```

### 3. Chat con el Insight Agent

```bash
curl -X POST http://localhost:8001/api/v1/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "¿Qué organismos tienen más alertas?"
  }'
```

### 4. Enviar Feedback

```bash
curl -X POST http://localhost:8001/api/v1/feedback/red-flag/validate \
  -H "Content-Type: application/json" \
  -d '{
    "red_flag_id": "rf_001",
    "is_valid": true,
    "user_notes": "Confirmado como irregularidad"
  }'
```

## 🖥️ Uso desde la UI

### Agent Dashboard (http://localhost:3001/agents)

1. **Ver Estado de Agentes**
   - Tarjetas con estado de cada agente
   - Métricas en tiempo real
   - Health monitoring

2. **Gestionar Workflows**
   - Ver workflows activos/completados/fallidos
   - Aprobar tareas pendientes
   - Ver progreso en tiempo real

3. **Chat con Agentes**
   - Interfaz conversacional
   - Hacer preguntas sobre los datos
   - Obtener insights automáticos

### Ejemplo de Flujo UI

```
1. Ir a http://localhost:3001/agents
2. Ver estado de agentes (deberían estar "active")
3. Scroll down para ver workflows
4. Si hay tareas pendientes de aprobación, hacer click en "Review Approval"
5. En el modal, revisar la tarea y aprobar/rechazar
```

## 🐍 Uso Programático (Python)

### Ejecutar el Script de Ejemplo

```bash
cd backend
python example_agent_workflow.py
```

Este script demuestra:
- ✅ Creación y ejecución de workflows
- ✅ Chat con el Insight Agent
- ✅ Sistema de feedback y learning
- ✅ Eventos en tiempo real
- ✅ Observability y telemetría

### Código de Ejemplo Básico

```python
import asyncio
from agents.orchestrator import AgentOrchestrator

async def quick_example():
    orchestrator = AgentOrchestrator()
    
    # Crear workflow
    workflow = await orchestrator.create_workflow(
        workflow_name="Mi Primer Workflow",
        tasks=[{
            "task_type": "extract_document",
            "agent": "document_intelligence",
            "parameters": {"file_path": "/path/to/doc.pdf"}
        }]
    )
    
    # Ejecutar
    await orchestrator.execute_workflow(workflow.workflow_id)
    
    # Ver resultado
    status = orchestrator.get_workflow_status(workflow.workflow_id)
    print(f"Progreso: {status['progress_percentage']}%")

asyncio.run(quick_example())
```

## 🔌 WebSocket en Tiempo Real

### Conectarse al WebSocket

```javascript
// En el frontend
const ws = new WebSocket('ws://localhost:8001/api/v1/ws');

ws.onopen = () => {
  // Suscribirse a eventos
  ws.send(JSON.stringify({
    action: 'subscribe',
    event_types: [
      'workflow.created',
      'workflow.completed',
      'task.completed'
    ]
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Evento recibido:', data);
};
```

## 📊 Monitoreo y Observability

### Ver Métricas del Sistema

```bash
# Resumen de métricas
curl http://localhost:8001/api/v1/observability/metrics

# Health check completo
curl http://localhost:8001/api/v1/observability/health

# Traces recientes
curl http://localhost:8001/api/v1/observability/traces

# Dashboard consolidado
curl http://localhost:8001/api/v1/observability/dashboard
```

### Ver Eventos del Sistema

```bash
# Últimos 50 eventos
curl http://localhost:8001/api/v1/observability/events

# Eventos de un tipo específico
curl "http://localhost:8001/api/v1/observability/events?event_type=workflow.completed"
```

## 🎯 Casos de Uso Comunes

### Caso 1: Análisis Supervisado de Documento

```bash
# 1. Crear workflow con aprobación requerida
curl -X POST http://localhost:8001/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "Análisis Supervisado",
    "tasks": [{
      "task_type": "analyze_document",
      "agent": "anomaly_detection",
      "parameters": {"document_id": "doc_001"},
      "requires_approval": true
    }]
  }'

# 2. Ejecutar workflow (se detendrá en aprobación)
curl -X POST http://localhost:8001/api/v1/workflows/{workflow_id}/execute

# 3. Ver tareas esperando aprobación
curl http://localhost:8001/api/v1/workflows/{workflow_id}/tasks/awaiting-approval

# 4. Aprobar tarea
curl -X POST http://localhost:8001/api/v1/workflows/{workflow_id}/tasks/{task_id}/approve \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Caso 2: Feedback Loop

```bash
# 1. Validar una red flag
curl -X POST http://localhost:8001/api/v1/feedback/red-flag/validate \
  -H "Content-Type: application/json" \
  -d '{
    "red_flag_id": "rf_123",
    "is_valid": false,
    "user_notes": "Falso positivo - monto normal"
  }'

# 2. Ver métricas actualizadas
curl http://localhost:8001/api/v1/feedback/metrics

# 3. Ver ajustes sugeridos
curl http://localhost:8001/api/v1/feedback/adjustments
```

### Caso 3: Chat Interactivo

```bash
# Hacer una pregunta
curl -X POST http://localhost:8001/api/v1/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "¿Cuántos casos de riesgo alto tenemos este mes?"
  }'

# Limpiar historial de chat
curl -X POST http://localhost:8001/api/v1/agents/chat/clear
```

## 🔧 Configuración

### Ajustar Thresholds

Editar `backend/app/core/agent_config.py`:

```python
class AnomalyDetectionConfig(BaseModel):
    transparency_thresholds: Dict[str, float] = {
        "high_risk": 30,    # <30 = RIESGO ALTO
        "medium_risk": 50,  # 30-50 = RIESGO MEDIO
        "low_risk": 70      # >70 = RIESGO BAJO
    }
    amount_thresholds: Dict[str, float] = {
        "very_high": 50000000  # $50M
    }
```

### Habilitar/Deshabilitar Red Flags

```python
red_flag_rules = {
    "HIGH_AMOUNT": {"enabled": True, "threshold": 50000000},
    "MISSING_BENEFICIARY": {"enabled": True},
    "SUSPICIOUS_AMOUNT_PATTERN": {"enabled": False},  # Deshabilitado
    "LOW_TRANSPARENCY_SCORE": {"enabled": True}
}
```

## 🐛 Troubleshooting

### Problema: Agentes no responden

```bash
# Verificar health
curl http://localhost:8001/api/v1/agents/health

# Verificar logs del servidor
# Ver terminal donde corre uvicorn
```

### Problema: WebSocket no conecta

```bash
# Verificar que el servidor soporte WebSocket
# FastAPI con uvicorn lo soporta por defecto
```

### Problema: Chat no funciona

```bash
# Verificar API key de OpenAI en .env
OPENAI_API_KEY=sk-...

# El sistema tiene fallback sin OpenAI
# Responderá con un mensaje indicando que necesita configuración
```

## 📚 Documentación Completa

- **Arquitectura Técnica**: `docs/AGENTIC_ARCHITECTURE.md`
- **Resumen de Implementación**: `ARQUITECTURA_AGENTIC_IMPLEMENTADA.md`
- **API Reference**: http://localhost:8001/docs

## ✨ Próximos Pasos

1. **Probar el sistema**: Ejecutar `example_agent_workflow.py`
2. **Explorar la UI**: Ir a http://localhost:3001/agents
3. **Crear workflows**: Usar la API o la UI
4. **Dar feedback**: Validar red flags para mejorar el sistema
5. **Monitorear**: Ver métricas y traces en observability

---

**¿Dudas o problemas?**
- Ver logs del servidor: `uvicorn app.main:app --reload --port 8001`
- Revisar documentación: `/docs/AGENTIC_ARCHITECTURE.md`
- Ejecutar ejemplo: `python example_agent_workflow.py`






# Arquitectura Agentic AI - Sistema Watcher

## 📋 Resumen de Implementación

Sistema completo de análisis de transparencia gubernamental basado en **Agentic AI**, donde múltiples agentes especializados colaboran bajo supervisión humana para detectar irregularidades en boletines oficiales.

## ✅ Componentes Implementados

### 1. Backend - Agentes Especializados

#### Agent Orchestrator
- **Ubicación**: `backend/agents/orchestrator/`
- **Funcionalidad**: Coordinador central que gestiona workflows y tareas
- **Características**:
  - Gestión de cola de tareas con prioridades
  - Estado compartido entre agentes
  - Solicitud de aprobación humana en puntos críticos
  - Monitoreo de salud y performance

#### Document Intelligence Agent
- **Ubicación**: `backend/agents/document_intelligence/`
- **Funcionalidad**: Extracción inteligente de información de PDFs
- **Características**:
  - Extracción de texto con pdfplumber
  - Clasificación automática de documentos
  - Detección de entidades (NER): montos, beneficiarios, organismos, fechas
  - Análisis de estructura documental

#### Anomaly Detection Agent
- **Ubicación**: `backend/agents/anomaly_detection/`
- **Funcionalidad**: Detección de patrones sospechosos y red flags
- **Características**:
  - Scoring de transparencia (0-100)
  - Clasificación de riesgo (ALTO/MEDIO/BAJO)
  - Detección de red flags con reglas configurables
  - Análisis de anomalías estadísticas
  - Explicaciones interpretables

#### Insight & Reporting Agent
- **Ubicación**: `backend/agents/insight_reporting/`
- **Funcionalidad**: Generación de insights y reportes
- **Características**:
  - Respuestas a queries en lenguaje natural
  - Generación automática de reportes ejecutivos
  - Agregación de métricas y tendencias
  - Chat conversacional con contexto

#### Learning & Feedback Agent
- **Ubicación**: `backend/agents/learning/`
- **Funcionalidad**: Aprendizaje continuo del sistema
- **Características**:
  - Registro de feedback humano
  - Cálculo de métricas de performance
  - Ajuste automático de thresholds
  - Sugerencias de mejoras

### 2. Backend - Infraestructura

#### Event Bus
- **Ubicación**: `backend/app/core/events.py`
- **Funcionalidad**: Sistema de eventos pub/sub para comunicación entre componentes
- **Eventos soportados**:
  - Workflow lifecycle (created, started, completed, failed)
  - Task lifecycle (started, completed, failed, approval)
  - Document events (uploaded, analyzed)
  - Red flag events (detected, validated)
  - System events (health checks, alerts)

#### Configuration System
- **Ubicación**: `backend/app/core/agent_config.py`
- **Funcionalidad**: Configuración centralizada para todos los agentes
- **Configurables**:
  - Thresholds de transparencia
  - Thresholds de montos
  - Reglas de red flags
  - Parámetros de modelos ML
  - Configuración de NLP

#### Observability System
- **Ubicación**: `backend/app/core/observability.py`
- **Funcionalidad**: Telemetría completa del sistema
- **Características**:
  - Métricas (counters, gauges, histograms)
  - Distributed tracing con spans
  - Health checks
  - Performance monitoring
  - Retención configurable de datos

### 3. API Endpoints

#### Agents API (`/api/v1/agents/`)
```
GET  /agents/health                    # Estado de salud de agentes
GET  /agents/status/{agent_type}       # Estado de un agente específico
POST /agents/chat                      # Chat con Insight Agent
POST /agents/chat/clear                # Limpiar historial de chat
```

#### Workflows API (`/api/v1/workflows/`)
```
POST   /workflows                           # Crear workflow
POST   /workflows/{id}/execute              # Ejecutar workflow
GET    /workflows                           # Listar workflows
GET    /workflows/{id}                      # Estado de workflow
GET    /workflows/{id}/details              # Detalles completos
GET    /workflows/{id}/tasks                # Tareas del workflow
GET    /workflows/{id}/logs                 # Logs del workflow
GET    /workflows/{id}/tasks/awaiting-approval  # Tareas pendientes de aprobación
POST   /workflows/{id}/tasks/{task_id}/approve  # Aprobar tarea
POST   /workflows/{id}/tasks/{task_id}/reject   # Rechazar tarea
```

#### Feedback API (`/api/v1/feedback/`)
```
POST /feedback/red-flag/validate       # Validar red flag
POST /feedback/classification/rate     # Corregir clasificación
POST /feedback                         # Feedback genérico
GET  /feedback/metrics                 # Métricas de performance
GET  /feedback/adjustments             # Ajustes sugeridos
POST /feedback/adjustments/{id}/apply  # Aplicar ajuste
GET  /feedback/history                 # Historial de feedback
GET  /feedback/insights                # Insights de aprendizaje
```

#### Observability API (`/api/v1/observability/`)
```
GET  /observability/health             # Estado del sistema
GET  /observability/metrics            # Resumen de métricas
GET  /observability/metrics/{name}     # Historial de métrica
GET  /observability/traces             # Traces recientes
GET  /observability/traces/{operation} # Stats de operación
GET  /observability/events             # Historial de eventos
GET  /observability/dashboard          # Datos consolidados
POST /observability/events/clear       # Limpiar eventos
POST /observability/metrics/cleanup    # Limpiar métricas antiguas
```

#### WebSocket (`/api/v1/ws`)
```
WebSocket /ws                          # Conexión real-time
GET       /ws/stats                    # Estadísticas de conexiones

Mensajes soportados:
- subscribe: Suscribirse a eventos
- unsubscribe: Desuscribirse
- ping: Keep-alive
```

### 4. Frontend - Componentes React

#### Agent Dashboard (`/agent-dashboard`)
- **Ubicación**: `frontend/src/pages/AgentDashboard.tsx`
- **Componentes**:
  - `AgentCard`: Card individual de agente
  - `AgentStatusMonitor`: Monitor de salud del sistema
  - Lista de workflows activos/completados/fallidos
  - Tabs para filtrar workflows por estado

#### Agent Chat
- **Ubicación**: `frontend/src/components/agents/AgentChat.tsx`
- **Funcionalidad**:
  - Chat conversacional con Insight Agent
  - Historial de conversación con contexto
  - Mensajes con timestamp
  - Limpieza de historial

#### Workflow Approval Interface
- **Ubicación**: `frontend/src/components/agents/WorkflowApproval.tsx`
- **Funcionalidad**:
  - Lista de tareas esperando aprobación
  - Preview de parámetros de tarea
  - Modificación de parámetros antes de aprobar
  - Rechazo con razón
  - Modal interactivo

## 🔄 Flujos de Trabajo Implementados

### Flujo 1: Análisis Supervisado de Documento

```python
# 1. Crear workflow
workflow = await orchestrator.create_workflow(
    workflow_name="Analizar Boletín 20250801",
    tasks=[
        {
            "task_type": "extract_document",
            "agent": "document_intelligence",
            "parameters": {"file_path": "/path/to/doc.pdf"},
            "requires_approval": False
        },
        {
            "task_type": "analyze_document",
            "agent": "anomaly_detection",
            "parameters": {},
            "requires_approval": True  # ← Usuario debe aprobar
        }
    ]
)

# 2. Ejecutar workflow
await orchestrator.execute_workflow(workflow.workflow_id)

# 3. Usuario recibe notificación de aprobación pendiente
# 4. Usuario revisa y aprueba/rechaza
# 5. Workflow continúa o se cancela
```

### Flujo 2: Chat con Agente

```typescript
// Frontend
const response = await fetch('/api/v1/agents/chat', {
  method: 'POST',
  body: JSON.stringify({
    query: "¿Qué organismos recibieron más subsidios en agosto?"
  })
});

const data = await response.json();
// {
//   "success": true,
//   "query": "...",
//   "response": "Análisis de subsidios...",
//   "timestamp": "..."
// }
```

### Flujo 3: Feedback y Mejora Continua

```python
# Usuario valida una red flag
feedback = await learning_agent.validate_red_flag(
    red_flag_id="rf_123",
    is_valid=False,  # Falso positivo
    user_notes="No es irregular, es un monto estándar"
)

# Sistema actualiza métricas
# {
//   "success": true,
//   "current_metrics": {
//     "red_flags": {
//       "precision": 0.75,
//       "false_positives": 5
//     }
//   }
// }

# Sistema sugiere ajustes
adjustments = learning_agent.get_suggested_adjustments()
# [
//   {
//     "type": "threshold_adjustment",
//     "reason": "Alta tasa de falsos positivos",
//     "suggestion": "Incrementar threshold de $50M a $75M"
//   }
// ]
```

## 📊 Métricas y Observability

### Métricas Disponibles

```python
# Counters
operation.document_extraction.success
operation.document_extraction.failure
operation.anomaly_detection.success

# Histograms (con percentiles)
operation.document_extraction.duration_ms
operation.anomaly_detection.duration_ms

# Gauges
system.active_workflows
system.agents_healthy
```

### Traces

Cada operación genera un trace con:
- Span ID único
- Duración en ms
- Tags (función, agente, etc.)
- Logs internos
- Estado (completed/failed)

## 🚀 Cómo Usar el Sistema

### 1. Setup Inicial

```bash
# Backend
cd backend
pip install -r requirements.txt

# Crear tablas de agentes (agregar a migration)
python -c "from agents.orchestrator.state import WorkflowState; print('OK')"

# Iniciar servidor
uvicorn app.main:app --reload --port 8001
```

```bash
# Frontend
cd frontend
npm install
npm run dev
```

### 2. Acceder a la UI

- **Dashboard Principal**: http://localhost:3001
- **Agent Dashboard**: http://localhost:3001/agent-dashboard
- **API Docs**: http://localhost:8001/docs

### 3. Ejemplo de Uso Completo

```python
# Crear un workflow de análisis
import httpx

# 1. Crear workflow
response = await httpx.post('http://localhost:8001/api/v1/workflows', json={
    "workflow_name": "Análisis Agosto 2025",
    "tasks": [
        {
            "task_type": "extract_document",
            "agent": "document_intelligence",
            "parameters": {
                "file_path": "/boletines/2025/08/20250801_1_Secc.pdf"
            }
        },
        {
            "task_type": "analyze_document",
            "agent": "anomaly_detection",
            "parameters": {},
            "requires_approval": True
        }
    ]
})

workflow = response.json()

# 2. Ejecutar workflow
await httpx.post(f'http://localhost:8001/api/v1/workflows/{workflow["workflow_id"]}/execute')

# 3. Monitorear progreso (polling o WebSocket)
status = await httpx.get(f'http://localhost:8001/api/v1/workflows/{workflow["workflow_id"]}')

# 4. Si hay tareas esperando aprobación
awaiting = await httpx.get(f'http://localhost:8001/api/v1/workflows/{workflow["workflow_id"]}/tasks/awaiting-approval')

# 5. Aprobar tarea
if awaiting.json()["awaiting_approval_count"] > 0:
    task_id = awaiting.json()["tasks"][0]["task_id"]
    await httpx.post(
        f'http://localhost:8001/api/v1/workflows/{workflow["workflow_id"]}/tasks/{task_id}/approve',
        json={"modifications": {}}
    )
```

## 🔧 Configuración Avanzada

### Ajustar Thresholds

```python
# En agent_config.py o mediante API
config = {
    "anomaly_detection": {
        "transparency_thresholds": {
            "high_risk": 30,  # <30 = ALTO
            "medium_risk": 50,  # 30-50 = MEDIO
            "low_risk": 70  # >70 = BAJO
        },
        "amount_thresholds": {
            "very_high": 50000000  # $50M
        }
    }
}
```

### Habilitar/Deshabilitar Red Flags

```python
red_flag_rules = {
    "HIGH_AMOUNT": {"enabled": True, "threshold": 50000000},
    "MISSING_BENEFICIARY": {"enabled": True},
    "SUSPICIOUS_AMOUNT_PATTERN": {"enabled": True, "patterns": ["999999"]},
    "LOW_TRANSPARENCY_SCORE": {"enabled": True, "threshold": 30}
}
```

## 📈 Próximos Pasos (Post-MVP)

### Fase 2: Semi-Autonomía (3-6 meses)
- [ ] Auto-aprobación de casos de riesgo BAJO
- [ ] Análisis automático programado
- [ ] Reentrenamiento incremental de modelos ML
- [ ] Detección de concept drift

### Fase 3: Autonomía Completa (6-12 meses)
- [ ] Ejecución completamente automática
- [ ] Alertas solo para casos críticos
- [ ] A/B testing de configuraciones
- [ ] Knowledge graph de entidades

## 🐛 Troubleshooting

### WebSocket no conecta
```bash
# Verificar que el servidor soporte WebSocket
# FastAPI incluye soporte por defecto con uvicorn
```

### Agentes no responden
```bash
# Verificar health
curl http://localhost:8001/api/v1/agents/health

# Verificar observability
curl http://localhost:8001/api/v1/observability/health
```

### Chat no funciona
```bash
# Verificar API key de OpenAI
# En .env
OPENAI_API_KEY=sk-...

# El sistema tiene fallback sin OpenAI
```

## 📝 Notas de Implementación

- Todos los agentes son **asíncronos** para máxima performance
- El sistema usa **event-driven architecture** para desacoplamiento
- Los workflows son **persistibles** (agregar SQLAlchemy models para producción)
- El frontend usa **React Query** para cache y revalidación automática
- WebSocket permite **actualizaciones en tiempo real** sin polling

## 🎯 Métricas de Éxito del MVP

- ✅ Orquestador funcional con state management
- ✅ 3+ agentes especializados implementados
- ✅ API completa para workflows supervisados
- ✅ UI con dashboard, chat y aprobación
- ✅ WebSocket para real-time updates
- ✅ Sistema de feedback y learning
- ✅ Observability completa con métricas y traces

---

**Implementado por**: AI Assistant
**Fecha**: Noviembre 2025
**Versión**: 1.0.0 (MVP)






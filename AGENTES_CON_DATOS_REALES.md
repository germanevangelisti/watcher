# 🤖 Sistema de Agentes Conectado a Datos Reales

## ✅ Integración Completada

Los agentes del sistema Watcher ahora están **completamente integrados con tus datos reales**:

- **1,063 boletines** oficiales descargados
- **167 resultados de análisis** disponibles
- **688 red flags** detectadas (631 de alta severidad)
- **Score promedio de transparencia**: 89.40

---

## 🔌 Componentes Implementados

### 1. Herramientas de Base de Datos (`agents/tools/database_tools.py`)

Proporciona acceso directo a los datos reales:

- `get_documents()` - Obtiene documentos con filtros
- `get_analysis_results()` - Resultados de análisis filtrados
- `get_red_flags()` - Red flags por severidad y categoría
- `get_statistics()` - Estadísticas generales del sistema
- `get_document_with_results()` - Documento completo con análisis
- `search_by_entity()` - Búsqueda por entidades (beneficiarios, montos, etc.)

### 2. Herramientas de Análisis (`agents/tools/analysis_tools.py`)

Genera insights avanzados:

- `get_transparency_trends()` - Tendencias temporales de transparencia
- `get_red_flag_distribution()` - Distribución de anomalías
- `get_top_risk_documents()` - Documentos más críticos
- `get_entity_analysis()` - Análisis de entidades frecuentes
- `compare_periods()` - Comparación entre períodos
- `detect_anomalous_patterns()` - Detección de patrones sospechosos
- `get_monthly_summary()` - Resumen mensual completo

### 3. Agentes Mejorados

#### Insight Reporting Agent
- Nuevo método `query_with_data()` que consulta la BD real
- Detección automática del tipo de consulta
- Generación de respuestas basadas en datos reales
- Integración con OpenAI para respuestas naturales

---

## 🚀 Uso del Sistema

### Opción 1: Demo Interactivo

```bash
cd watcher-monolith/backend
python demo_agents_with_data.py
```

Este script ejecuta 6 demos que muestran:
1. 📊 Estadísticas generales del sistema
2. 🔴 Top 5 documentos de mayor riesgo
3. 📈 Tendencias de transparencia 2025
4. 🚩 Distribución de red flags
5. 📋 Resumen mensual (Agosto 2025)
6. 💬 Chat con Insight Agent usando datos reales

### Opción 2: API REST

Inicia el servidor:

```bash
cd watcher-monolith/backend
uvicorn app.main:app --reload --port 8001
```

#### Endpoints Disponibles

**Estadísticas Generales**
```bash
curl http://localhost:8001/api/v1/agents/insights/statistics
```

**Documentos de Alto Riesgo**
```bash
curl http://localhost:8001/api/v1/agents/insights/top-risk?limit=10
```

**Tendencias de Transparencia**
```bash
curl "http://localhost:8001/api/v1/agents/insights/trends?start_year=2025&start_month=1&end_year=2025&end_month=11"
```

**Resumen Mensual**
```bash
curl http://localhost:8001/api/v1/agents/insights/monthly-summary/2025/8
```

**Chat con Datos Reales**
```bash
curl -X POST http://localhost:8001/api/v1/agents/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Cuántos documentos de alto riesgo hay?"}'
```

### Opción 3: Dashboard Web

1. Inicia el backend (puerto 8001)
2. Inicia el frontend:
```bash
cd watcher-monolith/frontend
npm run dev
```
3. Accede a `http://localhost:5173/agents`

---

## 💡 Ejemplos de Consultas al Chat Agent

El Insight Agent ahora puede responder preguntas reales sobre tus datos:

### Consultas de Estadísticas
```json
{
  "query": "¿Cuántos documentos hay en total?"
}
// Respuesta: Basada en los 1,063 documentos reales
```

### Consultas de Riesgo
```json
{
  "query": "Muéstrame los documentos más críticos"
}
// Respuesta: Lista de documentos con mayor número de red flags
```

### Consultas de Tendencias
```json
{
  "query": "¿Cómo ha evolucionado la transparencia en 2025?"
}
// Respuesta: Análisis de tendencias mes a mes con datos reales
```

### Consultas de Red Flags
```json
{
  "query": "¿Qué tipo de irregularidades son más comunes?"
}
// Respuesta: Distribución de los 688 red flags reales
```

### Consultas de Entidades
```json
{
  "query": "¿Qué organismos aparecen más frecuentemente?"
}
// Respuesta: Análisis de entidades extraídas de los documentos
```

---

## 📊 Datos Disponibles

### Por Período (2025)

| Mes | Documentos | Analizados |
|-----|-----------|------------|
| Enero | 108 | ✅ |
| Febrero | 99 | ✅ |
| Marzo | 88 | - |
| Abril | 95 | - |
| Mayo | 100 | - |
| Junio | 94 | - |
| Julio | 107 | - |
| Agosto | 99 | - |
| Septiembre | 110 | - |
| Octubre | 110 | - |
| Noviembre | 53 | - |

### Red Flags Detectadas

- **Total**: 688
- **Alta severidad**: 631
- **Media severidad**: 57

#### Por Tipo
- `HIGH_AMOUNT`: 631 casos
- `MISSING_BENEFICIARY`: 55 casos
- `SUSPICIOUS_AMOUNT_PATTERN`: 2 casos

#### Por Categoría
- `amounts`: 631
- `transparency`: 55
- `patterns`: 2

---

## 🔮 Capacidades Futuras

Con esta integración, los agentes ahora pueden:

1. **Análisis Predictivo**: Detectar patrones de riesgo antes de que se conviertan en problemas
2. **Alertas Inteligentes**: Notificar automáticamente sobre anomalías críticas
3. **Reportes Automatizados**: Generar informes ejecutivos sin intervención manual
4. **Búsqueda Semántica**: Encontrar documentos relacionados por contenido, no solo por metadatos
5. **Aprendizaje Continuo**: Mejorar detección basándose en feedback del usuario

---

## 🛠️ Arquitectura Técnica

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│                  Agent Dashboard UI                          │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/WebSocket
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Backend (Python)                     │
├─────────────────────────────────────────────────────────────┤
│  Agent Endpoints         │  Workflow Endpoints              │
│  - /agents/chat         │  - /workflows                    │
│  - /agents/insights/*   │  - /feedback                     │
└──────────┬──────────────┴─────────────────────┬─────────────┘
           │                                    │
           ▼                                    ▼
┌─────────────────────┐            ┌──────────────────────────┐
│  Insight Agent      │            │  Database Tools          │
│  - query_with_data()│◄───────────│  - get_documents()       │
│  - generate_report()│            │  - get_analysis_results()│
└─────────────────────┘            └──────────┬───────────────┘
           │                                   │
           ▼                                   ▼
┌──────────────────────────────────────────────────────────────┐
│                    SQLite Database                           │
│  - boletin_documents (1,063 docs)                           │
│  - analysis_results (167 resultados)                        │
│  - red_flags (688 alertas)                                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 🎯 Próximos Pasos

1. **Prueba el Demo**:
   ```bash
   python demo_agents_with_data.py
   ```

2. **Inicia el Sistema Completo**:
   ```bash
   # Terminal 1: Backend
   cd watcher-monolith/backend
   uvicorn app.main:app --reload --port 8001
   
   # Terminal 2: Frontend
   cd watcher-monolith/frontend
   npm run dev
   ```

3. **Accede al Dashboard**:
   - Frontend: `http://localhost:5173/agents`
   - API Docs: `http://localhost:8001/docs`

4. **Prueba Consultas**:
   - Haz preguntas en lenguaje natural
   - Explora los insights generados
   - Revisa documentos de alto riesgo

---

## 📝 Notas Técnicas

### Base de Datos
- Uso de **sesión síncrona** (`SyncSessionLocal`) para compatibilidad con herramientas
- Queries optimizadas con índices en campos clave
- Soporte para filtros complejos y agregaciones

### Performance
- Límites configurables en todas las queries
- Cache de resultados frecuentes (próximamente)
- Paginación en endpoints REST

### Seguridad
- Validación de parámetros en todos los endpoints
- Manejo de errores robusto
- Logging completo de operaciones

---

## ❓ Soporte

Si encuentras algún problema:

1. Verifica que la base de datos existe: `ls -la watcher-monolith/backend/sqlite.db`
2. Revisa los logs del backend
3. Ejecuta `python demo_agents_with_data.py` para diagnóstico
4. Verifica que tienes la variable `OPENAI_API_KEY` configurada (para chat avanzado)

---

**✅ Sistema Completamente Funcional y Conectado a Datos Reales**

Los agentes ahora tienen acceso completo a tus 1,063 documentos, 688 red flags y todos los análisis históricos. Pueden responder preguntas, generar insights y ayudarte a entender mejor los datos de transparencia gubernamental.






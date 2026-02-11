# 📝 Sistema de Logs en Tiempo Real

## Resumen

Implementación completa de un sistema de logging en tiempo real tanto para la UI como para el servidor, permitiendo visualizar el progreso detallado del procesamiento de boletines.

**Fecha de Implementación**: 2026-02-03  
**Sprint**: Sprint 0  
**Estado**: ✅ Completado

---

## 🎯 Objetivos Alcanzados

1. ✅ Sistema centralizado de logging en el backend
2. ✅ API endpoints para consultar logs en tiempo real
3. ✅ Componente visual de logs para el frontend
4. ✅ Integración con el Wizard de procesamiento
5. ✅ Tracking de sesiones de procesamiento
6. ✅ Auto-scroll y controles de visualización

---

## 🏗️ Arquitectura

### Backend Components

#### 1. **ProcessingLogger Service**
**Archivo**: `watcher-monolith/backend/app/services/processing_logger.py`

Clase centralizada para manejo de logs:
- Buffer en memoria (deque) con límite configurable
- Thread-safe con locks
- Métodos por nivel de log: `info()`, `success()`, `warning()`, `error()`, `progress()`
- Gestión de sesiones con `start_session()` y `end_session()`
- Soporte para múltiples sesiones concurrentes

```python
from app.services.processing_logger import processing_logger

# Iniciar sesión
processing_logger.start_session(session_id, "Extracción de boletines")

# Logs durante el proceso
processing_logger.info("Consultando base de datos...", session_id)
processing_logger.progress("Procesando archivo", 5, 10, session_id)
processing_logger.success("Completado exitosamente", session_id)

# Finalizar sesión
processing_logger.end_session(session_id, success=True)
```

#### 2. **API Endpoints**
**Archivo**: `watcher-monolith/backend/app/api/v1/endpoints/processing_logs.py`

**Endpoints disponibles**:

- **GET `/api/v1/processing/logs`**
  - Obtiene logs recientes
  - Query params: `session_id` (opcional), `limit` (default: 100)
  - Retorna: Array de log entries

- **DELETE `/api/v1/processing/logs/{session_id}`**
  - Limpia logs de una sesión específica
  - Retorna: Mensaje de confirmación

- **GET `/api/v1/processing/logs/sessions`**
  - Lista sesiones activas con estadísticas
  - Retorna: Información agregada de sesiones

#### 3. **Integración con Process-Batch**
**Archivo**: `watcher-monolith/backend/app/api/v1/endpoints/boletines.py`

El endpoint `/process-batch` ahora:
- Genera un `session_id` único por ejecución
- Registra logs en cada etapa del procesamiento
- Retorna el `session_id` en la respuesta
- Incluye progreso detallado (X/Y archivos procesados)

### Frontend Components

#### 1. **ProcessingLogs Component**
**Archivo**: `watcher-monolith/frontend/src/components/logs/ProcessingLogs.tsx`

Componente React para visualización de logs:

**Props**:
```typescript
interface ProcessingLogsProps {
  sessionId?: string;        // ID de sesión a filtrar
  autoScroll?: boolean;      // Auto-scroll al final (default: true)
  maxHeight?: number;        // Altura máxima en px (default: 400)
  refreshInterval?: number;  // Intervalo de polling en ms (default: 2000)
  showControls?: boolean;    // Mostrar controles (default: true)
}
```

**Características**:
- 🔄 Polling automático para actualizaciones en tiempo real
- 📜 Auto-scroll opcional al final
- ⏸️ Pausa/reanudación de actualizaciones
- 🔄 Botón de refresh manual
- 🗑️ Limpieza de logs por sesión
- 🎨 Códigos de color por nivel de log
- ⏱️ Timestamps formateados
- 📊 Contador de entradas

**Niveles de log y colores**:
- `info` → 🔵 Azul - ℹ️ Información general
- `success` → 🟢 Verde - ✅ Operaciones exitosas
- `warning` → 🟡 Amarillo - ⚠️ Advertencias
- `error` → 🔴 Rojo - ❌ Errores

#### 2. **Integración con Wizard**
**Archivo**: `watcher-monolith/frontend/src/components/wizard/ProcessingWizard.tsx`

**Cambios implementados**:

1. **Nuevos estados**:
```typescript
const [extractionSessionId, setExtractionSessionId] = useState<string | null>(null);
const [processingSessionId, setProcessingSessionId] = useState<string | null>(null);
```

2. **Captura de session_id en startExtraction**:
```typescript
const response = await fetch('/api/v1/boletines/process-batch?...');
const data = await response.json();
if (data.session_id) {
  setExtractionSessionId(data.session_id);
}
```

3. **Renderizado de logs en ExtractionStepContent**:
```tsx
{status === 'in_progress' && sessionId && (
  <Box mt="xl">
    <ProcessingLogs 
      sessionId={sessionId}
      autoScroll={true}
      maxHeight={350}
      refreshInterval={2000}
      showControls={true}
    />
  </Box>
)}
```

4. **Renderizado de logs en ProcessingStepContent**:
```tsx
{status === 'in_progress' && sessionId && (
  <Box mt="lg">
    <ProcessingLogs 
      sessionId={sessionId}
      autoScroll={true}
      maxHeight={300}
      refreshInterval={2000}
      showControls={true}
    />
  </Box>
)}
```

---

## 📋 Estructura de Log Entry

```typescript
interface LogEntry {
  timestamp: string;      // ISO 8601 timestamp
  level: string;          // info | success | warning | error
  message: string;        // Mensaje descriptivo
  session_id: string;     // ID de la sesión
}
```

**Ejemplo**:
```json
{
  "timestamp": "2026-02-03T14:30:45.123Z",
  "level": "success",
  "message": "✅ Completado: boletin_2025_001234.pdf",
  "session_id": "a1b2c3d4"
}
```

---

## 🚀 Flujo de Uso

### 1. Usuario inicia extracción en el Wizard

```
Usuario → Click "Iniciar Extracción" 
       → Frontend llama POST /api/v1/boletines/process-batch
       → Backend genera session_id (ej: "a1b2c3d4")
       → Backend inicia logging con session_id
       → Backend retorna { session_id, processed, failed, total }
       → Frontend captura session_id y lo almacena
```

### 2. Componente ProcessingLogs se renderiza

```
ProcessingLogs → Recibe sessionId="a1b2c3d4"
              → Inicia polling cada 2 segundos
              → GET /api/v1/processing/logs?session_id=a1b2c3d4
              → Actualiza UI con nuevos logs
              → Auto-scroll al final si está habilitado
```

### 3. Usuario observa progreso en tiempo real

```
UI muestra:
[14:30:45] INFO  🚀 Iniciando Extracción de boletines - 02/01/2025
[14:30:45] INFO  Construyendo query: status=pending, limit=1000
[14:30:45] INFO  Filtro de fecha aplicado: 20250102
[14:30:45] INFO  Consultando base de datos...
[14:30:46] SUCCESS ✅ Encontrados 5 boletines para procesar
[14:30:46] INFO  📊 Procesando boletin_2025_001234.pdf (1/5 - 20.0%)
[14:30:47] INFO  Extrayendo texto de boletin_2025_001234.pdf...
[14:30:48] SUCCESS ✅ Completado: boletin_2025_001234.pdf
[14:30:48] INFO  📊 Procesando boletin_2025_001235.pdf (2/5 - 40.0%)
...
[14:31:02] INFO  Guardando cambios en la base de datos...
[14:31:03] SUCCESS ✅ Procesamiento finalizado: 5 exitosos, 0 fallidos
[14:31:03] SUCCESS ✅ Procesamiento completado exitosamente
```

---

## 🎨 UI/UX Features

### Controles Interactivos

1. **⏸️ Pausa/Reanudación**
   - Pausa el polling sin perder datos
   - Badge visual indica estado "En pausa"

2. **🔄 Refresh Manual**
   - Fuerza actualización inmediata
   - Útil cuando se detecta un cambio

3. **🗑️ Limpieza de Logs**
   - Elimina logs de la sesión actual
   - Útil para iniciar un nuevo proceso limpio

### Visualización

- **Monospace font** para mejor legibilidad
- **Zebra striping** (filas alternadas) para distinguir entradas
- **Badges de nivel** con iconos y colores
- **Timestamps** formateados en hora local
- **Contador** de entradas totales
- **ScrollArea** con overflow automático

---

## 🔧 Configuración

### Backend

**Buffer Size**: Por defecto 1000 logs en memoria
```python
processing_logger = ProcessingLogger(max_logs=1000)
```

**Session ID**: Generado con UUID (primeros 8 caracteres)
```python
session_id = str(uuid.uuid4())[:8]
```

### Frontend

**Polling Interval**: 2 segundos por defecto
```tsx
<ProcessingLogs refreshInterval={2000} />
```

**Auto-scroll**: Habilitado por defecto
```tsx
<ProcessingLogs autoScroll={true} />
```

---

## 📊 Performance Considerations

### Backend
- **Thread-safe**: Usa locks para operaciones concurrentes
- **Memory bounded**: Buffer limitado (LRU automatic con deque)
- **Session cleanup**: Limpieza manual disponible via API

### Frontend
- **Polling optimizado**: Solo cuando el componente está visible
- **Cleanup**: Limpia intervals en unmount
- **Pausa inteligente**: Usuario puede pausar para reducir carga

---

## 🐛 Debugging

### Ver logs en el servidor
```bash
# Backend logs incluyen session_id
tail -f watcher-monolith/backend/logs/app.log | grep "a1b2c3d4"
```

### Consultar logs via API
```bash
# Todos los logs
curl http://localhost:8001/api/v1/processing/logs

# Logs de una sesión específica
curl "http://localhost:8001/api/v1/processing/logs?session_id=a1b2c3d4"

# Ver sesiones activas
curl http://localhost:8001/api/v1/processing/logs/sessions
```

---

## ✅ Testing Manual

### 1. Iniciar el servidor
```bash
cd /Users/germanevangelisti/watcher-agent
make start
```

### 2. Navegar al Wizard
```
http://localhost:5173/wizard
```

### 3. Seleccionar fecha y iniciar extracción
- Seleccionar: Año 2025, Mes 01, Día 02
- Click "Iniciar Extracción"
- Observar logs en tiempo real

### 4. Verificar funcionalidad
- ✅ Logs aparecen en tiempo real
- ✅ Auto-scroll funciona
- ✅ Progreso actualizado (X/Y archivos)
- ✅ Estados de éxito/error correctos
- ✅ Controles de pausa/resume funcionan

---

## 🔮 Mejoras Futuras

1. **WebSocket en lugar de polling**
   - Conexión bidireccional
   - Push notifications desde servidor
   - Menor latencia

2. **Filtros avanzados**
   - Por nivel de log
   - Por rango de tiempo
   - Búsqueda de texto

3. **Exportación de logs**
   - Descargar como JSON
   - Descargar como TXT
   - Copiar al portapapeles

4. **Persistencia de logs**
   - Almacenar en base de datos
   - Historial de sesiones
   - Análisis de patrones

5. **Logs estructurados**
   - Metadata adicional
   - Trazabilidad de errores
   - Métricas de performance

---

## 📚 Referencias

- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [React Hooks: useEffect](https://react.dev/reference/react/useEffect)
- [Mantine UI: ScrollArea](https://mantine.dev/core/scroll-area/)
- [Python: collections.deque](https://docs.python.org/3/library/collections.html#collections.deque)

---

**Implementado por**: Sonnet 4.5 (Implementation Agent)  
**Documentado**: 2026-02-03

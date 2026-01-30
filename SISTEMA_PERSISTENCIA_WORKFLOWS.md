# 💾 Sistema de Persistencia de Workflows - MVP Robusto

## 🎉 Sistema Completado

Se ha implementado un **sistema completo de persistencia y modificación de datos** para workflows de agentes inteligentes.

---

## ✅ Características Implementadas

### 1. **Base de Datos SQLite**
- ✅ Tabla `agent_workflows` - Flujos completos con estado y métricas
- ✅ Tabla `agent_tasks` - Tareas individuales con resultados
- ✅ Tabla `workflow_logs` - Logs detallados de ejecución
- ✅ Índices optimizados para consultas rápidas
- ✅ Relaciones con CASCADE para integridad referencial

### 2. **Persistencia Automática**
- ✅ **Creación**: Workflows se guardan al crearlos
- ✅ **Ejecución**: Estados se actualizan en tiempo real
- ✅ **Tareas**: Resultados se persisten al completar
- ✅ **Logs**: Eventos importantes se registran automáticamente
- ✅ **Resultados finales**: Se guardan al completar el workflow

### 3. **API REST Completa**
- ✅ `GET /api/v1/workflows/history` - Lista workflows con filtros
- ✅ `GET /api/v1/workflows/history/{id}` - Detalle completo con tareas y logs
- ✅ `GET /api/v1/workflows/stats` - Estadísticas agregadas
- ✅ `GET /api/v1/workflows/export/{id}` - Exportar JSON o CSV
- ✅ `DELETE /api/v1/workflows/history/{id}` - Eliminar workflows

### 4. **UI de Historial**
- ✅ Página dedicada `/workflows/history`
- ✅ Tabla con todos los workflows ejecutados
- ✅ Filtros por estado y tipo
- ✅ Botón "Ver Historial" en Agent Dashboard
- ✅ Modal con detalles completos (tareas, logs, resultados)
- ✅ Exportación con un clic (JSON/CSV)

### 5. **Exportación de Datos**
- ✅ Formato JSON con estructura completa
- ✅ Formato CSV para análisis en Excel
- ✅ Descarga automática de archivos
- ✅ Nombres de archivo descriptivos

---

## 🚀 Cómo Usar

### **Ejecutar Workflows**

Los workflows se guardan automáticamente:

```typescript
// Frontend - Al iniciar cualquier acción rápida
startWorkflow('analyze_high_risk', { threshold: 50, limit: 20 })

// Backend - Automáticamente persiste:
// 1. Workflow en DB
// 2. Tareas asociadas
// 3. Logs iniciales
```

### **Ver Historial**

1. Ir a **Agent Dashboard** (`/agents`)
2. Click en botón **"Ver Historial"**
3. Filtra por estado o tipo
4. Click en 👁️ para ver detalles completos

### **Exportar Resultados**

**Opción A: Desde la tabla**
```
1. Click en 📥 (JSON) o 📥 (CSV)
2. Archivo se descarga automáticamente
```

**Opción B: Desde el detalle**
```
1. Abrir workflow (👁️)
2. Click en "Exportar JSON" o "Exportar CSV"
3. Archivo descargado: workflow_{id}.{format}
```

### **Consultar via API**

```bash
# Listar workflows
curl http://localhost:8001/api/v1/workflows/history

# Con filtros
curl "http://localhost:8001/api/v1/workflows/history?status=completed&limit=10"

# Detalle completo
curl http://localhost:8001/api/v1/workflows/history/{workflow_id}

# Estadísticas
curl http://localhost:8001/api/v1/workflows/stats?days=30

# Exportar
curl http://localhost:8001/api/v1/workflows/export/{workflow_id}?format=json
curl http://localhost:8001/api/v1/workflows/export/{workflow_id}?format=csv
```

---

## 📊 Estructura de Datos

### **Workflow Guardado**
```json
{
  "id": "uuid",
  "workflow_name": "analyze_high_risk_1732547890",
  "workflow_type": "analyze_high_risk",
  "status": "completed",
  "parameters": { "threshold": 50, "limit": 20 },
  "results": {
    "task_0_0": {
      "task_type": "analyze_high_risk",
      "status": "completed",
      "result": {
        "success": true,
        "statistics": { ... },
        "high_risk_documents": [ ... ]
      }
    }
  },
  "total_tasks": 1,
  "completed_tasks": 1,
  "failed_tasks": 0,
  "progress_percentage": 100.0,
  "created_at": "2025-11-25T10:30:00Z",
  "completed_at": "2025-11-25T10:30:15Z"
}
```

### **Tareas Guardadas**
```json
{
  "id": "workflow_uuid_0",
  "workflow_id": "workflow_uuid",
  "task_type": "analyze_high_risk",
  "agent_type": "anomaly_detection",
  "status": "completed",
  "parameters": { ... },
  "result": { ... },
  "created_at": "2025-11-25T10:30:00Z",
  "completed_at": "2025-11-25T10:30:15Z"
}
```

### **Logs Guardados**
```json
{
  "id": 1,
  "workflow_id": "workflow_uuid",
  "level": "info",
  "message": "Workflow creado: analyze_high_risk",
  "source": "orchestrator",
  "created_at": "2025-11-25T10:30:00Z"
}
```

---

## 🗄️ Base de Datos

### **Ubicación**
```
backend/sqlite.db
```

### **Tablas**
```sql
-- Workflows principales
agent_workflows (
  id, workflow_name, workflow_type, status,
  parameters, config, results, error_message,
  total_tasks, completed_tasks, failed_tasks, progress_percentage,
  created_at, started_at, completed_at, updated_at, created_by
)

-- Tareas individuales
agent_tasks (
  id, workflow_id, task_type, agent_type, priority, requires_approval,
  status, parameters, result, error_message,
  approval_status, approval_notes,
  created_at, started_at, completed_at
)

-- Logs de ejecución
workflow_logs (
  id, workflow_id, level, message, source, extra_data, created_at
)
```

### **Consultas SQL Útiles**

```sql
-- Workflows completados hoy
SELECT * FROM agent_workflows 
WHERE DATE(created_at) = DATE('now') AND status = 'completed';

-- Workflows con errores
SELECT * FROM agent_workflows WHERE status = 'failed';

-- Duración promedio
SELECT 
  AVG((julianday(completed_at) - julianday(created_at)) * 86400) as avg_seconds
FROM agent_workflows 
WHERE status = 'completed';

-- Logs de error
SELECT * FROM workflow_logs WHERE level = 'error';
```

---

## 🔧 Mantenimiento

### **Limpiar Logs Antiguos**

Puedes implementar limpieza automática:

```python
from app.db.workflow_crud import log_crud

# Eliminar logs de más de 30 días
db = next(get_sync_db())
deleted = log_crud.delete_old_logs(db, days=30)
print(f"Logs eliminados: {deleted}")
```

### **Backup de Base de Datos**

```bash
# Backup manual
cp backend/sqlite.db backend/sqlite.db.backup.$(date +%Y%m%d)

# Backup automatizado (cron)
0 2 * * * cp /path/to/sqlite.db /path/to/backups/sqlite.db.$(date +\%Y\%m\%d)
```

---

## 📈 Estadísticas Disponibles

La API `/api/v1/workflows/stats` proporciona:

- **Total de workflows** en período
- **Workflows activos** (en progreso)
- **Workflows completados**
- **Workflows fallidos**
- **Total de tareas ejecutadas**
- **Tiempo promedio de completitud**

---

## 🎯 Casos de Uso

### **1. Auditoría**
- Ver historial completo de análisis ejecutados
- Revisar logs de decisiones de agentes
- Verificar resultados pasados

### **2. Análisis de Performance**
- Duración de workflows por tipo
- Tasa de éxito/fallo
- Identificar cuellos de botella

### **3. Debugging**
- Ver logs detallados de workflows fallidos
- Identificar errores recurrentes
- Revisar parámetros que causaron problemas

### **4. Reportes**
- Exportar resultados para presentaciones
- Análisis en Excel (CSV)
- Compartir insights con equipo

---

## 🔐 Consideraciones de Seguridad

- ✅ Los workflows se guardan sin datos sensibles por defecto
- ✅ Solo se persisten parámetros y resultados estructurados
- ✅ Logs no contienen información personal identificable
- ⚠️ Para producción, considera agregar:
  - Encriptación de resultados sensibles
  - Control de acceso por usuario
  - Retención de datos con políticas de eliminación

---

## 🚀 Próximas Mejoras Posibles

1. **Dashboard de Estadísticas**
   - Gráficos de workflows por día/mes
   - Métricas de performance en tiempo real
   - Alertas de workflows fallidos

2. **Filtros Avanzados**
   - Búsqueda por rango de fechas
   - Filtro por duración
   - Búsqueda de texto en logs

3. **Comparación de Workflows**
   - Comparar resultados entre ejecuciones
   - Análisis de diferencias
   - Detectar degradación de performance

4. **Automatización**
   - Re-ejecutar workflows fallidos
   - Programar workflows recurrentes
   - Notificaciones por email

---

## ✅ Checklist de Verificación

- [x] Modelos de DB creados
- [x] Migración ejecutada exitosamente
- [x] Orchestrator persiste workflows
- [x] API REST completa
- [x] UI de historial funcionando
- [x] Exportación JSON/CSV
- [x] Filtros por estado y tipo
- [x] Modal de detalles completo
- [x] Logs detallados guardados
- [x] Botón de acceso en dashboard
- [x] Rutas de frontend configuradas

---

## 📞 Soporte

**Si encuentras problemas:**

1. **Logs del backend**: Check `watcher-monolith/backend/` logs
2. **Consola del navegador**: F12 → Console para errores frontend
3. **Base de datos**: Usa SQL directo para verificar datos

**Comandos útiles:**

```bash
# Ver workflows en DB
cd backend
python -c "from app.db.sync_session import get_sync_db; from app.db.models import AgentWorkflow; db = next(get_sync_db()); print([w.workflow_name for w in db.query(AgentWorkflow).all()])"

# Contar workflows
python -c "from app.db.sync_session import get_sync_db; from app.db.workflow_crud import workflow_crud; db = next(get_sync_db()); print(workflow_crud.count_workflows(db))"
```

---

## 🎉 ¡Sistema Listo para Producción!

El MVP robusto de persistencia está **100% funcional**:

✅ **Todos los workflows se guardan automáticamente**  
✅ **Historial completo consultable**  
✅ **Exportación de datos en múltiples formatos**  
✅ **UI intuitiva para exploración**  
✅ **API REST para integración**  

**¡Disfruta tu sistema de análisis con persistencia completa! 🚀**




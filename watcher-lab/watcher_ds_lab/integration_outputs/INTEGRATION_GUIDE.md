
# 🔗 GUÍA DE INTEGRACIÓN WATCHER DS LAB ↔ MONOLITH

## 📋 PASOS DE INTEGRACIÓN

### 1. BACKEND (FastAPI)

**a) Agregar endpoints de red flags:**
```bash
# Ubicación: /watcher-monolith/backend/app/api/v1/endpoints/watcher.py
# Agregar el código generado por create_enhanced_batch_endpoint()
```

**b) Configurar base de datos:**
```bash
cd /watcher-monolith/backend
sqlite3 sqlite.db < migration.sql
```

**c) Instalar dependencias adicionales:**
```bash
pip install pandas numpy scikit-learn
```

### 2. FRONTEND (React)

**a) Agregar componente RedFlagsViewer:**
```bash
# Crear archivo: /watcher-monolith/frontend/src/components/RedFlagsViewer.tsx
# Usar código generado por create_frontend_redflags_component()
```

**b) Actualizar AnalyzerPage:**
```bash
# Modificar: /watcher-monolith/frontend/src/pages/AnalyzerPage.tsx
# Usar código generado por create_enhanced_analyzer_page()
```

**c) Instalar dependencias:**
```bash
cd /watcher-monolith/frontend
npm install @tabler/icons-react
```

### 3. INTEGRACIÓN DE DATOS

**a) Sincronizar datasets:**
```python
from integrations.monolith_integration import MonolithIntegration

integration = MonolithIntegration()
sync_result = integration.sync_datasets_with_monolith()
```

**b) Configurar rutas de archivos:**
```python
# Actualizar paths en config/settings.py:
MONOLITH_PDF_PATH = "/Users/germanevangelisti/watcher-agent/watcher-monolith/backend/data/raw"
MONOLITH_PROCESSED_PATH = "/Users/germanevangelisti/watcher-agent/watcher-monolith/backend/data/processed"
```

## 🎯 FUNCIONALIDADES INTEGRADAS

### Red Flags en Tiempo Real
- ✅ Detección automática durante análisis
- ✅ Clasificación por severidad (CRÍTICO, ALTO, MEDIO, INFORMATIVO)
- ✅ Evidencia visual en PDFs
- ✅ Recomendaciones específicas

### Visualización Avanzada
- ✅ Componente React para mostrar red flags
- ✅ Modal con evidencia detallada
- ✅ Botón para abrir PDF en ubicación exacta
- ✅ Badges de severidad con iconos

### Persistencia de Datos
- ✅ Tabla red_flags en SQLite
- ✅ Coordenadas visuales en pdf_evidence
- ✅ Vistas optimizadas para consultas
- ✅ Índices para rendimiento

## 🚀 COMANDOS DE DESPLIEGUE

### Desarrollo
```bash
# Backend
cd /watcher-monolith/backend
uvicorn app.main:app --reload

# Frontend  
cd /watcher-monolith/frontend
npm run dev
```

### Producción
```bash
# Build frontend
cd /watcher-monolith/frontend
npm run build

# Deploy backend
cd /watcher-monolith/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📊 FLUJO DE USO

1. **Usuario sube PDF** en frontend
2. **Backend procesa** con análisis existente + DS Lab
3. **Red flags detectadas** automáticamente
4. **Resultado muestra** análisis tradicional + red flags
5. **Usuario puede ver** evidencia específica en PDF
6. **Click en "Ver en PDF"** abre documento en ubicación exacta

## 🎯 BENEFICIOS DE LA INTEGRACIÓN

### Para Auditores:
- ✅ **Priorización automática** de documentos críticos
- ✅ **Evidencia visual** directa en PDFs
- ✅ **Recomendaciones específicas** para cada irregularidad

### Para Desarrolladores:
- ✅ **API unificada** con capacidades ML
- ✅ **Componentes reutilizables** React
- ✅ **Base de datos estructurada** para red flags

### Para Ciudadanos:
- ✅ **Transparencia mejorada** con alertas automáticas
- ✅ **Acceso directo** a evidencia en documentos
- ✅ **Interfaz intuitiva** para consultar irregularidades

## 🔍 PRÓXIMOS PASOS

1. **Implementar autenticación** para red flags sensibles
2. **Dashboard ejecutivo** con métricas de red flags
3. **Alertas por email** para casos críticos
4. **API pública** para desarrolladores cívicos
5. **Integración con sistemas** gubernamentales oficiales

---

*Integración completada entre Watcher DS Lab v2.0 y Watcher Monolith* ✅

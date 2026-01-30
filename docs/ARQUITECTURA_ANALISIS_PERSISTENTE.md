# 🧪 Arquitectura de Análisis Persistente - Watcher DS Lab

## Objetivo
Sistema completo para analizar boletines oficiales, persistir resultados, versionar modelos y comparar análisis históricos.

## 1. 🗄️ Esquema de Base de Datos

### Tablas Principales

#### `boletin_documents`
Metadata de cada boletín descargado
```sql
CREATE TABLE boletin_documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    day INT NOT NULL,
    section INT NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    download_date TIMESTAMP DEFAULT NOW(),
    last_analyzed TIMESTAMP,
    analysis_status VARCHAR(50), -- 'pending', 'analyzing', 'completed', 'failed'
    num_pages INT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_boletin_date ON boletin_documents(year, month, day);
CREATE INDEX idx_boletin_status ON boletin_documents(analysis_status);
```

#### `analysis_configs`
Configuraciones y versiones de modelos
```sql
CREATE TABLE analysis_configs (
    id SERIAL PRIMARY KEY,
    config_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    parameters JSONB NOT NULL, -- Parámetros del análisis
    model_version VARCHAR(50),
    model_weights_path TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    UNIQUE(config_name, version)
);

-- Ejemplo de parameters JSONB:
{
    "transparency_thresholds": {
        "high_risk": 30,
        "medium_risk": 50,
        "low_risk": 70
    },
    "amount_thresholds": {
        "suspicious_amount": 10000000,
        "very_high": 50000000
    },
    "ml_models": {
        "random_forest": {"n_estimators": 100, "max_depth": 10},
        "isolation_forest": {"contamination": 0.1}
    },
    "nlp_config": {
        "min_entity_confidence": 0.8,
        "extract_amounts": true,
        "extract_beneficiaries": true
    }
}
```

#### `analysis_executions`
Ejecuciones de análisis
```sql
CREATE TABLE analysis_executions (
    id SERIAL PRIMARY KEY,
    execution_name VARCHAR(200),
    config_id INT REFERENCES analysis_configs(id),
    status VARCHAR(50), -- 'running', 'completed', 'failed', 'cancelled'
    start_date DATE,
    end_date DATE,
    total_documents INT,
    processed_documents INT,
    failed_documents INT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT,
    execution_metadata JSONB -- Logs, warnings, etc.
);

CREATE INDEX idx_execution_status ON analysis_executions(status);
CREATE INDEX idx_execution_dates ON analysis_executions(started_at, completed_at);
```

#### `analysis_results`
Resultados detallados por documento
```sql
CREATE TABLE analysis_results (
    id SERIAL PRIMARY KEY,
    document_id INT REFERENCES boletin_documents(id),
    execution_id INT REFERENCES analysis_executions(id),
    config_id INT REFERENCES analysis_configs(id),
    
    -- Scores y métricas
    transparency_score FLOAT,
    risk_level VARCHAR(20), -- 'high', 'medium', 'low'
    anomaly_score FLOAT,
    
    -- Entidades extraídas
    extracted_entities JSONB, -- {amounts: [], beneficiaries: [], contracts: []}
    
    -- Red Flags detectadas
    red_flags JSONB, -- [{type: 'high_amount', severity: 'high', description: '...'}]
    num_red_flags INT,
    
    -- Clasificaciones ML
    ml_predictions JSONB, -- {random_forest: 0.85, isolation_forest: 'anomaly'}
    
    -- Texto y contexto
    extracted_text_sample TEXT, -- Primeros 5000 chars
    processing_time_seconds FLOAT,
    
    analyzed_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(document_id, execution_id)
);

CREATE INDEX idx_results_document ON analysis_results(document_id);
CREATE INDEX idx_results_execution ON analysis_results(execution_id);
CREATE INDEX idx_results_risk ON analysis_results(risk_level);
CREATE INDEX idx_results_score ON analysis_results(transparency_score);
```

#### `red_flags`
Red flags individuales (para análisis detallado)
```sql
CREATE TABLE red_flags (
    id SERIAL PRIMARY KEY,
    result_id INT REFERENCES analysis_results(id),
    document_id INT REFERENCES boletin_documents(id),
    
    flag_type VARCHAR(100), -- 'HIGH_AMOUNT', 'MISSING_INFO', 'INCONSISTENT_DATA'
    severity VARCHAR(20), -- 'critical', 'high', 'medium', 'low'
    category VARCHAR(100), -- 'transparency', 'amounts', 'patterns', 'entities'
    
    title VARCHAR(255),
    description TEXT,
    evidence JSONB, -- Datos específicos que triggerearon la flag
    
    confidence_score FLOAT,
    page_number INT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_red_flags_document ON red_flags(document_id);
CREATE INDEX idx_red_flags_type ON red_flags(flag_type);
CREATE INDEX idx_red_flags_severity ON red_flags(severity);
```

#### `analysis_comparisons`
Comparaciones entre ejecuciones
```sql
CREATE TABLE analysis_comparisons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200),
    execution_a_id INT REFERENCES analysis_executions(id),
    execution_b_id INT REFERENCES analysis_executions(id),
    
    -- Métricas de comparación
    comparison_metrics JSONB,
    -- {
    --   "score_diff_avg": 5.2,
    --   "new_red_flags": 15,
    --   "resolved_flags": 8,
    --   "documents_changed_risk": 12
    -- }
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 2. 🔄 Flujo de Trabajo

### Paso 1: Registrar Documentos Descargados
```python
# Al descargar un boletín, registrarlo en la BD
POST /api/v1/dslab/documents/register
{
    "filename": "20250501_1_Secc.pdf",
    "year": 2025,
    "month": 5,
    "day": 1,
    "section": 1,
    "file_path": "/boletines/2025/05/20250501_1_Secc.pdf",
    "file_size_bytes": 2048576
}
```

### Paso 2: Crear Configuración de Análisis
```python
POST /api/v1/dslab/configs
{
    "config_name": "watcher_v1",
    "version": "1.0.0",
    "description": "Configuración inicial con modelos entrenados en agosto",
    "parameters": {
        "transparency_thresholds": {"high_risk": 30, "medium_risk": 50},
        "ml_models": {"random_forest": {"n_estimators": 100}}
    }
}
```

### Paso 3: Ejecutar Análisis
```python
POST /api/v1/dslab/analysis/start
{
    "execution_name": "Análisis Mayo-Julio 2025",
    "config_id": 1,
    "start_date": "2025-05-01",
    "end_date": "2025-07-31",
    "sections": [1, 2, 3, 4, 5]
}
```

### Paso 4: Visualizar Resultados
```python
GET /api/v1/dslab/analysis/executions/{execution_id}/results
GET /api/v1/dslab/analysis/executions/{execution_id}/summary
GET /api/v1/dslab/documents/{document_id}/history  # Ver todos los análisis de un doc
```

### Paso 5: Comparar Ejecuciones
```python
POST /api/v1/dslab/analysis/compare
{
    "name": "Comparación v1.0 vs v1.1",
    "execution_a_id": 1,
    "execution_b_id": 2
}

GET /api/v1/dslab/analysis/comparisons/{comparison_id}
```

## 3. 🎨 UI Components

### Dashboard Principal
- **Estado de Análisis**: Grid con progreso por mes/día
- **Métricas Agregadas**: Score promedio, red flags totales, documentos analizados
- **Timeline**: Histórico de ejecuciones

### Página de Configuración
- **Gestor de Versiones**: Crear/editar/activar configuraciones
- **Parámetros Ajustables**: Thresholds, modelos ML, NLP settings
- **Validación**: Simular análisis con config antes de ejecutar

### Página de Ejecución
- **Selector de Rango**: Fechas, secciones
- **Selector de Config**: Elegir versión a usar
- **Monitor en Tiempo Real**: Progreso, errores, tiempo estimado

### Página de Resultados
- **Vista Agregada**: Métricas por mes, distribución de scores
- **Vista Detallada por Documento**: Drill-down a red flags específicas
- **Filtros**: Por riesgo, score, tipo de flag, fecha

### Página de Comparación
- **Selector de Ejecuciones**: A vs B
- **Diff Visual**: Qué cambió, nuevos flags, scores diferentes
- **Exportar**: CSV/PDF con comparación detallada

## 4. 🔧 APIs Propuestas

### Documentos
```
POST   /api/v1/dslab/documents/register         # Registrar documento
GET    /api/v1/dslab/documents                  # Listar documentos
GET    /api/v1/dslab/documents/{id}             # Detalle de documento
GET    /api/v1/dslab/documents/{id}/history     # Histórico de análisis
PUT    /api/v1/dslab/documents/{id}/status      # Actualizar estado
GET    /api/v1/dslab/documents/stats            # Estadísticas generales
```

### Configuraciones
```
POST   /api/v1/dslab/configs                    # Crear config
GET    /api/v1/dslab/configs                    # Listar configs
GET    /api/v1/dslab/configs/{id}               # Detalle config
PUT    /api/v1/dslab/configs/{id}               # Actualizar config
DELETE /api/v1/dslab/configs/{id}               # Eliminar config
POST   /api/v1/dslab/configs/{id}/activate      # Activar config
```

### Ejecuciones
```
POST   /api/v1/dslab/analysis/start             # Iniciar análisis
GET    /api/v1/dslab/analysis/executions        # Listar ejecuciones
GET    /api/v1/dslab/analysis/executions/{id}   # Detalle ejecución
GET    /api/v1/dslab/analysis/executions/{id}/progress  # Progreso en tiempo real
POST   /api/v1/dslab/analysis/executions/{id}/cancel    # Cancelar
GET    /api/v1/dslab/analysis/executions/{id}/results   # Resultados
GET    /api/v1/dslab/analysis/executions/{id}/summary   # Resumen
GET    /api/v1/dslab/analysis/executions/{id}/red-flags # Red flags
```

### Resultados
```
GET    /api/v1/dslab/results                    # Listar resultados (filtrable)
GET    /api/v1/dslab/results/{id}               # Detalle resultado
GET    /api/v1/dslab/red-flags                  # Listar red flags (filtrable)
GET    /api/v1/dslab/red-flags/stats            # Estadísticas de red flags
```

### Comparaciones
```
POST   /api/v1/dslab/analysis/compare           # Crear comparación
GET    /api/v1/dslab/analysis/comparisons       # Listar comparaciones
GET    /api/v1/dslab/analysis/comparisons/{id}  # Detalle comparación
DELETE /api/v1/dslab/analysis/comparisons/{id}  # Eliminar comparación
```

## 5. 🚀 Plan de Implementación

### Fase 1: Base de Datos (1-2 días)
- [x] Diseño del esquema
- [ ] Migraciones de Alembic
- [ ] Modelos SQLAlchemy
- [ ] Scripts de seed/test data

### Fase 2: Backend APIs (2-3 días)
- [ ] Endpoints de documentos
- [ ] Endpoints de configuraciones
- [ ] Endpoints de ejecuciones
- [ ] Sistema de background tasks para análisis
- [ ] Integración con código DS Lab existente

### Fase 3: Frontend UI (3-4 días)
- [ ] Dashboard de estado
- [ ] Gestor de configuraciones
- [ ] Monitor de ejecución
- [ ] Visualización de resultados
- [ ] Comparador de versiones

### Fase 4: Integración DS Lab (2-3 días)
- [ ] Adaptar código de análisis existente
- [ ] Wrapper para guardar en BD
- [ ] Sistema de versionado de modelos
- [ ] Exportación de resultados

## 6. 📊 Beneficios

✅ **Trazabilidad**: Saber qué versión de modelo analizó cada documento
✅ **Experimentación**: Probar parámetros sin perder resultados anteriores
✅ **Auditoría**: Histórico completo de análisis y decisiones
✅ **Optimización**: Comparar configuraciones para mejorar detección
✅ **Reproducibilidad**: Re-ejecutar análisis con misma config
✅ **Escalabilidad**: Procesar grandes volúmenes con tracking

## 7. 🎯 Casos de Uso

### Caso 1: Ajustar Thresholds
1. Ejecutar análisis con config v1.0
2. Revisar resultados, notar muchos falsos positivos
3. Crear config v1.1 con thresholds ajustados
4. Ejecutar análisis sobre mismos documentos
5. Comparar v1.0 vs v1.1
6. Activar v1.1 si mejora

### Caso 2: Análisis Mensual Programado
1. Descargar boletines del mes nuevo
2. Ejecutar análisis con config activa
3. Dashboard muestra automáticamente nuevos resultados
4. Alertas sobre red flags críticas

### Caso 3: Auditoría Histórica
1. Seleccionar documento específico
2. Ver todos los análisis ejecutados
3. Comparar scores y flags entre versiones
4. Exportar timeline completo

### Caso 4: Mejora de Modelo
1. Entrenar nuevo modelo con más datos
2. Crear config v2.0 con nuevo modelo
3. Ejecutar en subset de test
4. Comparar métricas con v1.x
5. Desplegar v2.0 si mejora

## 8. 🔐 Consideraciones

- **Performance**: Indexar campos clave (fecha, score, risk_level)
- **Storage**: JSONB para flexibilidad en entidades/flags
- **Backup**: Snapshots regulares de análisis históricos
- **Limpieza**: Política de retención (ej: mantener últimas 5 ejecuciones)
- **Seguridad**: Roles para editar configs vs solo visualizar


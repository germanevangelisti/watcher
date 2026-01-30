# 📋 Plan de Organización y Análisis - Watcher DS Lab

## 🎯 Objetivo
Preparar la infraestructura de datos para análisis con Watcher DS Lab y posterior visualización en la UI.

---

## 📊 Fase 1: Organización del Filesystem (HOY)

### Estado Actual
```
/boletines/
├── 20250801_1_Secc.pdf
├── 20250801_2_Secc.pdf
├── ... (207 archivos mezclados)
```

### Estado Objetivo
```
/boletines/
├── 2025/
│   ├── 08/
│   │   ├── 20250801_1_Secc.pdf
│   │   ├── 20250801_2_Secc.pdf
│   │   ├── ... (por día y sección)
│   └── 09/
│       └── ... (archivos futuros)
└── 2026/
    └── ...
```

### Beneficios
✅ **Sin duplicados**: El sistema verifica antes de descargar
✅ **Fácil navegación**: Año/mes claros
✅ **Escalable**: Crece organizadamente
✅ **DS Lab ready**: Estructura consistente para análisis
✅ **Backup simple**: Un directorio por mes

---

## 🔧 Ejecución de Reorganización

### Opción 1: Script Bash (Rápido - 2 minutos)
```bash
cd /Users/germanevangelisti/watcher-agent
./scripts/quick_organize.sh
```

**Qué hace:**
- ✅ Crea estructura 2024-2026 con meses 01-12
- ✅ Mueve archivos a año/mes correspondiente
- ✅ Verifica si ya existen (no sobrescribe)
- ✅ Muestra resumen de organización

### Opción 2: Script Python (Completo - 5 minutos)
```bash
cd /Users/germanevangelisti/watcher-agent
python3 scripts/reorganize_boletines.py
```

**Qué hace:**
- ✅ Análisis detallado de archivos
- ✅ Backup automático antes de mover
- ✅ Dry-run para verificar
- ✅ Verificación de integridad
- ✅ Reporte completo de estadísticas

---

## 📥 Fase 2: Descarga Completa del Año

### Objetivo
Tener todos los boletines de 2025 disponibles para análisis masivo.

### Estrategia de Descarga

#### Opción A: Mes por mes (Recomendada)
```python
# Via UI o API
POST /api/v1/downloader/download/start
{
    "start_date": "2025-09-01",
    "end_date": "2025-09-30",
    "sections": [1, 2, 3, 4, 5],
    "skip_weekends": true
}
```

**Ventajas:**
- ✅ Control granular
- ✅ Menos riesgo de timeout
- ✅ Fácil reanudar si falla

#### Opción B: Año completo
```python
POST /api/v1/downloader/download/start
{
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "sections": [1, 2, 3, 4, 5],
    "skip_weekends": true
}
```

**Tiempo estimado:**
- 250 días hábiles × 5 secciones = 1,250 archivos
- ~1.5 segundos por archivo (con rate limiting)
- Total: ~31 minutos

### Calendario de Descarga Sugerido

| Mes | Días Hábiles | Archivos | Tiempo Est. | Estado |
|-----|--------------|----------|-------------|--------|
| Enero | 21 | 105 | 2.6 min | ⏳ Pendiente |
| Febrero | 20 | 100 | 2.5 min | ⏳ Pendiente |
| Marzo | 21 | 105 | 2.6 min | ⏳ Pendiente |
| Abril | 22 | 110 | 2.7 min | ⏳ Pendiente |
| Mayo | 21 | 105 | 2.6 min | ⏳ Pendiente |
| Junio | 21 | 105 | 2.6 min | ⏳ Pendiente |
| Julio | 23 | 115 | 2.9 min | ⏳ Pendiente |
| Agosto | 21 | 105 | 2.6 min | ✅ **COMPLETO** |
| Septiembre | 22 | 110 | 2.7 min | ⏳ Pendiente |
| Octubre | 23 | 115 | 2.9 min | ⏳ Pendiente |
| Noviembre | 20 | 100 | 2.5 min | ⏳ Pendiente |
| Diciembre | 20 | 100 | 2.5 min | ⏳ Pendiente |
| **TOTAL** | **255** | **1,275** | **~32 min** | **8% completo** |

---

## 🔬 Fase 3: Análisis con Watcher DS Lab

### Pre-requisitos
✅ Archivos organizados en `/boletines/YYYY/MM/`
✅ PDFs descargados y verificados
✅ Espacio suficiente (~1 GB para dataset)

### Pipeline de Análisis

```python
# 1. Extracción de texto desde PDFs
cd /Users/germanevangelisti/watcher-agent/watcher-lab/watcher_ds_lab
python src/extractors/pdf_text_extractor.py \
    --input /Users/germanevangelisti/watcher-agent/boletines/2025 \
    --output data/raw/texto_boletines_2025.csv

# 2. Procesamiento y feature extraction
python src/processors/text_processor.py \
    --input data/raw/texto_boletines_2025.csv \
    --output data/processed/features_2025.csv

# 3. Detección de anomalías con modelos ML
python src/agents/detection_agent.py \
    --input data/processed/features_2025.csv \
    --output reports/red_flags_2025.json

# 4. Scoring de transparencia
python src/analyzers/transparency_scorer.py \
    --input data/processed/features_2025.csv \
    --output reports/transparency_scores_2025.csv
```

### Métricas Esperadas (basado en agosto 2025)

| Métrica | Agosto | Año Completo (Proyección) |
|---------|--------|---------------------------|
| Documentos | 99 | 1,188 |
| Red Flags | 102 | 1,224 |
| Casos Críticos | 2 | 24 |
| Score Prom. Transp. | 44.6/100 | ~45/100 |
| Anomalías ML | 10 | 120 |

### Tipos de Red Flags Detectados

1. **TRANSPARENCIA_CRITICA**
   - Score < 30
   - Falta de información clave
   - Entidades no especificadas

2. **ANOMALIA_ML**
   - Patrones fuera de lo normal
   - Isolation Forest detecta outliers
   - K-Means identifica clusters raros

3. **INCONSISTENCIA_CLASIFICACION**
   - Categoría predicha ≠ categoría real
   - Random Forest con baja confianza
   - Requiere revisión manual

4. **MONTO_IRREGULAR**
   - Montos fuera de rango esperado
   - Desvíos > 2 sigma
   - Incrementos anuales > 100%

---

## 📊 Fase 4: Integración con UI

### Base de Datos - Modelo Actualizado

```sql
-- Tabla principal de boletines
CREATE TABLE boletines (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE,
    year INTEGER,
    month INTEGER,
    day INTEGER,
    section INTEGER,
    file_path TEXT,  -- ruta relativa: 2025/08/20250801_1_Secc.pdf
    file_size_mb FLOAT,
    status VARCHAR(50),  -- pending, downloaded, analyzed, failed
    downloaded_at TIMESTAMP,
    analyzed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de red flags (integración DS Lab)
CREATE TABLE red_flags (
    id SERIAL PRIMARY KEY,
    boletin_id INTEGER REFERENCES boletines(id),
    tipo VARCHAR(100),  -- TRANSPARENCIA_CRITICA, ANOMALIA_ML, etc.
    severidad VARCHAR(20),  -- CRITICO, ALTO, MEDIO, INFORMATIVO
    descripcion TEXT,
    confidence FLOAT,  -- 0.0 - 1.0
    metadata JSONB,  -- datos adicionales del análisis
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de scoring de transparencia
CREATE TABLE transparency_scores (
    id SERIAL PRIMARY KEY,
    boletin_id INTEGER REFERENCES boletines(id),
    score INTEGER,  -- 0-100
    num_amounts INTEGER,
    num_entities INTEGER,
    num_keywords INTEGER,
    risk_level VARCHAR(20),  -- ALTO, MEDIO, BAJO
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices para búsquedas eficientes
CREATE INDEX idx_boletines_date ON boletines(year, month, day);
CREATE INDEX idx_boletines_status ON boletines(status);
CREATE INDEX idx_redflags_severity ON red_flags(severidad);
CREATE INDEX idx_redflags_boletin ON red_flags(boletin_id);
CREATE INDEX idx_transparency_score ON transparency_scores(score);
```

### API Endpoints Nuevos

```python
# GET /api/v1/dslab/analyze/{filename}
# Ejecuta análisis DS Lab para un boletín específico

# GET /api/v1/dslab/red-flags
# Lista todas las red flags detectadas con filtros

# GET /api/v1/dslab/transparency-scores
# Obtiene scores de transparencia con estadísticas

# GET /api/v1/dslab/dashboard-stats
# Dashboard principal con métricas agregadas
```

### Componentes UI Actualizados

#### 1. **Calendario de Boletines** (Ya existe)
```typescript
// Agregar indicadores de análisis
interface CalendarDay {
    sections_analyzed: number[];  // [1, 2, 3]
    has_red_flags: boolean;
    critical_flags_count: number;
    avg_transparency_score: number;
}
```

#### 2. **Dashboard DS Lab** (Mejorado)
```typescript
// Métricas en tiempo real
- Total boletines analizados
- Red flags detectadas (críticas/altas/medias)
- Score promedio de transparencia
- Top 10 casos críticos
- Gráficos de tendencias mensuales
```

#### 3. **Vista de Detalle de Boletín**
```typescript
// Nueva página: /dslab/boletin/{filename}
- Información del boletín
- Lista de red flags detectadas
- Score de transparencia con desglose
- PDF viewer con highlights en red flags
- Botones de acción (revisar, aprobar, reportar)
```

---

## 📅 Cronograma de Implementación

### Semana 1: Organización y Descarga
- **Día 1**: Reorganizar filesystem ✅ (hoy)
- **Día 2-3**: Descargar enero-abril (420 archivos)
- **Día 4-5**: Descargar mayo-agosto (420 archivos)
- **Día 6-7**: Descargar septiembre-diciembre (435 archivos)

### Semana 2: Análisis DS Lab
- **Día 8-9**: Extracción de texto de todos los PDFs
- **Día 10-11**: Feature extraction y procesamiento
- **Día 12**: Detección de red flags
- **Día 13**: Scoring de transparencia
- **Día 14**: Validación manual de casos críticos

### Semana 3: Integración con UI
- **Día 15-16**: Actualizar modelos de base de datos
- **Día 17-18**: Crear endpoints API nuevos
- **Día 19-20**: Actualizar componentes de UI
- **Día 21**: Testing end-to-end

### Semana 4: Refinamiento y Documentación
- **Día 22-23**: Ajustar modelos ML basado en feedback
- **Día 24-25**: Mejorar visualizaciones
- **Día 26-27**: Documentar hallazgos
- **Día 28**: Demo y presentación de resultados

---

## 🎯 Entregables Finales

### Datos
1. ✅ **1,275 boletines** organizados y descargados
2. ✅ **Dataset completo** con features extraídos
3. ✅ **Red flags detectadas** con severidad y confianza
4. ✅ **Scores de transparencia** para cada documento

### Análisis
1. ✅ **Reporte de anomalías** (top 50 casos críticos)
2. ✅ **Tendencias mensuales** de transparencia
3. ✅ **Distribución por sección** de irregularidades
4. ✅ **Recomendaciones** de acción

### Tecnología
1. ✅ **UI funcional** con visualización de red flags
2. ✅ **API completa** para consultas
3. ✅ **Modelos ML** entrenados y optimizados
4. ✅ **Documentación** de arquitectura

---

## 🚀 Comenzar AHORA

### Paso 1: Reorganizar (5 minutos)
```bash
cd /Users/germanevangelisti/watcher-agent
./scripts/quick_organize.sh
```

### Paso 2: Verificar
```bash
# Ver estructura creada
tree -L 3 boletines/

# Contar archivos por mes
find boletines/ -name "*.pdf" | cut -d'/' -f2-3 | sort | uniq -c
```

### Paso 3: Descargar siguiente mes (desde UI)
1. Abrir http://localhost:5173/dslab
2. Tab "Descargar Boletines"
3. Fecha inicio: 2025-09-01
4. Fecha fin: 2025-09-30
5. Iniciar descarga

---

## 💡 Notas Importantes

### Prevención de Duplicados
El sistema actual YA previene duplicados:
```python
# En download_single_boletin()
if filepath.exists():
    file_size = filepath.stat().st_size
    if file_size > 10240:  # >10KB = archivo válido
        return {"status": "exists"}  # ✅ No descarga de nuevo
```

### Espacio en Disco
- Actual: 159 MB (207 archivos)
- Año completo: ~950 MB (1,275 archivos)
- Con análisis: +300 MB (datasets)
- **Total necesario**: ~1.5 GB

### Performance
- Descarga: ~1.5 seg/archivo
- Extracción texto: ~2 seg/PDF
- Análisis DS Lab: ~0.1 seg/documento
- **Total para año**: ~1.5 horas

---

¿Listo para comenzar con la reorganización? 🚀


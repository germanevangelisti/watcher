# 🧪 Watcher DS Lab - Guía de Uso Completa

## 📋 Índice
1. [Inicio Rápido](#inicio-rápido)
2. [Configuración Inicial](#configuración-inicial)
3. [Ejecutar Análisis](#ejecutar-análisis)
4. [Interpretar Resultados](#interpretar-resultados)
5. [Versionado de Modelos](#versionado-de-modelos)
6. [Casos de Uso Avanzados](#casos-de-uso-avanzados)
7. [API Reference](#api-reference)
8. [Troubleshooting](#troubleshooting)

---

## 🚀 Inicio Rápido

### Prerequisitos
```bash
# Backend debe estar corriendo
cd watcher-monolith/backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Verificar que esté disponible
curl http://localhost:8001/api/v1/dslab/documents/stats
```

### Setup Inicial (Una Sola Vez)
```bash
cd watcher-monolith/backend

# 1. Crear tablas
python scripts/create_dslab_tables.py

# 2. Registrar boletines existentes
python scripts/register_existing_boletines.py

# 3. Crear configuración inicial
python scripts/create_initial_config.py
```

### Tu Primer Análisis
```bash
# Ejecutar análisis de prueba (10 documentos)
python scripts/run_test_analysis.py
```

---

## ⚙️ Configuración Inicial

### 1. Estructura de Configuración

Una configuración contiene todos los parámetros para el análisis:

```python
{
    "config_name": "watcher_baseline",
    "version": "1.0.0",
    "description": "Config inicial...",
    "parameters": {
        "transparency_thresholds": {
            "high_risk": 30,    # Score < 30 = Alto riesgo
            "medium_risk": 50,  # Score < 50 = Riesgo medio
            "low_risk": 70      # Score >= 70 = Bajo riesgo
        },
        "amount_thresholds": {
            "very_high": 50000000,     # $50M
            "high": 10000000,          # $10M
            "suspicious_pattern_amount": 999999
        },
        "red_flag_rules": {
            "HIGH_AMOUNT": {
                "enabled": true,
                "threshold": 50000000,
                "severity": "high"
            },
            "MISSING_BENEFICIARY": {
                "enabled": true,
                "severity": "medium"
            },
            "LOW_TRANSPARENCY_SCORE": {
                "enabled": true,
                "threshold": 30,
                "severity": "high"
            }
        },
        "nlp_config": {
            "extract_amounts": true,
            "extract_beneficiaries": true,
            "min_entity_confidence": 0.7
        }
    }
}
```

### 2. Crear Nueva Configuración

```bash
curl -X POST http://localhost:8001/api/v1/dslab/configs \
  -H "Content-Type: application/json" \
  -d '{
    "config_name": "watcher_strict",
    "version": "1.0.0",
    "description": "Versión más estricta con thresholds bajos",
    "parameters": {
        "transparency_thresholds": {
            "high_risk": 25,
            "medium_risk": 45,
            "low_risk": 65
        }
    }
  }'
```

### 3. Clonar y Modificar Configuración

```bash
# Clonar config existente
curl -X POST http://localhost:8001/api/v1/dslab/configs/1/clone \
  -H "Content-Type: application/json" \
  -d '{
    "new_version": "1.1.0",
    "description": "Ajuste basado en feedback de enero"
  }'

# Editar parámetros de la nueva versión
curl -X PUT http://localhost:8001/api/v1/dslab/configs/2 \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
        "transparency_thresholds": {
            "high_risk": 28,
            "medium_risk": 48,
            "low_risk": 68
        }
    }
  }'

# Activar nueva versión
curl -X POST http://localhost:8001/api/v1/dslab/configs/2/activate
```

---

## 📊 Ejecutar Análisis

### Análisis por Rango de Fechas

```bash
curl -X POST http://localhost:8001/api/v1/dslab/analysis/executions \
  -H "Content-Type: application/json" \
  -d '{
    "execution_name": "Análisis Enero 2025",
    "config_id": 1,
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "sections": [1, 2, 3, 4, 5]
  }'

# Respuesta:
{
    "id": 1,
    "execution_name": "Análisis Enero 2025",
    "status": "pending",
    "total_documents": 108,
    ...
}
```

### Monitorear Progreso

```bash
# Ver progreso en tiempo real
curl http://localhost:8001/api/v1/dslab/analysis/executions/1/progress

# Respuesta:
{
    "execution_id": 1,
    "status": "running",
    "total_documents": 108,
    "processed_documents": 45,
    "failed_documents": 2,
    "progress_percentage": 41.67,
    "estimated_time_remaining_seconds": 120,
    "current_document": "20250115_2_Secc.pdf"
}
```

### Script de Monitoreo Automático

```python
import time
import requests

def monitor_execution(execution_id):
    while True:
        response = requests.get(
            f"http://localhost:8001/api/v1/dslab/analysis/executions/{execution_id}/progress"
        )
        progress = response.json()
        
        status = progress['status']
        processed = progress['processed_documents']
        total = progress['total_documents']
        
        print(f"Progreso: {processed}/{total} ({progress['progress_percentage']:.1f}%)")
        
        if status in ['completed', 'failed', 'cancelled']:
            break
        
        time.sleep(3)
    
    print(f"Estado final: {status}")

# Usar
monitor_execution(1)
```

---

## 🔍 Interpretar Resultados

### Ver Resumen de Ejecución

```bash
curl http://localhost:8001/api/v1/dslab/analysis/executions/1/summary

# Respuesta:
{
    "execution_id": 1,
    "execution_name": "Análisis Enero 2025",
    "config_name": "watcher_baseline",
    "config_version": "1.0.0",
    "status": "completed",
    "total_documents": 108,
    "processed_documents": 106,
    "failed_documents": 2,
    "avg_transparency_score": 52.3,
    "risk_distribution": {
        "high": 15,
        "medium": 45,
        "low": 46
    },
    "total_red_flags": 87,
    "red_flags_by_severity": {
        "critical": 5,
        "high": 20,
        "medium": 42,
        "low": 20
    },
    "duration_seconds": 245.8
}
```

### Filtrar Resultados de Alto Riesgo

```bash
# Solo documentos de alto riesgo
curl "http://localhost:8001/api/v1/dslab/analysis/results?execution_id=1&risk_level=high"

# Documentos con más de 3 red flags
curl "http://localhost:8001/api/v1/dslab/analysis/results?execution_id=1&min_red_flags=3"

# Score de transparencia menor a 30
curl "http://localhost:8001/api/v1/dslab/analysis/results?execution_id=1&max_score=30"
```

### Ver Detalle de un Documento

```bash
curl http://localhost:8001/api/v1/dslab/analysis/results/1/full

# Respuesta incluye:
{
    "result": {
        "transparency_score": 28.5,
        "risk_level": "high",
        "num_red_flags": 5,
        "extracted_entities": {
            "amounts": [
                {
                    "raw_text": "$75,000,000",
                    "numeric_value": 75000000
                }
            ],
            "beneficiaries": ["EMPRESA XYZ S.A."],
            ...
        },
        ...
    },
    "document": {
        "filename": "20250115_2_Secc.pdf",
        "year": 2025,
        "month": 1,
        "day": 15,
        ...
    },
    "red_flags": [
        {
            "type": "HIGH_AMOUNT",
            "severity": "high",
            "title": "Monto muy alto detectado: $75,000,000",
            "description": "...",
            "evidence": {...}
        }
    ]
}
```

### Estadísticas de Red Flags

```bash
curl http://localhost:8001/api/v1/dslab/red-flags/stats?execution_id=1

# Respuesta:
{
    "total_flags": 87,
    "by_severity": {
        "critical": 5,
        "high": 20,
        "medium": 42,
        "low": 20
    },
    "by_type": {
        "HIGH_AMOUNT": 12,
        "MISSING_BENEFICIARY": 25,
        "LOW_TRANSPARENCY_SCORE": 15,
        "SUSPICIOUS_AMOUNT_PATTERN": 8
    },
    "by_category": {
        "amounts": 20,
        "transparency": 40,
        "patterns": 15,
        "entities": 12
    },
    "top_documents": [
        {
            "document_id": 45,
            "filename": "20250115_2_Secc.pdf",
            "flag_count": 8
        },
        ...
    ]
}
```

---

## 🔄 Versionado de Modelos

### Flujo de Mejora Continua

```
1. Ejecutar con v1.0
   ↓
2. Analizar resultados
   ↓
3. Identificar ajustes necesarios
   ↓
4. Clonar config → v1.1
   ↓
5. Ejecutar con v1.1 (mismos docs)
   ↓
6. Comparar v1.0 vs v1.1
   ↓
7. Si mejora → Activar v1.1
   ↓
8. Repetir
```

### Ejemplo Completo

```bash
# 1. Ejecutar análisis inicial
curl -X POST .../analysis/executions \
  -d '{"config_id": 1, "start_date": "2025-01-01", "end_date": "2025-01-31"}'
# execution_id: 1

# 2. Revisar resultados
curl .../analysis/executions/1/summary
# Detectamos: Demasiados falsos positivos en HIGH_AMOUNT

# 3. Crear nueva versión con threshold más alto
curl -X POST .../configs/1/clone -d '{"new_version": "1.1.0"}'
# config_id: 2

curl -X PUT .../configs/2 \
  -d '{
    "parameters": {
      "amount_thresholds": {
        "very_high": 100000000  # $100M en lugar de $50M
      }
    }
  }'

# 4. Ejecutar análisis con nueva config (mismos documentos)
curl -X POST .../analysis/executions \
  -d '{"config_id": 2, "start_date": "2025-01-01", "end_date": "2025-01-31"}'
# execution_id: 2

# 5. Comparar resultados
curl -X POST .../analysis/comparisons \
  -d '{
    "name": "v1.0 vs v1.1 - Threshold Adjustment",
    "execution_a_id": 1,
    "execution_b_id": 2
  }'

curl .../analysis/comparisons/1
# Ver diferencias, mejoras, etc.

# 6. Si v1.1 es mejor, activar
curl -X POST .../configs/2/activate
```

---

## 🎯 Casos de Uso Avanzados

### Análisis Mensual Programado

```python
import schedule
import requests

def analyze_previous_month():
    """Analizar el mes anterior automáticamente"""
    from datetime import date, timedelta
    
    today = date.today()
    first_day_prev_month = date(today.year, today.month - 1, 1)
    last_day_prev_month = date(today.year, today.month, 1) - timedelta(days=1)
    
    response = requests.post(
        "http://localhost:8001/api/v1/dslab/analysis/executions",
        json={
            "execution_name": f"Análisis Automático {first_day_prev_month.strftime('%B %Y')}",
            "config_id": 1,  # Config activa
            "start_date": str(first_day_prev_month),
            "end_date": str(last_day_prev_month),
            "sections": [1, 2, 3, 4, 5]
        }
    )
    
    print(f"Análisis iniciado: {response.json()}")

# Programar para el día 2 de cada mes
schedule.every().month.at("02:00").do(analyze_previous_month)
```

### Auditoría de Documento Específico

```bash
# Ver todos los análisis históricos de un documento
curl http://localhost:8001/api/v1/dslab/documents/45/history

# Respuesta:
{
    "document": {
        "filename": "20250115_2_Secc.pdf",
        ...
    },
    "total_analyses": 3,
    "analyses": [
        {
            "execution_id": 3,
            "config_id": 3,
            "transparency_score": 32.5,
            "risk_level": "high",
            "analyzed_at": "2025-11-17T15:30:00"
        },
        {
            "execution_id": 2,
            "config_id": 2,
            "transparency_score": 28.0,
            "risk_level": "high",
            "analyzed_at": "2025-11-15T10:20:00"
        },
        ...
    ]
}
```

### Exportar Resultados

```python
import pandas as pd
import requests

def export_high_risk_documents(execution_id):
    """Exportar documentos de alto riesgo a CSV"""
    response = requests.get(
        f"http://localhost:8001/api/v1/dslab/analysis/results",
        params={
            "execution_id": execution_id,
            "risk_level": "high",
            "limit": 1000
        }
    )
    
    results = response.json()['results']
    
    # Crear DataFrame
    data = []
    for r in results:
        data.append({
            "Documento": r['document']['filename'],
            "Fecha": f"{r['document']['year']}-{r['document']['month']:02d}-{r['document']['day']:02d}",
            "Score Transparencia": r['transparency_score'],
            "Nivel Riesgo": r['risk_level'],
            "Red Flags": r['num_red_flags'],
            "Score Anomalía": r['anomaly_score']
        })
    
    df = pd.DataFrame(data)
    df.to_csv(f"high_risk_execution_{execution_id}.csv", index=False)
    print(f"Exportados {len(df)} documentos de alto riesgo")

export_high_risk_documents(1)
```

---

## 📚 API Reference

### Documentos

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/dslab/documents` | GET | Listar documentos |
| `/dslab/documents` | POST | Registrar documento |
| `/dslab/documents/{id}` | GET | Detalle de documento |
| `/dslab/documents/{id}/history` | GET | Histórico de análisis |
| `/dslab/documents/stats` | GET | Estadísticas |

### Configuraciones

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/dslab/configs` | GET/POST | Listar/crear configs |
| `/dslab/configs/{id}` | GET/PUT/DELETE | CRUD config |
| `/dslab/configs/{id}/clone` | POST | Clonar config |
| `/dslab/configs/{id}/activate` | POST | Activar versión |

### Ejecuciones

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/dslab/analysis/executions` | GET/POST | Listar/crear ejecuciones |
| `/dslab/analysis/executions/{id}` | GET | Detalle |
| `/dslab/analysis/executions/{id}/progress` | GET | Progreso en tiempo real |
| `/dslab/analysis/executions/{id}/summary` | GET | Resumen de resultados |
| `/dslab/analysis/executions/{id}/cancel` | POST | Cancelar |

### Resultados

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/dslab/analysis/results` | GET | Listar resultados (filtrable) |
| `/dslab/analysis/results/{id}/full` | GET | Resultado completo |
| `/dslab/red-flags` | GET | Listar red flags |
| `/dslab/red-flags/stats` | GET | Estadísticas |

### Comparaciones

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/dslab/analysis/comparisons` | GET/POST | Listar/crear comparaciones |
| `/dslab/analysis/comparisons/{id}` | GET/DELETE | Detalle/eliminar |

---

## 🔧 Troubleshooting

### Backend no inicia

```bash
# Verificar puerto
lsof -i :8001

# Reiniciar
cd watcher-monolith/backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Análisis muy lento

- Reducir `max_workers` en config
- Analizar en batches más pequeños
- Verificar tamaño de PDFs

### Demasiados falsos positivos

- Ajustar `transparency_thresholds`
- Aumentar `amount_thresholds`
- Desactivar reglas específicas en `red_flag_rules`

### No se extraen entidades

- Verificar que `pdfplumber` esté instalado
- Revisar calidad de PDFs
- Ajustar `min_entity_confidence`

---

## 📖 Recursos Adicionales

- `/docs/DSLAB_SISTEMA_IMPLEMENTADO.md` - Overview técnico
- `/docs/ARQUITECTURA_ANALISIS_PERSISTENTE.md` - Arquitectura detallada
- `/watcher-lab/watcher_ds_lab/PROJECT_SUMMARY.md` - DS Lab original

---

**Última actualización:** 2025-11-17
**Versión del sistema:** 1.0.0


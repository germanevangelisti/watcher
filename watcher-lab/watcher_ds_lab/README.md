# 🔍 WATCHER DATA SCIENCE LAB

## 🎯 Objetivo del Proyecto
Sistema escalable de análisis y auditoría de boletines oficiales de Córdoba (Argentina) para detectar irregularidades fiscales, actos administrativos sospechosos y gastos públicos no justificados mediante Machine Learning y análisis automatizado.

## 🏗️ Arquitectura del Sistema

```
watcher_ds_lab/
├── src/                    # Código fuente modular
│   ├── extractors/         # Extracción de entidades y features
│   ├── models/            # Modelos ML y pipeline
│   ├── validators/        # Sistema de validación y auditoría
│   ├── analyzers/         # Análisis de patrones y anomalías
│   └── agents/            # Sistema agentic para detección automática
├── models/                # Modelos ML serializados
├── data/                  # Datasets y archivos procesados
├── reports/               # Reportes y visualizaciones
├── scripts/               # Scripts de ejecución y utilidades
├── tests/                 # Tests unitarios
└── config/                # Configuraciones del sistema
```

## 📊 Datos Disponibles
- **Dataset principal**: 99 boletines agosto 2025 (29 features)
- **Casos críticos**: 16 documentos riesgo ALTO identificados
- **Modelos entrenados**: Random Forest, Isolation Forest, K-Means
- **Score transparencia**: Métrica 0-100 para cada documento

## 🧠 Contexto del Desarrollo
Evolución desde notebook Jupyter (4,282 líneas) hacia sistema modular y escalable con capacidades agentic para detección automática de red flags en transparencia gubernamental.

## 🚀 Próximos Pasos
1. Modularización de clases principales del notebook
2. Análisis de falsos positivos en clasificación de riesgo
3. Implementación de nuevas features para mayor precisión
4. Sistema agentic para detección automática de patrones sospechosos
5. Pipeline de validación continua y calibración de modelos

## 🔧 Instalación
```bash
cd watcher_ds_lab
pip install -r ../requirements.txt
python scripts/setup.py
```

## 📈 Métricas Actuales
- **Tasa procesamiento**: 100% (99/99 documentos)
- **Score transparencia promedio**: 44.6/100
- **Casos riesgo alto**: 16 (16.2%)
- **Anomalías detectadas**: 10 (10.1%)

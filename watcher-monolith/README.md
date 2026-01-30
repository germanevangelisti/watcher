# Watcher Monolith

Sistema de análisis inteligente de boletines oficiales para detectar posibles irregularidades en gastos, contrataciones y actos administrativos.

## 🆕 Novedades - DS Lab Manager

**Sistema completo de análisis persistente**: Gestión, descarga y análisis automatizado de boletines oficiales con interfaz visual intuitiva y resultados históricos.

### Características Principales

#### 📥 Gestión de Boletines
- 📅 **Calendario Visual**: Ve qué boletines están descargados con código de colores
- 📥 **Descarga Batch**: Descarga meses completos con progreso en tiempo real
- 📊 **Vista Anual**: Resumen de cobertura por mes con métricas visuales
- 🔍 **Validación Automática**: Detecta días hábiles sin boletines

#### 🔬 Análisis Persistente
- ⚙️ **Configuraciones Versionadas**: Múltiples configuraciones de modelos y parámetros
- ▶️ **Ejecución en Tiempo Real**: Monitor de progreso con logs y estimaciones
- 📊 **Resultados Históricos**: Almacenamiento de análisis para comparaciones
- 🚨 **Red Flags Detalladas**: Clasificación por severidad y categoría
- 📈 **Análisis Comparativo**: Compara resultados entre ejecuciones

#### 🎨 Interfaces Disponibles
- **DS Lab Manager** (`/dslab`): Calendario, descargas y vista general
- **Ejecutar Análisis** (`/dslab/analysis`): Monitor de ejecución con logs en tiempo real

**Documentación**:
- 📖 [Guía de Uso Completa](./docs/DSLAB_GUIA_USO_COMPLETA.md)
- 🎨 [UI de Análisis](./docs/DSLAB_UI_ANALISIS_GUIA.md)
- 🔧 [Troubleshooting](./docs/DSLAB_TROUBLESHOOTING.md)
- 🏗️ [Sistema Implementado](../SISTEMA_DSLAB_COMPLETO.md)

---

## Estructura del Proyecto

```
watcher-monolith/
├── backend/              # Backend FastAPI
│   ├── app/
│   │   ├── api/         # Endpoints API
│   │   │   └── v1/
│   │   │       └── endpoints/
│   │   │           ├── downloader.py 🆕        # Gestión de descargas
│   │   │           ├── dslab_documents.py 🆕  # Metadata de documentos
│   │   │           ├── dslab_configs.py 🆕    # Configuraciones de análisis
│   │   │           ├── dslab_executions.py 🆕 # Ejecuciones de análisis
│   │   │           ├── dslab_results.py 🆕    # Resultados y comparaciones
│   │   │           ├── boletines.py
│   │   │           ├── alertas.py
│   │   │           └── ...
│   │   ├── core/        # Configuración central
│   │   ├── services/    # Lógica de negocio
│   │   │   └── dslab_analyzer.py 🆕    # Motor de análisis
│   │   ├── db/
│   │   │   ├── models.py 🆕             # Modelos DS Lab
│   │   │   └── sync_session.py 🆕       # Sesión síncrona
│   │   └── schemas/
│   │       └── dslab.py 🆕              # Schemas Pydantic
│   ├── scripts/         # Utilidades
│   │   ├── create_dslab_tables.py 🆕
│   │   ├── register_existing_boletines.py 🆕
│   │   └── create_initial_config.py 🆕
│   ├── tests/           # Tests
│   └── requirements.txt # Dependencias Python
├── frontend/            # Frontend React
│   ├── src/
│   │   ├── components/  # Componentes React
│   │   │   └── dslab/ 🆕         # DS Lab Components
│   │   │       ├── BoletinesCalendar.tsx
│   │   │       ├── DownloadManager.tsx
│   │   │       ├── DSLabDashboard.tsx
│   │   │       └── YearOverview.tsx 🆕
│   │   ├── pages/      # Páginas/rutas
│   │   │   ├── DSLabManagerPage.tsx 🆕
│   │   │   └── DSLabAnalysisPage.tsx 🆕
│   │   └── services/   # Servicios API
│   └── package.json    # Dependencias Node.js
└── docs/               # Documentación
    ├── DSLAB_MANAGER_GUIDE.md 🆕
    ├── DSLAB_IMPLEMENTATION_SUMMARY.md 🆕
    ├── DSLAB_UI_ANALISIS_GUIA.md 🆕
    ├── DSLAB_GUIA_USO_COMPLETA.md 🆕
    └── DSLAB_TROUBLESHOOTING.md 🆕
```

## Requisitos

### Backend
- Python 3.8+
- FastAPI
- OpenAI API Key

### Frontend
- Node.js 16+
- React 18
- Vite

## Configuración

1. Backend:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Frontend:
   ```bash
   cd frontend
   npm install
   ```

3. Variables de entorno:
   Crear archivo `.env` en `/backend`:
   ```env
   OPENAI_API_KEY=tu-api-key
   MAX_RETRIES=3
   MAX_FRAGMENT_SIZE=2000
   ```

## Ejecución

1. Backend:
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8001
   ```
   API docs: http://localhost:8001/docs

2. Frontend:
   ```bash
   cd frontend
   npm run dev
   ```
   Web app: http://localhost:3001

## 🚀 Quick Start - DS Lab

### Primera Configuración (Solo una vez)

```bash
cd backend

# 1. Crear tablas DS Lab
python scripts/create_dslab_tables.py

# 2. Registrar documentos existentes
python scripts/register_existing_boletines.py

# 3. Crear configuración baseline
python scripts/create_initial_config.py
```

### Uso Diario

#### Opción 1: Interfaz Web (Recomendado)
1. Accede a http://localhost:3001/dslab
2. Usa el calendario para ver cobertura
3. Descarga meses faltantes desde la pestaña "Descargas"
4. Ve a http://localhost:3001/dslab/analysis para ejecutar análisis

#### Opción 2: Scripts Python
```bash
# Descargar meses específicos
python scripts/download_months_2025.py  # Edita para configurar meses

# Ejecutar análisis de prueba
python scripts/run_test_analysis.py
```

### Verificar Estado del Sistema

```bash
# Estado de documentos
cd backend
sqlite3 sqlite.db "SELECT COUNT(*) FROM boletin_documents;"

# Configuraciones disponibles
sqlite3 sqlite.db "SELECT id, config_name, version, is_active FROM analysis_configs;"

# Últimas ejecuciones
sqlite3 sqlite.db "SELECT id, execution_name, status, processed_documents, total_documents FROM analysis_executions ORDER BY id DESC LIMIT 5;"
```

### Troubleshooting

Si encuentras errores:
```bash
# Recrear base de datos
cd backend
mv sqlite.db sqlite.db.backup
python scripts/create_dslab_tables.py
python scripts/register_existing_boletines.py
python scripts/create_initial_config.py
```

📖 **Guía detallada**: [DSLAB_TROUBLESHOOTING.md](./docs/DSLAB_TROUBLESHOOTING.md)

---

## Características

### Sistema Principal
- ✅ Análisis de texto y archivos
- ✅ Interfaz moderna con Mantine UI
- ✅ API REST documentada
- ✅ Procesamiento asíncrono
- ✅ Manejo de errores robusto
- ✅ Configuración flexible

### DS Lab Manager 🆕
- ✅ Descarga automatizada de boletines con batch por mes
- ✅ Calendario visual interactivo con vista anual
- ✅ Progreso en tiempo real con polling
- ✅ Dashboard de análisis y estadísticas
- ✅ Sistema de análisis persistente con versiones
- ✅ Ejecución de análisis con monitor en tiempo real
- ✅ Detección de red flags con clasificación por severidad
- ✅ Resultados históricos y comparaciones

## Páginas Principales

| Ruta | Descripción |
|------|-------------|
| `/` | Dashboard principal |
| `/alertas` | Gestión de alertas |
| `/actos` | Listado de actos administrativos |
| `/presupuesto` | Análisis presupuestario |
| `/boletines` | Estado de procesamiento de boletines |
| `/dslab` 🆕 | **DS Lab Manager** - Calendario, descargas y vista general |
| `/dslab/analysis` 🆕 | **Ejecutar Análisis** - Monitor en tiempo real con logs |
| `/analyzer` | Analizador de documentos |

## API Endpoints

### DS Lab Manager 🆕

#### Gestión de Descargas
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/downloader/download/start` | POST | Inicia descarga de boletines |
| `/api/v1/downloader/download/status/{task_id}` | GET | Progreso de descarga |
| `/api/v1/downloader/calendar` | GET | Calendario de disponibilidad |
| `/api/v1/downloader/download/summary` | GET | Resumen de descargas |

#### Gestión de Documentos
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/dslab/documents` | POST, GET | Crear/listar documentos |
| `/api/v1/dslab/documents/{id}` | GET, PUT | Ver/editar documento |
| `/api/v1/dslab/documents/batch-register` | POST | Registro en lote |
| `/api/v1/dslab/documents/stats` | GET | Estadísticas de documentos |

#### Configuraciones de Análisis
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/dslab/configs` | POST, GET | Crear/listar configuraciones |
| `/api/v1/dslab/configs/{id}` | GET, PUT, DELETE | Ver/editar/eliminar config |
| `/api/v1/dslab/configs/{id}/activate` | POST | Activar configuración |
| `/api/v1/dslab/configs/{id}/clone` | POST | Clonar configuración |

#### Ejecuciones de Análisis
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/dslab/analysis/executions` | POST, GET | Iniciar/listar ejecuciones |
| `/api/v1/dslab/analysis/executions/{id}` | GET | Ver ejecución |
| `/api/v1/dslab/analysis/executions/{id}/progress` | GET | Progreso en tiempo real |
| `/api/v1/dslab/analysis/executions/{id}/summary` | GET | Resumen de resultados |
| `/api/v1/dslab/analysis/executions/{id}/cancel` | POST | Cancelar ejecución |

#### Resultados y Comparaciones
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/dslab/analysis/results` | GET | Listar resultados |
| `/api/v1/dslab/analysis/results/{id}` | GET | Ver resultado detallado |
| `/api/v1/dslab/analysis/results/summary` | GET | Resumen agregado |
| `/api/v1/dslab/analysis/redflags` | GET | Listar red flags |
| `/api/v1/dslab/analysis/comparisons` | POST, GET | Crear/listar comparaciones |

Ver documentación completa en: http://localhost:8001/docs

## Guías de Uso

### Descargar Boletines con DS Lab Manager

1. Accede a http://localhost:3001/dslab
2. Click en tab "Descargar Boletines"
3. Selecciona rango de fechas (ejemplo: 01/09/2025 - 30/09/2025)
4. Elige secciones (1-5)
5. Click "Iniciar Descarga"
6. Observa progreso en tiempo real
7. Revisa calendario actualizado

Para más detalles: [Guía Completa DS Lab Manager](./docs/DSLAB_MANAGER_GUIDE.md)

## Integración con Watcher DS Lab

El sistema está preparado para integrar con el **Watcher DS Lab** para análisis automático de irregularidades:

- 🔬 Detección de red flags
- 📊 Scoring de transparencia
- 🤖 Machine Learning para anomalías
- 📈 Análisis predictivo

## Testing

### Backend
```bash
cd backend
pytest
```

### Frontend
```bash
cd frontend
npm test
```

## Documentación Adicional

- [Guía DS Lab Manager](./docs/DSLAB_MANAGER_GUIDE.md)
- [Resumen de Implementación](./docs/DSLAB_IMPLEMENTATION_SUMMARY.md)
- [API Documentation](http://localhost:8001/docs)

## Contribuir

1. Fork el proyecto
2. Crea tu feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto es parte de Watcher Project - Sistema de vigilancia de transparencia gubernamental.

---

**Desarrollado con ❤️ para la transparencia pública**

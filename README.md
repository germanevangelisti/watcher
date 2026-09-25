# 🏛️ Watcher Agent - Sistema de Monitoreo de Boletines Oficiales

**Sistema inteligente de vigilancia y análisis automatizado de boletines oficiales de la Provincia de Córdoba, Argentina.**

[![Estado](https://img.shields.io/badge/Estado-Activo-success)]()
[![Versión](https://img.shields.io/badge/Versión-MVP_v1.1-blue)]()
[![Arquitectura](https://img.shields.io/badge/Arquitectura-Async-orange)]()
[![Sprint Actual](https://img.shields.io/badge/Sprint-3-green)]()

---

## 📋 Tabla de Contenidos

- [Descripción General](#-descripción-general)
- [Características Principales](#-características-principales)
- [Arquitectura](#-arquitectura)
- [Quick Start](#-quick-start)
- [Desarrollo](#-desarrollo)
- [Estado del Proyecto](#-estado-del-proyecto)
- [Documentación](#-documentación)
- [Equipo](#-equipo)

---

## 🎯 Descripción General

Watcher Agent es un sistema de análisis automatizado que:

- **Descarga y procesa** boletines oficiales de la Provincia de Córdoba
- **Extrae información** de actos administrativos, licitaciones, decretos y resoluciones
- **Analiza con IA** el contenido para detectar irregularidades y patrones
- **Organiza por jurisdicción** (Provincia, Capital, Municipalidades, Comunas)
- **Genera alertas** sobre posibles irregularidades o eventos de interés público
- **Visualiza datos** en dashboards interactivos con mapas y gráficos

### Problema que Resuelve

Los boletines oficiales contienen información crítica sobre decisiones gubernamentales, pero:
- Son documentos extensos y técnicos (100-300 páginas diarias)
- Requieren análisis manual exhaustivo
- La información relevante está dispersa
- Es difícil detectar patrones o irregularidades

**Watcher Agent automatiza este proceso**, permitiendo el monitoreo ciudadano efectivo de las acciones gubernamentales.

---

## ✨ Características Principales

### 1. **Sincronización Automática**
- ✅ Descarga automática de boletines oficiales
- ✅ Sincronización "al día" con scheduler configurable
- ✅ Procesamiento batch de archivos históricos
- ✅ **300+ boletines** procesados (2024-2026)

### 2. **Organización Jurisdiccional**
- ✅ **26 jurisdicciones** cargadas con datos geográficos
  - 1 Provincia (Córdoba)
  - 1 Capital (Ciudad de Córdoba)
  - 20 Municipalidades principales
  - 4 Comunas representativas
- ✅ Jerarquía visual clara con colores e iconos
- ✅ Filtros y búsqueda por jurisdicción
- ✅ Vista de detalle con estadísticas

### 3. **Análisis Inteligente con IA**
- ✅ Procesamiento de lenguaje natural (GPT-4)
- ✅ Extracción de entidades (organismos, montos, personas)
- ✅ Clasificación por categoría de riesgo
- ✅ Detección de patrones sospechosos
- ✅ Generación de alertas automáticas

### 4. **Dashboard Interactivo**
- ✅ Visualización de estadísticas en tiempo real
- ✅ Sistema de agentes IA especializados
- ✅ Historial de análisis y workflows
- ✅ Alertas y notificaciones
- 🚧 Mapa interactivo (próximamente)

### 5. **API REST Completa**
- ✅ **30+ endpoints** documentados
- ✅ Boletines, análisis, alertas, presupuesto
- ✅ Jurisdicciones, estadísticas, búsquedas
- ✅ Workflows y ejecuciones de agentes

### 6. **Sistema de Logs en Tiempo Real** 🆕
- ✅ Logging centralizado con `ProcessingLogger`
- ✅ API endpoints para consultar logs (`/api/v1/processing/logs`)
- ✅ Componente React con auto-scroll y controles
- ✅ Tracking de sesiones de procesamiento
- ✅ Integración en wizard de procesamiento

### 7. **Wizard de Procesamiento** 🆕
- ✅ Interfaz paso a paso (Extracción → Procesamiento → Resultados)
- ✅ Prevención de reprocesamiento de boletines
- ✅ Filtros por fecha (año, mes, día)
- ✅ Indicadores de progreso en tiempo real
- ✅ Estadísticas detalladas por etapa

### 8. **Testing Automatizado** 🆕
- ✅ Módulo completo en `tests/test_complete_workflow.py`
- ✅ Validación de flujo completo (5 etapas)
- ✅ Script ejecutable: `./tests/run_test.sh`
- ✅ Generación de reportes JSON
- ✅ Indicadores de progreso detallados

---

## 🏗️ Arquitectura

### Stack Tecnológico

**Backend:**
- Python 3.11+
- FastAPI (API REST async)
- SQLAlchemy 2.0 (ORM async)
- SQLite + aiosqlite (Base de datos async)
- Google Vertex AI (text-embedding-004)
- ChromaDB (Vector database)
- LangGraph + LangChain (Sistema agéntico)
- APScheduler (Tareas programadas)

**Frontend:**
- React 18
- TypeScript
- Mantine UI
- React Router
- Vite

**Data Science:**
- Jupyter Notebooks
- pandas, numpy
- scikit-learn
- Isolation Forest (detección de anomalías)

### Estructura del Proyecto (MVP v1.1)

```
watcher-agent/
├── watcher-backend/           # Backend consolidado
│   ├── app/
│   │   ├── api/v1/endpoints/  # Endpoints REST
│   │   ├── services/          # Lógica de negocio
│   │   │   ├── document_processor.py
│   │   │   ├── chunking_service.py
│   │   │   ├── embedding_service.py (Google)
│   │   │   ├── retrieval_service.py
│   │   │   └── llm_provider.py
│   │   ├── db/                # Modelos y CRUD (async)
│   │   ├── core/              # Config y utilidades
│   │   └── adapters/          # Extractores PDF/Word
│   ├── agents/                # Sistema agéntico (LangGraph)
│   │   ├── orchestrator/
│   │   ├── document_intelligence/
│   │   ├── insight_reporting/
│   │   └── tools/             # Tools async (DB, análisis)
│   ├── tests/                 # Suite de tests completa
│   ├── scripts/               # Scripts de utilidad
│   │   ├── dev.sh
│   │   └── test.sh
│   ├── migrations/            # Migraciones SQL
│   └── sqlite.db              # Base de datos
│
├── watcher-frontend/          # React frontend (v2 - shadcn/ui + TanStack)
│   ├── src/
│   │   ├── pages/             # Páginas principales (10 pages)
│   │   ├── components/        # UI primitives + feature components
│   │   ├── lib/               # API hooks, stores, WebSocket, utils
│   │   └── types/             # TypeScript definitions
│   └── dist/                  # Build de producción
│
├── watcher-frontend-legacy/   # React frontend v1 (Mantine - deprecated)
│
├── watcher-lab/               # Notebooks y experimentos
│   └── watcher_ds_lab/        # Módulo Python DS
│
├── boletines/                 # PDFs descargados (git-ignored)
│
├── docs/                      # Documentación
│   └── architecture/          # Legacy docs
│
├── Makefile                   # Comandos unificados
├── pytest.ini                 # Config de tests
├── AGENTS.md                  # Contrato de agentes IA
└── README.md                  # Este archivo
```

### Arquitectura de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  React + TypeScript + Mantine UI                            │
│  - Dashboard  - Jurisdicciones  - Documentos  - Agentes     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/WebSocket
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND API (FastAPI)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Sync        │  │ Jurisdicciones│  │  Agentes IA  │      │
│  │  Service     │  │  Service      │  │  Workflows   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  PDF         │  │  Watcher     │  │  Analysis    │      │
│  │  Processor   │  │  Service     │  │  Service     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   CAPA DE DATOS                              │
│  ┌──────────────────────┐    ┌──────────────────────┐       │
│  │  SQLite Database     │    │  OpenAI API (GPT-4)  │       │
│  │  - boletines         │    │  - Análisis de texto │       │
│  │  - jurisdicciones    │    │  - Extracción NER    │       │
│  │  - analisis          │    │  - Clasificación     │       │
│  │  - alertas           │    └──────────────────────┘       │
│  │  - workflows         │                                    │
│  └──────────────────────┘                                    │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  FUENTES EXTERNAS                            │
│  - Boletín Oficial de Córdoba                               │
│  - Datos abiertos del gobierno                              │
│  - APIs públicas                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisitos

- Python 3.11+
- Node.js 18+
- npm o yarn
- (Opcional) OpenAI API Key

### Instalación

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd watcher-agent

# 2. Instalar todas las dependencias
make install
# o manualmente:
# cd watcher-backend && pip install -r requirements.txt
# cd watcher-frontend && npm install

# 3. Configurar variables de entorno (opcional)
cp watcher-backend/.env.example watcher-backend/.env
cp watcher-frontend/.env.example watcher-frontend/.env
# Editar .env y agregar API keys si están disponibles

# 4. Iniciar servicios
make start-backend   # Terminal 1
make start-frontend  # Terminal 2
```

### Acceso

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8001

### Demo salida MVP (M6)

Checklist canónico (≤10 pasos): [knowledgebase/vision/mvp-m6-checklist.md](knowledgebase/vision/mvp-m6-checklist.md). Alcance: [knowledgebase/vision/mvp.md](knowledgebase/vision/mvp.md).

- **API Docs:** http://localhost:8001/docs

### Comandos Disponibles

```bash
make help            # Ver todos los comandos disponibles
make install         # Instalar dependencias
make start           # Iniciar servidores de desarrollo
make test            # Ejecutar tests
make lint            # Ejecutar linters
make build           # Build para producción
make clean           # Limpiar artefactos

# Scripts alternativos
./watcher-backend/scripts/dev.sh     # Iniciar desarrollo con logs
./watcher-backend/scripts/test.sh    # Ejecutar suite de tests
```

---

## 💻 Desarrollo

### Flujo de Trabajo

Este proyecto sigue un modelo de **desarrollo asistido por IA**:

- **Opus 4.5**: Planificación, arquitectura, revisión
- **Sonnet 4.5**: Implementación, testing, documentación
- **Humanos**: Dirección, validación, decisiones estratégicas

Ver [AGENTS.md](AGENTS.md) para detalles del contrato de agentes.

### Estructura de Tickets

Los tickets siguen el formato: `S{sprint}-{número}: {Título}`

Ejemplo: `S0-001: Create AGENTS.md`

### Estándares de Código

**Python:**
- PEP 8
- Type hints
- Docstrings
- Max 100 caracteres por línea
- Linter: ruff

**TypeScript/React:**
- ESLint
- Functional components + hooks
- Props tipadas
- Componentes reutilizables

### Pre-commit Hooks

```bash
# Instalar hooks
pip install pre-commit
pre-commit install

# Ejecutar manualmente
pre-commit run --all-files
```

### Testing

```bash
# Test completo del workflow
./watcher-backend/tests/run_test.sh 20250101

# Backend (unitarios)
cd watcher-backend
pytest

# Frontend
cd watcher-frontend
npm run test -- --run

# Todos
make test
```

### Notas Técnicas (MVP v1.1)

**Refactor Completado:**
- ✅ **Async Migration**: Todo el stack de base de datos migrado a SQLAlchemy 2.0 async
  - `DatabaseTools` → async methods
  - `AnalysisTools` → async methods
  - `AgentOrchestrator` → async persistence
  - Agents → usan `AsyncSession` con `AsyncSessionLocal()`
- ✅ **Estructura Reorganizada**:
  - `watcher-monolith/backend/` → `watcher-backend/`
  - `watcher-monolith/frontend/` → `watcher-frontend-legacy/`
  - `watcher-ui-v2/` → `watcher-frontend/` (v2 con shadcn/ui + TanStack)
  - `tests/` y `scripts/` consolidados en `watcher-backend/`
  - `docs/` reorganizado con `architecture/` subdirectorio
- ✅ **UI v2 Refactor Completado**:
  - Stack: Vite 7 + React 19 + shadcn/ui + TanStack Router + TanStack Query + Zustand
  - 10 pages, 11 feature components, 20+ API hooks, 3 stores, 11 routes
  - Dark mode minimalist design, real-time WebSocket pipeline monitoring
  - Production build: ~260KB gzip total
- ✅ **Eliminación de Legacy Code**:
  - Removidos 30+ archivos obsoletos (.bak, scripts de ejemplo, docs redundantes)
  - Limpiado código legacy de servicios deprecated
  - Actualizada toda la configuración (Makefile, pytest.ini, CI/CD)

**Correcciones Aplicadas (anteriores):**
- ✅ **Pydantic Warnings**: Agregado `model_config = ConfigDict(protected_namespaces=())` en schemas de DSLab para permitir campos `model_version` y `model_weights_path`
- ✅ **WebSocket**: Deshabilitado en frontend (sistema usa polling HTTP que es más simple y suficiente)
- ✅ **307 Redirects & 500 Errors**: Dual decorators (`@router.get("")` + `@router.get("/")`) en endpoints `/boletines` y `/analisis` para soportar ambas versiones (con/sin trailing slash) + manejo robusto con `hasattr()` checks
- ✅ **Agentes con Datos Reales**: Implementados `Document Intelligence`, `Anomaly Detection` e `Insight Reporting` agents con lógica real que consulta boletines extraídos de la DB y guarda análisis
- ✅ **Estados de Boletines**: Clarificado flujo: `pending` (descargado) → `completed` (texto extraído) → análisis se guarda en tabla `analisis` sin cambiar status del boletín
- ✅ **Wizard Corregido**: UI muestra correctamente pendientes vs extraídos usando nuevo endpoint `/api/v1/boletines/stats-wizard`
- ✅ **Logs Limpios**: Backend inicia sin warnings molestos

**Sistema de Actualización Actual:**
- Polling HTTP cada 2-3 segundos para actualizaciones en tiempo real
- Más estable y compatible que WebSocket
- Ideal para el volumen actual de usuarios

---

## 📊 Estado del Proyecto

### Sprint 0: Tooling & Repo Contract ✅

- [x] AGENTS.md (Contrato de agentes)
- [x] Makefile (Comandos unificados)
- [x] .env setup + graceful startup
- [x] Helper scripts (dev.sh, test.sh)
- [x] Pre-commit config
- [x] CI workflow (GitHub Actions)

**Fecha:** 2 de febrero de 2026

### Sprint 1: Feature "Sync to Today" ✅

- [x] Sincronización automática de boletines
- [x] Scheduler configurable (diario/semanal)
- [x] UI para configuración y monitoreo
- [x] Estado persistente en base de datos
- [x] Procesamiento batch mejorado
- [x] Rate limiting y simulación humana

**Fecha:** 3 de febrero de 2026  
**Boletines procesados:** 300+

### Sprint 2: Rediseño Jurisdiccional ✅

#### FASE 1: Base de Datos (Completada)
- [x] Modelo `Jurisdiccion` con datos geográficos
- [x] Modelo `MencionJurisdiccional`
- [x] Actualización modelo `Boletin` (fuente, jurisdiccion_id)
- [x] Migración SQL con 26 jurisdicciones iniciales
- [x] Asociación de 300 boletines a Provincia de Córdoba

#### FASE 2: API y UI (Completada)
- [x] **6 endpoints** de jurisdicciones:
  - `GET /jurisdicciones/` - Listar con filtros
  - `GET /jurisdicciones/stats` - Estadísticas
  - `GET /jurisdicciones/{id}` - Detalle
  - `GET /jurisdicciones/{id}/boletines` - Boletines
  - `GET /jurisdicciones/cerca/{lat}/{lng}` - Búsqueda geográfica
  - `GET /jurisdicciones/tipos/disponibles` - Tipos
- [x] **3 páginas** de UI:
  - `/jurisdicciones` - Dashboard principal
  - `/jurisdicciones/:id` - Vista de detalle
  - Integración en `/documentos`
- [x] **3 componentes** reutilizables:
  - `JurisdiccionSelector`
  - `JurisdiccionBadge`
  - `JurisdiccionStatsCard`

**Fecha:** 3 de febrero de 2026  
**Jurisdicciones:** 26 (1 provincia, 1 capital, 20 municipios, 4 comunas)

#### FASE 3: Extracción de Menciones 🚧 (60% Completado)

**Objetivo:** Identificar menciones jurisdiccionales en el texto de boletines provinciales.

**Tareas Backend:**
- [x] Implementar extractor NLP para menciones (`MencionExtractor`)
- [x] Servicio de procesamiento de boletines (`MencionProcessor`)
- [x] Clasificar tipo de mención (8 tipos: decreto, resolución, etc.)
- [x] Integración con extracción de PDF
- [x] 5 Endpoints API REST (`/menciones/`)
- [x] Almacenamiento en tabla `menciones_jurisdiccionales`

**Tareas Frontend:**
- [ ] Página de menciones (`/menciones`)
- [ ] Tab "Menciones" en detalle de jurisdicción
- [ ] Tab "Menciones" en detalle de boletín
- [ ] Componentes de visualización
- [ ] Estadísticas y filtros

**Estado:** Backend completo y funcional. UI pendiente.

#### FASE 4: Mapa Interactivo 📅 (Planificado)

**Objetivo:** Visualización geográfica de jurisdicciones y actividad.

**Tareas:**
- [ ] Integración Leaflet/Mapbox
- [ ] Markers por jurisdicción con popups
- [ ] Heatmap de actividad por zona
- [ ] Filtros geográficos
- [ ] Timeline de eventos

### Próximos Sprints

**Sprint 3:** Sistema de Usuarios y Roles  
**Sprint 4:** Alertas Avanzadas y Notificaciones  
**Sprint 5:** Análisis de Presupuesto Mejorado  
**Sprint 6:** Mobile App (React Native)

---

## 📚 Documentación

### Documentación Principal

| Documento | Descripción |
|-----------|-------------|
| [AGENTS.md](AGENTS.md) | Contrato de agentes IA y contribuidores |
| [ENV_SETUP.md](ENV_SETUP.md) | Configuración de variables de entorno |
| [SPRINT_0_SUMMARY.md](SPRINT_0_SUMMARY.md) | Resumen Sprint 0 |
| [SYNC_FEATURE_IMPLEMENTATION.md](SYNC_FEATURE_IMPLEMENTATION.md) | Feature "Sync to Today" |
| [REDISEÑO_JURISDICCIONAL.md](REDISEÑO_JURISDICCIONAL.md) | Plan completo rediseño |
| [FASE1_JURISDICCIONES_COMPLETADA.md](FASE1_JURISDICCIONES_COMPLETADA.md) | Fase 1 completada |
| [FASE2_UI_JURISDICCIONES_COMPLETADA.md](FASE2_UI_JURISDICCIONES_COMPLETADA.md) | Fase 2 completada |
| [RESUMEN_IMPLEMENTACION_JURISDICCIONES.md](RESUMEN_IMPLEMENTACION_JURISDICCIONES.md) | Resumen completo |

### Documentación Técnica

```
watcher-backend/docs/          # Docs consolidados
├── AGENTIC_ARCHITECTURE.md    # Arquitectura de agentes IA
├── API_ENDPOINTS.md           # Documentación de API
└── ...

docs/architecture/             # Legacy architecture docs
├── ARQUITECTURA_ANALISIS_PERSISTENTE.md
├── DSLAB_GUIA_USO_COMPLETA.md
└── ...
```

### API Documentation

La documentación interactiva de la API está disponible en:
- **Swagger UI:** http://localhost:8001/docs
- **ReDoc:** http://localhost:8001/redoc

### Categorías de Endpoints

| Categoría | Endpoints | Descripción |
|-----------|-----------|-------------|
| **Boletines** | `/api/v1/boletines/` | CRUD y procesamiento de boletines |
| **Jurisdicciones** | `/api/v1/jurisdicciones/` | Gestión de jurisdicciones |
| **Análisis** | `/api/v1/analisis/` | Resultados de análisis IA |
| **Alertas** | `/api/v1/alertas/` | Sistema de alertas |
| **Agentes** | `/api/v1/agents/` | Gestión de agentes IA |
| **Workflows** | `/api/v1/workflows/` | Ejecución de workflows |
| **Presupuesto** | `/api/v1/presupuesto/` | Análisis presupuestario |
| **Sync** | `/api/v1/sync/` | Sincronización automática |
| **Dashboard** | `/api/v1/dashboard/` | Estadísticas y métricas |

---

## 🎨 Capturas de Pantalla

### Dashboard Principal
Vista general con estadísticas, agentes activos y actividad reciente.

### Vista de Jurisdicciones
Exploración de jurisdicciones con filtros, búsqueda y vista de detalle.

### Documentos y Boletines
Lista de boletines con filtros por jurisdicción, fecha y estado de procesamiento.

### Análisis de Agentes IA
Dashboard de agentes IA especializados con historial de ejecuciones.

---

## 🤝 Equipo

### Agentes IA

- **Opus 4.5** - Agente de Planificación
  - Descomposición de tareas
  - Creación de tickets
  - Validación de implementación
  - Revisión de arquitectura

- **Sonnet 4.5** - Agente de Implementación
  - Desarrollo de features
  - Testing y QA
  - Documentación técnica
  - Resolución de bugs

### Desarrollador Principal

- **German Evangelisti** - Arquitecto y Product Owner

### Contribuidores

Ver [AGENTS.md](AGENTS.md) para guías de contribución.

---

## 📝 Licencia

Este proyecto es de código privado para uso interno.

---

## 🔗 Enlaces Útiles

- **Boletín Oficial de Córdoba:** https://boletinoficial.cba.gov.ar/
- **Datos Abiertos Córdoba:** https://datosabiertos.cordoba.gob.ar/
- **OpenAI API:** https://platform.openai.com/
- **FastAPI:** https://fastapi.tiangolo.com/
- **React:** https://react.dev/
- **Mantine UI:** https://mantine.dev/

---

## 📞 Contacto

Para preguntas, sugerencias o reportar issues:

- **Email:** german.evangelisti@example.com
- **GitHub Issues:** [Crear Issue](#)
- **Discussions:** [GitHub Discussions](#)

---

## 🙏 Agradecimientos

- Gobierno de la Provincia de Córdoba por datos abiertos
- Comunidad open source de FastAPI y React
- OpenAI por la API de GPT-4
- Todos los contribuidores del proyecto

---

**Última actualización:** 11 de febrero de 2026  
**Versión:** MVP v1.1  
**Estado:** ✅ Producción

---

<div align="center">
  <strong>Hecho con ❤️ para la transparencia gubernamental y el control ciudadano</strong>
</div>

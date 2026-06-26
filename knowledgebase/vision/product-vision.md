# Visión de Producto — Watcher Agent

**Documento vivo** · Última actualización: 2026-06-26

---

## 🎯 Visión

**Watcher Agent** es un sistema de monitoreo ciudadano que automatiza la ingesta, análisis y alerta sobre boletines oficiales de la Provincia de Córdoba, Argentina. Extrae actos administrativos, licitaciones, decretos y resoluciones mediante LLM, detecta irregularidades y patrones, y los visualiza en dashboards interactivos.

No reemplaza al periodismo de investigación — **lo potencia** eliminando el trabajo mecánico de leer 100-300 páginas diarias.

---

## 🧭 Stakeholders

| Rol | Interés |
|---|---|
| **Germán Evangelisti** (Product Owner + Arquitecto) | Control ciudadano, transparencia gubernamental, detección de irregularidades |
| **Opus 4.5** (Agente de Planificación) | Descomposición de tareas, creación de tickets, validación de implementación |
| **Sonnet 4.5** (Agente de Implementación) | Desarrollo de features, testing, documentación técnica |
| **Ciudadanía** (futuro) | Acceso a información fiscal transparente y accionable |

---

## 🏗️ Stack técnico

| Capa | Tecnología |
|---|---|
| API | FastAPI 0.104+ (async, Python 3.9+) |
| Database | PostgreSQL (prod) / SQLite (dev) vía SQLAlchemy async |
| Graph DB | Neo4j 5 Community (entidades + relaciones) |
| Vector Store | ChromaDB (búsqueda semántica) |
| LLM | Google Gemini 2.0 Flash (structured output) |
| Task Scheduler | APScheduler (cron-based bulletin sync) |
| Frontend | React 18 + TypeScript + Vite + shadcn/ui |
| Packaging | uv |

---

## 📐 Principios de diseño

1. **Async-first** — Todas las operaciones I/O son asíncronas (FastAPI + SQLAlchemy async + httpx)
2. **Multi-modelo** — PostgreSQL (metadata) + Neo4j (grafo) + ChromaDB (vectores)
3. **Pipeline ABC** — Extract → Transform → Load como contrato base
4. **Intelligence Tiers** — FreeProvider (keyword/regex, sin LLM) + ProProvider (Gemini, structured output)
5. **Privacy-first** — CUIT masking middleware, sin datos sensibles en logs
6. **Agentic layer** — 5 agentes especializados coordinados por orchestrator

---

## 🗺️ Roadmap

| Fase | Épicas | Estado |
|---|---|---|
| Fase 0 | Setup + tooling | ✅ Completado |
| Fase 1 | Épica 0: Migración OpenAI → Gemini | ✅ Completado (queda re-indexado consistente) |
| Fase 2 | Épicas 1-5: Pipeline (Ingesta, Extracción, Features, Indexación, Retrieval) | 🟢 Mayormente completado (Feature Eng. parcial) |
| Fase 3 | Épica 6: Sistema agentico multi-agente | ✅ Completado |
| Fase 4 | Épica 7: Producción, hardening, testing | 🟢 Mayormente completado |
| Fase 5 | UI v2: shadcn/ui + TanStack | ✅ Completado |
| Extra | Vertical Presupuesto/Ejecución 2026 | ✅ Completado |
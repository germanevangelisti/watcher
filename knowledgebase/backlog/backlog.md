# Product Backlog — Watcher Agent

Ordenado por valor de negocio. Estatus: `idea` | `refinado` | `en progreso` | `hecho`.

---

## Épica 0 — Migración OpenAI → Google Gemini
> En curso

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 0.1 | Instalar SDK Google Generative AI | `google-generativeai` y `langchain-google-genai` en requirements | ✅ hecho |
| 0.2 | Actualizar config para GOOGLE_API_KEY | AgentSystemConfig, config.py y .env migrados | 🟡 en progreso |
| 0.3 | Migrar EmbeddingService | `text-embedding-004` reemplaza `text-embedding-ada-002` | ⬜ pendiente |
| 0.4 | Migrar DocumentProcessor y compliance endpoint | Embeddings de Google en pipeline de documentos | ⬜ pendiente |
| 0.5 | Migrar WatcherService | `gemini-2.0-flash` reemplaza `gpt-3.5-turbo` | ⬜ pendiente |
| 0.6 | Migrar InsightReportingAgent | Gemini en reporting agent | ⬜ pendiente |
| 0.7 | Re-indexar ChromaDB con Google embeddings | Script de re-indexación funcional | ⬜ pendiente |

---

## Épica 1 — Pipeline de Ingesta
> Pendiente

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 1.1 | ProvincialPipeline: PDF download | Descarga de boletinoficial.cba.gov.ar con reintentos | ⬜ pendiente |
| 1.2 | UploadedPipeline: user document ingestion | Upload vía `/api/v1/upload` con validación | ⬜ pendiente |
| 1.3 | IngestionRun tracking | Pipeline name, status, rows_in, rows_loaded, timestamps | ⬜ pendiente |
| 1.4 | Jurisdicciones: provincia, capital, municipalidades, comunas | Clasificación automática por jurisdicción | ⬜ pendiente |

---

## Épica 2 — Extracción y Análisis
> Pendiente

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 2.1 | FreeProvider: keyword/regex | Detección de riesgo sin LLM | ⬜ pendiente |
| 2.2 | ProProvider: Gemini structured extraction | Extracción de actos administrativos con structured output | ⬜ pendiente |
| 2.3 | IntelligenceProvider protocol | Selección automática Free vs Pro según GOOGLE_API_KEY | ⬜ pendiente |
| 2.4 | Document Intelligence Agent | PDF text extraction, NER, entity linking | ⬜ pendiente |

---

## Épica 3 — Feature Engineering
> Pendiente

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 3.1 | Transparency scoring (0–100) | Score numérico por acto administrativo | ⬜ pendiente |
| 3.2 | Red flag classification | Clasificación de irregularidades con tipología | ⬜ pendiente |
| 3.3 | Entidad extraction + normalization | Nombres normalizados, CUIT masked | ⬜ pendiente |

---

## Épica 4 — Indexación y Búsqueda
> Pendiente

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 4.1 | Neo4j graph: Entidad + Boletin nodes | Nodos y relaciones MENCIONADO_EN | ⬜ pendiente |
| 4.2 | ChromaDB vector index | Embeddings de texto completo de actos | ⬜ pendiente |
| 4.3 | Fulltext index: entidad_nombre | Búsqueda fulltext en Neo4j | ⬜ pendiente |

---

## Épica 5 — Retrieval y Consulta
> Pendiente

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 5.1 | Semantic search | Búsqueda semántica vía ChromaDB | ⬜ pendiente |
| 5.2 | Graph traversal queries | Consultas de relaciones entre entidades y boletines | ⬜ pendiente |
| 5.3 | Insight & Reporting Agent | NL queries, executive summaries | ⬜ pendiente |

---

## Épica 6 — Sistema Agentico Multi-Agente
> Pendiente

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 6.1 | Orchestrator | Workflow management, human approval gates, WebSocket pub/sub | ⬜ pendiente |
| 6.2 | Anomaly Detection Agent | Detección de anomalías con scoring | ⬜ pendiente |
| 6.3 | Learning & Feedback Agent | Model tuning, threshold adjustment | ⬜ pendiente |

---

## Épica 7 — Producción y Hardening
> Pendiente

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 7.1 | Testing suite | Unit + integration tests con cobertura > 80% | ⬜ pendiente |
| 7.2 | APScheduler cron sync | Sincronización automática de boletines | ⬜ pendiente |
| 7.3 | API endpoints documentados | Swagger UI + ReDoc completos | ⬜ pendiente |
| 7.4 | Dashboard UI v2 | shadcn/ui + TanStack migration | ⬜ pendiente |

---

## Bugs conocidos

| ID | Descripción | Épica | Estado |
|---|---|---|---|

> Extraído de `.cursor/plans/` y `README.md` — 2026-05-24
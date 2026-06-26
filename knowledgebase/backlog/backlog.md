# Product Backlog — Watcher Agent

Ordenado por valor de negocio. Estatus: `idea` | `refinado` | `en progreso` | `hecho`.

> **Sincronizado con el código el 2026-06-26** a partir del historial de git (hasta `da098b7`), `docs/changelog.md` (v2.0.0) y la auditoría del backend. El núcleo de las Épicas 0–2 y 4–6 está implementado; ver notas por historia.

---

## Épica 0 — Migración OpenAI → Google Gemini
> Hecho (queda 1 ajuste de deuda técnica)

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 0.1 | Instalar SDK Google Generative AI | `google-generativeai` y `langchain-google-genai` en requirements | ✅ hecho |
| 0.2 | Actualizar config para GOOGLE_API_KEY | `config.py`, `agent_config.py` y startup en `main.py` migrados | ✅ hecho |
| 0.3 | Migrar EmbeddingService | Embeddings de Google en producción (`gemini-embedding-001`, 3072 dims) | ✅ hecho* |
| 0.4 | Migrar DocumentProcessor y compliance endpoint | Embeddings de Google en pipeline de documentos | ✅ hecho |
| 0.5 | Migrar WatcherService | Gemini reemplaza `gpt-3.5-turbo` | ✅ hecho |
| 0.6 | Migrar InsightReportingAgent | Gemini en reporting agent | ✅ hecho |
| 0.7 | Re-indexar ChromaDB con Google embeddings | Script de re-indexación funcional | 🟡 en progreso* |

> *Deuda: el modelo de embeddings difiere entre producción (`gemini-embedding-001`, 3072 dims) y `scripts/reindex_google_embeddings.py` (`text-embedding-004`, 768 dims). Falta unificar y re-indexar de forma consistente.

---

## Épica 1 — Pipeline de Ingesta
> Hecho (1.1 parcial)

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 1.1 | ProvincialPipeline: PDF download | Descarga de boletinoficial.cba.gov.ar con reintentos | 🟡 parcial (descarga en `sync_service`, no en `extract()`) |
| 1.2 | UploadedPipeline: user document ingestion | Upload vía `/api/v1/upload` con validación + dedup SHA256 | ✅ hecho |
| 1.3 | IngestionRun tracking | Pipeline name, status, rows_in, rows_loaded, timestamps | ✅ hecho |
| 1.4 | Jurisdicciones: provincia, capital, municipalidades, comunas | Clasificación automática por jurisdicción | 🟡 parcial |

---

## Épica 2 — Extracción y Análisis
> Hecho

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 2.1 | FreeProvider: keyword/regex | Detección de riesgo sin LLM | ✅ hecho |
| 2.2 | ProProvider: Gemini structured extraction | Extracción de actos administrativos con structured output | ✅ hecho |
| 2.3 | IntelligenceProvider protocol | Selección automática Free vs Pro según GOOGLE_API_KEY | ✅ hecho |
| 2.4 | Document Intelligence Agent | PDF text extraction, NER, entity linking | ✅ hecho |

---

## Épica 3 — Feature Engineering
> Parcial

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 3.1 | Transparency scoring (0–100) | Score numérico por acto administrativo | 🟡 parcial (lógica repartida en servicios) |
| 3.2 | Red flag classification | Clasificación de irregularidades con tipología | 🟡 parcial |
| 3.3 | Entidad extraction + normalization | Nombres normalizados, CUIT masked | 🟡 parcial (CUIT masking ✅) |

---

## Épica 4 — Indexación y Búsqueda
> Hecho

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 4.1 | Neo4j graph: Entidad + Boletin nodes | Nodos y relaciones MENCIONADO_EN | ✅ hecho |
| 4.2 | ChromaDB vector index | Embeddings de texto completo de actos | ✅ hecho |
| 4.3 | Fulltext index: entidad_nombre | Búsqueda fulltext en Neo4j (`entidad_nombre_fulltext`) | ✅ hecho |

---

## Épica 5 — Retrieval y Consulta
> Hecho

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 5.1 | Semantic search | Búsqueda semántica vía ChromaDB | ✅ hecho |
| 5.2 | Hybrid Search con RRF | Fusión semántica + keyword + re-ranking | ✅ hecho |
| 5.3 | Graph traversal queries | Consultas de relaciones (`/camino`, `/vecinos`, `/graph`) | ✅ hecho |
| 5.4 | Insight & Reporting Agent | NL queries con RAG, executive summaries | ✅ hecho |

---

## Épica 6 — Sistema Agentico Multi-Agente
> Hecho

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 6.1 | Orchestrator | Workflow management, human approval gates, WebSocket pub/sub | ✅ hecho |
| 6.2 | Anomaly Detection Agent | Detección de anomalías con scoring | ✅ hecho |
| 6.3 | Learning & Feedback Agent | Model tuning, threshold adjustment, `/feedback` | ✅ hecho |
| 6.4 | Verification Agent | Verificación adversarial registrada en orchestrator | ✅ hecho |

---

## Épica 7 — Producción y Hardening
> Mayormente hecho

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 7.1 | Testing suite | Unit + integration + e2e (~181 tests pasando) | 🟡 cobertura >80% sin medir |
| 7.2 | APScheduler cron sync | Sincronización automática de boletines | ✅ hecho |
| 7.3 | API endpoints documentados | Swagger UI + ReDoc completos | 🟡 parcial |
| 7.4 | Dashboard UI v2 | shadcn/ui + TanStack migration | ✅ hecho |

---

## Épica P — Presupuesto y Ejecución 2026 (fuera del plan original)
> Hecho

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| P.1 | Parser PDF presupuesto 2026 | `scripts/parse_pdf_presupuesto_2026.py` → tabla `presupuesto_base` | ✅ hecho |
| P.2 | ETL análisis → ejecución | `scripts/etl_analisis_to_ejecucion.py` | ✅ hecho |
| P.3 | Tabla de alias de organismos | Matching mejorado análisis ↔ presupuesto base | ✅ hecho |
| P.4 | Detección de duplicados en ejecución | Columna `is_duplicate` + lógica en ETL | ✅ hecho |
| P.5 | API `/presupuesto/ejecucion/*` | Endpoints con filtrado y agregación | ✅ hecho |
| P.6 | Frontend "Ejecución Presupuestaria" | Página con métricas de deduplicación | ✅ hecho |

---

## Bugs conocidos

| ID | Descripción | Épica | Estado |
|---|---|---|---|
| DT-1 | Modelo de embeddings inconsistente (`gemini-embedding-001` vs `text-embedding-004`) | 0 | ⬜ abierto |

> Sincronizado con commits hasta `da098b7` — 2026-06-26

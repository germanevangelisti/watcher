# Product Backlog — Watcher Agent

Ordenado por valor de negocio. Estatus: `idea` | `refinado` | `en progreso` | `hecho`.

> **Sincronizado con el código el 2026-09-15**. [V.1](V.1-verificar-pipeline-vs-realidad.md) y [V.2](V.2-matching-denominador.md) hechos. Abril 2026 cerrado en DB (no commitear).

---

## H.1 — Pipeline en hardware local
> Hecho · 8 pts · [detalle](H.1-pipeline-hardware-local.md)

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| H.1 | Pipeline en workstation local (cooperledge) | Workers nproc-2, Compose local 8 GB Neo4j, rerank/embed/LLM locales, tests | ✅ hecho |

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
| 0.7 | Re-indexar ChromaDB con Google embeddings | Script de re-indexación funcional y consistente | ✅ hecho* |

> *A1 (resuelto): `scripts/reindex_google_embeddings.py` reutiliza el modelo canónico (`gemini-embedding-001`, 3072 dims), re-indexa la colección in-place con backup y tiene tests. Queda como paso **operativo** correr el re-indexado contra ChromaDB con datos reales.

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
> Hecho

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| 3.1 | Transparency scoring (0–100) | Score numérico por acto administrativo | ✅ hecho (`TransparencyScorer` per-acto, cableado en pipeline) |
| 3.2 | Red flag classification | Clasificación de irregularidades con tipología | ✅ hecho (`RedFlagClassifier` con tipología canónica `RedFlagType`) |
| 3.3 | Entidad extraction + normalization | Nombres normalizados, CUIT masked | ✅ hecho (extracción + normalización + validación de CUIT en `EntityService`) |

> **E3 (resuelto):** `app/services/feature_engineering.py` centraliza scoring de transparencia (0–100) y clasificación de red flags **por acto administrativo**, cableado en `_analyze_document`. Persiste en `Analisis.transparency_score`, `Analisis.red_flags_json` y `Analisis.num_red_flags` (migración `add_acto_feature_engineering`). `EntityService` ahora extrae y normaliza CUIT/CUIL (`XX-XXXXXXXX-X`) con validación de dígito verificador. 54 tests unitarios nuevos.

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

## Épica V — Verificación / ground truth
> V.1–V.6 hechos · V.5 cerró el período · [V.1](V.1-verificar-pipeline-vs-realidad.md) · [V.2](V.2-matching-denominador.md) · [V.3](V.3-honestidad-contraste.md) · [V.4](V.4-limites-del-cociente.md) · [V.5](V.5-ingesta-mayo-septiembre.md) · [V.6](V.6-dedup-licitaciones-republicadas.md)

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| V.1.1 | Inventario calendario vs DB | Diff días/secciones de boletinoficial.cba.gov.ar vs `boletines` | ✅ hecho |
| V.1.2 | Gold set de extracción | ≥ 12 PDFs etiquetados; recall/monto/`numero_acto` | ✅ hecho |
| V.1.3 | Cerrar un mes | Marzo 2026 completo; ledger idempotente al reprocesar | ✅ hecho |
| V.1.4 | Ancla Ley 11.088 | Totales EPEC/ACIF + 15 programas + unmatched / 295% | ✅ hecho |
| V.1.5 | Trimestral CGE | `ejecucion_trimestral` T1 2026 vs 8 organismos (orden de magnitud) | ✅ hecho |
| V.2.1 | Bitácora 4 alertas >100% | Query organismo → ledger → `pb_id` → vigente | ✅ hecho |
| V.2.2 | S-511 / Unidad Ejecutora | No matchear a Dirección de Ministerio | ✅ hecho |
| V.2.3 | Denominador por organismo | `%` vs suma vigente del organismo canónico | ✅ hecho |
| V.2.4 | Truncados `presupuesto_base` | `MINISTERIO DE` / secretarías no cuelgan $50B de $1.9B | ✅ hecho |
| V.3 | Honestidad del contraste | El `pb_id` persistido se revalida; dedup robusto; UI no silencia >100% | ✅ hecho (V.3.1/32/33) |
| V.4 | Límites del cociente | El `%` declara su período y su techo; 74 truncos recuperados del PDF | ✅ hecho (V.4.1/42/43) |
| V.5 | Ingesta mayo–septiembre | 5 meses ingeridos, calendario sin huecos, ETL re-corrido, gate exit 0 | ✅ hecho (2026-09-19) |
| V.6 | Dedup de licitaciones republicadas | `_normalize_acto` unifica grafías; A/B medido; contra-ejemplos con test | ✅ hecho |
| V.7 | El monto del acto de al lado | El extractor no mezcla columnas (4ª sección) | ⬜ pendiente |
| V.8 | El monto del aviso vecino | Guard en `crud.py:208` contra el **texto de entrada** (no la cita) | ⬜ pendiente* |

\* El caso catastrófico de V.8 ($3,0B en una fila, alerta fabricada de 10.850%) está
**reparado a mano contra el PDF**, con evidencia en `datos_extra`; la reparación se
pierde si el boletín se re-extrae.

> **Actualización V.5 (2026-09-19).** El período medido pasa de 3 a **8 meses**
> (feb–sep). Cifras corregidas: feb–abr **$538,44B → $519,57B** canónicos por la
> dedup de V.6; alertas >100% **5 → 3** (ninguna nueva); el techo no se mueve
> ($7,531907T). Queda **2026-01** como único mes vencido sin ingesta. Toda historia
> que cite el ledger pre-V.5 debe leerse con estas dos correcciones.

No mezclar capa A (pipeline vs boletín) con capa C (boletín vs caja). Mayo+ ya no multiplica matching basura de las 4 alertas; el recall 44.4% sigue siendo deuda de extracción.

---

## Épica P — Presupuesto y Ejecución 2026 (fuera del plan original)
> P.1–P.7.4 hecho · mergeada a `main`

| # | Historia | Criterio de aceptación | Estado |
|---|---|---|---|
| P.1 | Parser PDF presupuesto 2026 | `scripts/parse_pdf_presupuesto_2026.py` → tabla `presupuesto_base` | ✅ hecho |
| P.2 | ETL análisis → ejecución | `scripts/etl_analisis_to_ejecucion.py` | ✅ hecho |
| P.3 | Tabla de alias de organismos | Matching mejorado análisis ↔ presupuesto base | ✅ hecho |
| P.4 | Detección de duplicados en ejecución | Columna `is_duplicate` + lógica en ETL | ✅ hecho |
| P.5 | API `/presupuesto/ejecucion/*` | Endpoints con filtrado y agregación | ✅ hecho |
| P.6 | Frontend "Ejecución Presupuestaria" | Página con métricas de deduplicación | ✅ hecho |
| P.7.1 | Clasificar gasto público per acto | `is_gasto_publico` + `etapa_gasto` + `jurisdiccion_gasto` por reglas | ✅ hecho |
| P.7.2 | Ledger al cerrar el pipeline | Upsert `ejecucion_presupuestaria` tras `_analyze_document`; `numero_acto` recuperado | ✅ hecho |
| P.7.3 | Anclar Ley 11.088 | `presupuesto_base` 2026 cargado + alias ACIF/EPEC/Policía/CCU | ✅ hecho (480 programas; match 90/131) |
| P.7.4 | Contrastar en UI | `% monto_acumulado/monto_vigente` + toggle compromiso/ejecución | ✅ hecho |

Medición 2026-09-14 tras P.7.3: `presupuesto_base` 480 filas; match **90/131** (provincial 90/97). Corte UI post V.2 (2026-09-15): [corte-abril-ui.md](../current/corte-abril-ui.md) — 0 alertas >100%. Ver [P.7](P.7-gasto-acumulado-presupuesto.md). [V.1](V.1-verificar-pipeline-vs-realidad.md) y [V.2](V.2-matching-denominador.md) hechos.

---

## Bugs conocidos

| ID | Descripción | Épica | Estado |
|---|---|---|---|
| DT-1 | Modelo de embeddings inconsistente (`gemini-embedding-001` vs `text-embedding-004`) | 0 | ✅ resuelto (A1) |
| DT-2 | Tests de `indexing_service` hacen `await` sobre sesión SQLAlchemy síncrona del fixture | 7 | ⬜ abierto |
| DT-3 | `scripts/parse_excel_presupuesto.py` importaba `pandas` (no declarado) en el top level e impedía colectar `test_etl_presupuesto.py` | P | ✅ resuelto (P.7.2, import perezoso) |
| DT-4 | `reindex_google_embeddings.py` hace `sys.exit(1)` al importarse sin `GOOGLE_API_KEY` → INTERNALERROR que corta la colección de toda la suite | 7 | ✅ resuelto (2026-09-18, `_require_deps()`) |
| DT-5 | 6 módulos de test no colectan: `watcher_monolith` y `kba_agent` no existen en el repo | 7 | ✅ resuelto (2026-09-18: 3 revividos por prefijo, 3 con `importorskip`) |
| DT-6 | `ruff.toml` (80 bytes) tiene precedencia sobre `pyproject.toml` en ruff y solo define `per-file-ignores`: `select` y `line-length = 100` nunca se aplicaron. Ruff corría con defaults | 7 | ✅ causa raíz resuelta (2026-09-18) |
| DT-7 | Residual de lint tras el autofix: 643 errores sin autofix posible — `E501` 439 (líneas >100), `B904` 97 (`raise` sin `from`), `N806` 34. Concentrados en `app/db/models.py` (49 E501), endpoints y agents | 7 | ⬜ abierto (diferido a historia propia) |

> Sincronizado con commits hasta `da098b7` — 2026-06-26. Bugs DT-3..DT-6 detectados en P.7 (2026-09-13).
> DT-4..DT-7 trabajados el 2026-09-18 (rama `chore/lint-normalization`). Detalle de DT-6: la deuda real era 8.327 errores, no 2.668 — el número chico era el de los defaults, no el del ruleset del proyecto.

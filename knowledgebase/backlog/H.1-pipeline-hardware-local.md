# H.1 Pipeline en hardware local (cooperledge)

**Épica:** Épica 7 / Deuda técnica + runtime
**Puntos:** 8
**Estado:** hecho  
**Rama:** mergeada a `main` (`feature/H.1-pipeline-hardware-local`)

## Objetivo

Hacer que el pipeline de Watcher use la workstation local (CPU Ultra 9, 64 GB RAM, RTX 5070 Ti 12 GB) como runtime primario: workers reales, memoria de Neo4j/Postgres acorde, reranker y embeddings locales, y un IntelligenceProvider `LocalPro` vía Ollama. Gemini queda como fallback cloud.

## Criterio de aceptación

- [x] `HARDWARE_PROFILE=local` (default en development) calcula `PIPELINE_WORKERS = max(1, nproc-2)`.
- [x] `BatchProcessor`, `ProvincialPipeline.transform` y `/pipeline` batch corren con concurrencia acotada (no loops 100% secuenciales).
- [x] Loops que invocan LLM respetan `LLM_MAX_CONCURRENT` (default 1 en local) para no saturar 12 GB de VRAM.
- [x] `docker-compose.yml` parametriza heap Neo4j; `docker-compose.local.yml` sube Neo4j a 8 GB y Postgres `shared_buffers=2GB` **sin** romper el default de GCE (1 GB).
- [x] Reranker auto en perfil local prefiere cross-encoder; Gemini es explícito (`RERANK_STRATEGY=google`).
- [x] Embeddings locales implementados (sentence-transformers) en colección separada; no pisan la de Gemini 3072-d.
- [x] `INTELLIGENCE_PROVIDER=local` usa Ollama (`OLLAMA_BASE_URL`); si Ollama no responde, degrada a FreeProvider.
- [x] `WatcherService.analyze_fragment` delega al provider local cuando el tier es `local` aunque exista `GOOGLE_API_KEY`.
- [x] Tests unitarios de hardware, factory de providers, reranker auto y embeddings locales (con mocks).
- [x] `knowledgebase/current/status.md` + ADR actualizados.

## Fuera de alcance (historias siguientes)

- UI de compliance / menciones / jurisdicciones / mapa
- JWT
- Scrapers Nación / municipios
- Fine-tune QLoRA
- Correr el reindex operativo contra datos reales (queda como paso operativo)
- P.7 gasto acumulado vs presupuesto (ledger vivo)

## Follow-up incluido en el merge (runtime cooperledge)

- [x] Caps locales: `PIPELINE_CHUNK_SIZE=3000`, `PIPELINE_MAX_INDEX_CHUNKS=80`, `ANALYSIS_MAX_FRAGMENTS=8` + `fragment_priority`.
- [x] `OLLAMA_NUM_CTX=4096`, timeout 600s; `document_pipeline_concurrency()` = workers (LLM sigue en semáforo).
- [x] ALTER SQLite para `transparency_score` / `red_flags_json` / `num_red_flags`.
- [x] Scripts PowerShell: `scripts/start-backend-local.ps1`, `compose-local.ps1`, `enable-wsl.ps1`.

## Notas para agentes

- No subir el heap de Neo4j a 8 GB en `docker-compose.yml` base: GCE e2-medium tiene ~4 GB.
- No setear `NEO4J_HEAP_*` en `.env` de GCE: Compose interpola y pisa los defaults.
- Código en inglés, docs en español. Línea ≤ 100 (ruff).
- `sentence-transformers` es extra opcional `[local]`; los tests no deben requerir GPU ni Torch real.

# ADR-001 — Pipeline en hardware local (cooperledge)

**Fecha:** 2026-09-12
**Estado:** aceptado
**Historia:** H.1

## Contexto

Watcher se diseñó para Gemini API + una VM GCE e2-medium (~2 vCPU, 4 GB). La workstation `cooperledge` (Ultra 9 275HX, 64 GB RAM, RTX 5070 Ti 12 GB) puede correr extracción, embeddings y re-ranking en local. El pipeline era secuencial (`max_workers` muerto) y el reranker auto prefería Gemini 1-hit-1-call.

## Decisión

1. **Dos perfiles:** `HARDWARE_PROFILE=local` (default en development) y `cloud` (default si `ENVIRONMENT=production`).
2. **Workers:** `PIPELINE_WORKERS = max(1, nproc - PIPELINE_CPU_RESERVE)` con reserva 2. Los loops extract+LLM usan `min(workers, LLM_MAX_CONCURRENT)` (1 en local para no saturar 12 GB VRAM).
3. **Memoria de infra:** `docker-compose.yml` mantiene heap Neo4j 512m–1G (GCE). `docker-compose.local.yml` (no auto-merged) sube Neo4j a 8 GB y Postgres `shared_buffers=2GB`.
4. **IA local-first en perfil local:** reranker cross-encoder; embeddings sentence-transformers en colección `watcher_documents_local` (no pisa Gemini 3072-d); `LocalProProvider` vía Ollama. Gemini queda como `INTELLIGENCE_PROVIDER=google` o fallback.
5. **Degradación:** Ollama caído → FreeProvider; sentence-transformers ausente → noop/google según clave.

## Consecuencias

- El deploy GCE no cambia si no se usa `docker-compose.local.yml`.
- Cambiar a embeddings locales requiere reindexar esa colección (dims distintas).
- Extra opcional `[local]` instala torch + sentence-transformers.
- Un 14B Q5 y el reranker no deben convivir a full VRAM; `LLM_MAX_CONCURRENT=1` es el default local.
- En cooperledge, S2 judiciales llega a 500+ chunks de embedding (CPU). Caps: `PIPELINE_MAX_INDEX_CHUNKS=80`, `ANALYSIS_MAX_FRAGMENTS=8` con `fragment_priority`.
- `OLLAMA_NUM_CTX=4096` (8192 con 14B llena 12 GB y timeout). `--reload` del API mata pipelines en vuelo.

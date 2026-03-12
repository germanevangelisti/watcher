# Watcher — Changelog

## v2.0.0 (March 2026) — Architecture Overhaul

### Fase 0 — Foundation & Tooling
- Migrated from `requirements.txt` to `pyproject.toml` + `uv`
- Created `query_loader.py` with LRU cache for SQL and Cypher files
- Updated Makefile to use `uv run pytest`
- Added HEALTHCHECK and `curl` to Dockerfile

### Fase 1 — Pipeline ABC + Query Externalization
- Created `BoletinPipeline` ABC with `IngestionRun` tracking
- Implemented `ProvincialPipeline` (Córdoba PDF ingestion)
- Implemented `UploadedPipeline` (user document upload)
- Added `IngestionRun` SQLAlchemy model
- Externalized 5 SQL queries to `app/queries/*.sql`
- Added `GET /api/v1/pipelines/runs` endpoint

### Fase 2 — Neo4j as Core
- Created declarative schema `graph/init.cypher` (3 constraints, 5 indexes, 1 fulltext index)
- Externalized 8 Cypher queries to `graph/queries/*.cypher`
- Refactored `neo4j_client.py` → `graph_driver.py` (backward-compatible shim kept)
- Updated `graph_service.py` to use externalized queries via `run_query()`
- Added Neo4j service to `docker-compose.yml` with health checks

### Fase 3 — Intelligence Tiering + Privacy
- Created `IntelligenceProvider` protocol with `FreeProvider` (rule-based) and `ProProvider` (Gemini)
- Integrated provider tier into `WatcherService` (delegates to `FreeProvider` when no API key)
- Added `CUITMaskingMiddleware` (masks Argentine tax IDs in JSON responses)
- Added `SecurityHeadersMiddleware` (X-Content-Type-Options, X-Frame-Options, etc.)
- Created `config/source_registry.yml` with 6 data sources
- Added `GET /api/v1/sources/health` endpoint

### Fase 4 — Legacy Cleanup
- Deleted 7 obsolete backend files (debug scripts, one-shot migrations, package-lock.json)
- Consolidated 25+ docs into 6 structured files
- Moved 5 DSLAB docs to `watcher-lab/docs/`
- Moved research PDFs to `docs/research/`
- Deleted `watcher-frontend-legacy/`

---

## v1.1.0 (February 2026)

- Multi-act extraction with structured Gemini output (FRAGMENT_ANALYSIS_SCHEMA)
- Added `texto_original`, `relacion_principal`, `firmante`, `imputacion_presupuestaria` fields
- Risk calibration rules: informativo/bajo/medio/alto with ARS thresholds
- Reference Firewall service (Fase IV)
- AIU Decomposition hook (Fase II)

## v1.0.0 (November 2025)

- Initial FastAPI backend with SQLite
- PDF text extraction pipeline (PyPDF2 / unstructured)
- Gemini integration for administrative act analysis
- ChromaDB vector search
- React + Vite frontend with dashboard, search, graph explorer
- APScheduler for bulletin sync
- Alertas, actos, presupuesto, métricas endpoints
- Compliance validation rules (23 mandatory government records)
- WebSocket real-time logs
- DS Lab for experimentation (separate module)

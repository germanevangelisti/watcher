# Watcher v2.0 — Task Tracker

## Fase 0: Fundación y Tooling
- [x] 0.1 Migrar [requirements.txt](file:///Users/germanevangelisti/watcher/watcher-lab/requirements.txt) → [pyproject.toml](file:///Users/germanevangelisti/watcher/watcher-backend/pyproject.toml) + `uv`
- [x] 0.2 Crear `query_loader.py` + directorio [queries/](file:///Users/germanevangelisti/watcher/watcher-backend/app/queries/)
- [x] 0.3 Actualizar [Makefile](file:///Users/germanevangelisti/watcher/Makefile) para `uv run`
- [x] 0.4 Actualizar [Dockerfile](file:///Users/germanevangelisti/watcher/watcher-backend/Dockerfile) → uv-only, HEALTHCHECK, mkdir app/queries
- [x] 0.5 ✅ Tests: `test_query_loader.py` pasa (11/11)

## Fase 1: Pipeline ABC + Query Externalization
- [x] 1.1 Crear `BoletinPipeline` base ABC con `IngestionRun` tracking → [pipelines/base.py](file:///Users/germanevangelisti/watcher/watcher-backend/app/pipelines/base.py)
- [x] 1.2 Implementar `ProvincialPipeline` → [pipelines/provincial.py](file:///Users/germanevangelisti/watcher/watcher-backend/app/pipelines/provincial.py)
- [x] 1.3 Implementar `UploadedPipeline` → [pipelines/uploaded.py](file:///Users/germanevangelisti/watcher/watcher-backend/app/pipelines/uploaded.py)
- [x] 1.4 Agregar modelo `IngestionRun` a SQLAlchemy → [db/models.py](file:///Users/germanevangelisti/watcher/watcher-backend/app/db/models.py)
- [x] 1.5 Extraer 5 queries SQL a archivos → [queries/*.sql](file:///Users/germanevangelisti/watcher/watcher-backend/app/queries/)
- [x] 1.6 Crear endpoint `/api/v1/pipelines/runs` → [endpoints/pipeline_runs.py](file:///Users/germanevangelisti/watcher/watcher-backend/app/api/v1/endpoints/pipeline_runs.py)
- [x] 1.7 ✅ Tests: 43/43 unit tests pasan

## Fase 2: Neo4j como Core + Schema Declarativo
- [x] 2.1 Crear `graph/init.cypher` con constraints e índices → [graph/init.cypher](file:///Users/germanevangelisti/watcher/watcher-backend/graph/init.cypher)
- [x] 2.2 Crear `graph/queries/` con queries Cypher externalizados → [graph/queries/](file:///Users/germanevangelisti/watcher/watcher-backend/graph/queries/)
- [x] 2.3 Refactorizar [neo4j_client.py](file:///Users/germanevangelisti/watcher/watcher-backend/app/db/neo4j_client.py) → [graph_driver.py](file:///Users/germanevangelisti/watcher/watcher-backend/app/db/graph_driver.py)
- [ ] 2.4 Actualizar [entity_service.py](file:///Users/germanevangelisti/watcher/watcher-backend/app/services/entity_service.py) para Neo4j
- [x] 2.5 Actualizar [graph_service.py](file:///Users/germanevangelisti/watcher/watcher-backend/app/services/graph_service.py) para queries externalizados
- [x] 2.6 Agregar Neo4j a [docker-compose.yml](file:///Users/germanevangelisti/watcher/docker-compose.yml) como servicio core
- [x] 2.7 ✅ Tests: 27/27 unit tests pasan (test_graph_query_loader + test_graph_schema)

## Fase 3: Intelligence Tiering + Privacy Middleware
- [x] 3.1 Crear [IntelligenceProvider](file:///Users/germanevangelisti/watcher/watcher-backend/app/services/intelligence_provider.py) protocol + `FreeProvider` + `ProProvider`
- [x] 3.2 Refactorizar [watcher_service.py](file:///Users/germanevangelisti/watcher/watcher-backend/app/services/watcher_service.py) para usar providers
- [x] 3.3 Crear `CUITMaskingMiddleware` → [middleware/masking.py](file:///Users/germanevangelisti/watcher/watcher-backend/app/middleware/masking.py)
- [x] 3.4 Crear `SecurityHeadersMiddleware` → [middleware/security.py](file:///Users/germanevangelisti/watcher/watcher-backend/app/middleware/security.py)
- [x] 3.5 Integrar middlewares en [main.py](file:///Users/germanevangelisti/watcher/watcher-backend/app/main.py)
- [x] 3.6 Crear [config/source_registry.yml](file:///Users/germanevangelisti/watcher/watcher-backend/config/source_registry.yml) y endpoint `/sources/health`
- [x] 3.7 ✅ Tests: 46/46 pasan (test_intelligence_providers + test_masking_middleware + test_security_middleware)

## Fase 4: Limpieza de Código Legacy
- [x] 4.1 Eliminar 7 archivos backend obsoletos (check_config, view_db, demo_agents, migrate_*, db_queries.sql, package-lock.json)
- [x] 4.2 Consolidar docs/ de 25 archivos → 6 ([README](file:///Users/germanevangelisti/watcher/docs/README.md), [architecture](file:///Users/germanevangelisti/watcher/docs/architecture.md), [api-reference](file:///Users/germanevangelisti/watcher/docs/api-reference.md), [deployment](file:///Users/germanevangelisti/watcher/docs/deployment.md), [development](file:///Users/germanevangelisti/watcher/docs/development.md), [changelog](file:///Users/germanevangelisti/watcher/docs/changelog.md))
- [x] 4.3 Mover 5 DSLAB docs a [watcher-lab/docs/](file:///Users/germanevangelisti/watcher/watcher-lab/docs/)
- [x] 4.4 Mover PDFs de investigación a [docs/research/](file:///Users/germanevangelisti/watcher/docs/research/)
- [x] 4.5 Eliminar `watcher-frontend-legacy/`
- [x] 4.6 ✅ Tests: 181/181 pasan post-cleanup

## Fase 5: Frontend — Graph Viz + Pipeline Health
- [ ] 5.1 Mejorar Graph Explorer con expand-on-click
- [ ] 5.2 Crear página Pipeline Health
- [ ] 5.3 Crear API hook `usePipelineRuns`
- [ ] 5.4 Panel de detalles de nodo
- [ ] 5.5 ✅ Tests: frontend tests pasan

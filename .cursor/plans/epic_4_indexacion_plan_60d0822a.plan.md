---
name: Epic 4 Indexacion Plan
overview: "Plan de implementacion para las 3 tareas de la Epica 4 (Indexacion): FTS5 full-text search, triple indexacion transaccional, y endpoint unificado de pipeline completo."
todos:
  - id: 4.1-fts5
    content: "4.1 Implementar SQLite FTS5: migracion Alembic, triggers de sync, FTSService con search_bm25(), script de backfill, tests"
    status: completed
  - id: 4.2-triple
    content: "4.2 Triple indexacion: crear IndexingService, refactorizar EmbeddingService.add_document(), rollback transaccional, verificacion de consistencia, tests"
    status: completed
  - id: 4.3-pipeline
    content: "4.3 Endpoint unificado: PipelineService, schemas, router POST /api/v1/pipeline/process/{file_id}, status tracking, batch processing, tests"
    status: completed
  - id: 4-notebook
    content: Crear notebook epic_4_indexacion.ipynb con validacion end-to-end de FTS5, triple indexacion, y pipeline completo
    status: completed
  - id: 4-notion-update
    content: Actualizar las 3 tareas en Notion a 'Hecho' al completar cada una
    status: completed
isProject: false
---

# Plan de Implementacion - Epica 4: Indexacion

## Estado de dependencias

Todas las dependencias previas estan completadas ("Hecho" en Notion):

- **2.2** Crear ExtractorRegistry con Strategy Pattern - Hecho
- **3.1** Unificar estrategia de chunking - Hecho
- **3.2** Implementar metadata enriquecida por chunk (ChunkRecord) - Hecho

La infraestructura base ya existe:

- `ChunkRecord` en [models.py](watcher-monolith/backend/app/db/models.py) (linea 1151) con campos para `embedding_model`, `embedding_dimensions`, `indexed_at`
- `EmbeddingService` en [embedding_service.py](watcher-monolith/backend/app/services/embedding_service.py) con ChromaDB + Google embeddings
- `ChunkingService`, `TextCleaner`, `ChunkEnricher` operativos
- Migracion Alembic para `chunk_records` ya creada

---

## Tarea 4.1 - Implementar SQLite FTS5 para full-text search

**Notion:** `Por hacer` | Sprint 3 | Vencimiento: 2026-03-04
**Estimacion:** 2-3 horas

### Objetivo

Crear una tabla virtual FTS5 en SQLite sincronizada con `chunk_records` para habilitar busqueda BM25 por texto completo.

### Pasos de implementacion

1. **Crear migracion Alembic** para la tabla FTS5
  - Archivo: `watcher-monolith/backend/alembic/versions/add_fts5_index.py`
  - SQL: `CREATE VIRTUAL TABLE chunk_records_fts USING fts5(text, document_id UNINDEXED, chunk_id UNINDEXED, section_type UNINDEXED, content=chunk_records, content_rowid=id)`
  - Crear triggers para mantener sincronizacion automatica:
    - `INSERT` trigger: agrega filas nuevas a FTS
    - `DELETE` trigger: remueve filas de FTS
    - `UPDATE` trigger: actualiza FTS al cambiar texto
2. **Crear servicio `FTSService**`
  - Archivo nuevo: `watcher-monolith/backend/app/services/fts_service.py`
  - Metodo `search_bm25(query, top_k, filters)` que ejecuta `SELECT ... FROM chunk_records_fts WHERE chunk_records_fts MATCH ? ORDER BY rank`
  - Metodo `rebuild_index()` para reconstruir el indice FTS completo desde `chunk_records`
  - Metodo `get_index_stats()` para estadisticas del indice
  - Usar `bm25()` de FTS5 para scoring
3. **Script de backfill** para indexar chunks existentes
  - Archivo: `scripts/backfill_fts5.py`
  - Recorre todos los `ChunkRecord` existentes y los inserta en la tabla FTS5
4. **Tests**
  - Test de creacion de tabla FTS5
  - Test de busqueda BM25 con query en espanol
  - Test de sincronizacion automatica via triggers
  - Test de rebuild del indice

### Archivos afectados

- `watcher-monolith/backend/alembic/versions/add_fts5_index.py` (nuevo)
- `watcher-monolith/backend/app/services/fts_service.py` (nuevo)
- `scripts/backfill_fts5.py` (nuevo)
- `tests/test_fts_service.py` (nuevo)

---

## Tarea 4.2 - Triple indexacion: vector + relacional + full-text

**Notion:** `Por hacer` | Sprint 3 | Vencimiento: 2026-03-05 | Deps: 3.2, 4.1
**Estimacion:** 2-3 horas

### Objetivo

Refactorizar `EmbeddingService.add_document()` para que cada chunk quede indexado en 3 lugares atomicamente:

1. **ChromaDB** (embedding + metadata filtrable)
2. **SQLite `chunk_records**` (metadata relacional completa)
3. **SQLite FTS5** (texto para BM25) - via triggers automaticos de 4.1

### Pasos de implementacion

1. **Crear `IndexingService**` como orquestador de triple indexacion
  - Archivo nuevo: `watcher-monolith/backend/app/services/indexing_service.py`
  - Metodo central: `async index_chunk(document_id, chunk_result, metadata, db_session)` que:
    - a) Crea `ChunkRecord` en SQLite (lo cual dispara el trigger FTS5 automaticamente)
    - b) Genera embedding via Google API
    - c) Inserta en ChromaDB
    - d) Actualiza `indexed_at` en `ChunkRecord`
  - Metodo `async index_document(document_id, chunks, metadata, db_session)` que procesa todos los chunks con rollback logico si falla alguno
  - Logica de rollback: si ChromaDB falla, borrar ChunkRecords creados; si SQLite falla, borrar de ChromaDB
2. **Refactorizar `EmbeddingService.add_document()**`
  - Delegar la logica de persistencia de ChunkRecords al nuevo `IndexingService`
  - Mantener `EmbeddingService` enfocado solo en embeddings y ChromaDB
  - `add_document()` pasa a ser un wrapper que llama a `IndexingService`
3. **Agregar metodo de verificacion de consistencia**
  - `async verify_triple_index(document_id)`: verifica que un documento existe en los 3 indices
  - `async repair_index(document_id)`: repara inconsistencias detectadas
4. **Tests**
  - Test de indexacion triple exitosa
  - Test de rollback cuando ChromaDB falla
  - Test de rollback cuando SQLite falla
  - Test de verificacion de consistencia

### Archivos afectados

- `watcher-monolith/backend/app/services/indexing_service.py` (nuevo)
- `watcher-monolith/backend/app/services/embedding_service.py` (refactorizar `add_document`)
- `tests/test_indexing_service.py` (nuevo)

---

## Tarea 4.3 - Endpoint unificado de pipeline completo

**Notion:** `Por hacer` | Sprint 3 | Vencimiento: 2026-03-06 | Deps: 2.2, 3.1, 3.2, 4.2
**Estimacion:** 3-4 horas

### Objetivo

Crear `POST /api/v1/pipeline/process/{file_id}` que ejecute el pipeline end-to-end: extract -> clean -> chunk -> enrich -> index (triple). Con status tracking granular.

### Pasos de implementacion

1. **Definir schemas del pipeline**
  - Archivo nuevo: `watcher-monolith/backend/app/schemas/pipeline.py`
  - Status enum: `uploaded -> extracting -> extracted -> cleaning -> cleaned -> chunking -> chunked -> enriching -> enriched -> indexing -> indexed | failed`
  - `PipelineRequest`: opciones de configuracion (chunk_size, overlap, skip_cleaning, etc.)
  - `PipelineResponse`: resultado con status, stats por etapa, errores
  - `PipelineStatus`: modelo para tracking en tiempo real
2. **Crear `PipelineService**` que orquesta todo el pipeline
  - Archivo nuevo: `watcher-monolith/backend/app/services/pipeline_service.py`
  - Metodo `async process_document(file_id, options, db_session)`:
    - Etapa 1: Buscar documento en DB, validar que existe y tiene archivo
    - Etapa 2: Extraer texto via `ExtractorRegistry`
    - Etapa 3: Limpiar via `TextCleaner`
    - Etapa 4: Chunking via `ChunkingService`
    - Etapa 5: Enriquecer via `ChunkEnricher`
    - Etapa 6: Triple indexacion via `IndexingService`
    - Actualizar status del documento en cada etapa
  - Manejo de errores: capturar en que etapa fallo, guardar error, marcar como `failed`
3. **Crear router `pipeline.py**`
  - Archivo nuevo: `watcher-monolith/backend/app/api/v1/endpoints/pipeline.py`
  - `POST /api/v1/pipeline/process/{file_id}` - ejecutar pipeline completo
  - `GET /api/v1/pipeline/status/{file_id}` - consultar status actual
  - `POST /api/v1/pipeline/batch` - procesar multiples documentos
  - `GET /api/v1/pipeline/stats` - estadisticas del pipeline
4. **Registrar router** en [api.py](watcher-monolith/backend/app/api/v1/api.py)
  - Agregar import de `pipeline`
  - Agregar `api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])`
5. **Agregar campo `processing_status**` al modelo de documento
  - Evaluar si usar `RequiredDocument.status` existente o agregar columna nueva
  - Los status actuales (`missing`, `downloaded`, `processed`, `failed`) se expanden a: `uploaded`, `extracting`, `extracted`, `processing`, `processed`, `indexing`, `indexed`, `failed`
6. **Tests**
  - Test del pipeline completo end-to-end
  - Test de fallo parcial (ej. extraccion falla)
  - Test de status tracking
  - Test del endpoint batch

### Archivos afectados

- `watcher-monolith/backend/app/schemas/pipeline.py` (nuevo)
- `watcher-monolith/backend/app/services/pipeline_service.py` (nuevo)
- `watcher-monolith/backend/app/api/v1/endpoints/pipeline.py` (nuevo)
- `watcher-monolith/backend/app/api/v1/api.py` (agregar router)
- `watcher-monolith/backend/app/db/models.py` (posible extension de status)

---

## Orden de ejecucion y grafo de dependencias

```mermaid
graph LR
    E3_done["Epicas 0-3 Completadas"] --> T41["4.1 FTS5 Index"]
    T41 --> T42["4.2 Triple Indexacion"]
    T42 --> T43["4.3 Pipeline Endpoint"]
    T43 --> E5["Epica 5: Retrieval"]
```




| Tarea        | Estimacion | Dependencias       | Riesgo                                      |
| ------------ | ---------- | ------------------ | ------------------------------------------- |
| 4.1 FTS5     | 2-3 hrs    | Ninguna bloqueante | Bajo - SQLite FTS5 bien documentado         |
| 4.2 Triple   | 2-3 hrs    | 4.1                | Medio - rollback cross-storage              |
| 4.3 Pipeline | 3-4 hrs    | 4.2                | Bajo - orquestacion de servicios existentes |


**Tiempo total estimado: 7-10 horas**

## Notebook de validacion

Crear `notebooks/epic_4_indexacion.ipynb` con celdas de prueba para:

- Verificar creacion de tabla FTS5
- Probar busqueda BM25 basica
- Ejecutar triple indexacion de un documento de ejemplo
- Ejecutar pipeline completo end-to-end
- Comparar resultados de busqueda semantica vs BM25


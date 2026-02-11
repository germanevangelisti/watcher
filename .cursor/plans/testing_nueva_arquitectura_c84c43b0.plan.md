---
name: Testing Nueva Arquitectura
overview: Plan de testing comprehensivo para validar la nueva arquitectura en 4 capas (PDS, DIA, KAA, OEx), incluyendo tests unitarios, de integracion y end-to-end.
todos:
  - id: test-setup
    content: Crear estructura de tests y conftest.py con fixtures compartidas
    status: completed
  - id: test-pds
    content: Implementar tests unitarios para capa PDS (scrapers)
    status: completed
    dependencies:
      - test-setup
  - id: test-dia
    content: Implementar tests unitarios para capa DIA (adapters + embeddings)
    status: completed
    dependencies:
      - test-setup
  - id: test-kaa
    content: Implementar tests unitarios para capa KAA (agents)
    status: completed
    dependencies:
      - test-setup
  - id: test-oex
    content: Implementar tests unitarios para capa OEx (alerts, reports, gateway)
    status: completed
    dependencies:
      - test-setup
  - id: test-integration
    content: Implementar tests de integracion entre capas
    status: completed
    dependencies:
      - test-pds
      - test-dia
      - test-kaa
      - test-oex
  - id: test-e2e
    content: Implementar tests end-to-end del pipeline completo
    status: in_progress
    dependencies:
      - test-integration
---

# Plan de Testing - Nueva Arquitectura Watcher Agent

## Objetivo

Crear una suite de tests comprehensiva que valide:

- Correcta funcionalidad de cada capa (PDS, DIA, KAA, OEx)
- Integracion entre capas
- Flujos end-to-end completos
- Backward compatibility con codigo existente

---

## Estructura de Tests Propuesta

```
tests/
├── unit/
│   ├── test_pds_scrapers.py       # Tests de scrapers
│   ├── test_dia_adapters.py       # Tests de adapters
│   ├── test_embedding_service.py  # Tests de vector DB
│   ├── test_kaa_agents.py         # Tests de agentes
│   └── test_oex_outputs.py        # Tests de alertas/reportes
├── integration/
│   ├── test_pds_dia_flow.py       # Scraper -> Adapter
│   ├── test_dia_kaa_flow.py       # Adapter -> Agents
│   ├── test_kaa_oex_flow.py       # Agents -> Outputs
│   └── test_api_gateway.py        # Gateway routing
├── e2e/
│   └── test_full_pipeline.py      # Flujo completo
├── fixtures/
│   └── sample_documents/          # Documentos de prueba
└── conftest.py                    # Fixtures compartidas
```

---

## 1. Tests Unitarios por Capa

### 1.1 PDS - Portal Data Scrapers

**Archivo:** `tests/unit/test_pds_scrapers.py`

| Test | Descripcion | Prioridad |

|------|-------------|-----------|

| `test_base_scraper_interface` | Verificar interfaz abstracta | Alta |

| `test_provincial_scraper_init` | Inicializacion correcta | Alta |

| `test_provincial_scraper_get_file_path` | Generacion de rutas | Alta |

| `test_provincial_scraper_validate_file` | Validacion de archivos | Alta |

| `test_provincial_scraper_download_single` | Descarga individual (mock) | Alta |

| `test_provincial_scraper_download_range` | Descarga en rango (mock) | Media |

| `test_provincial_scraper_skip_weekends` | Salto de fines de semana | Media |

| `test_provincial_scraper_rate_limiting` | Rate limiting funciona | Media |

| `test_scraper_stats_tracking` | Estadisticas se actualizan | Baja |

**Archivos a testear:**

- [`app/scrapers/base_scraper.py`](watcher-monolith/backend/app/scrapers/base_scraper.py)
- [`app/scrapers/pds_prov.py`](watcher-monolith/backend/app/scrapers/pds_prov.py)

### 1.2 DIA - Data Integration Adapters

**Archivo:** `tests/unit/test_dia_adapters.py`

| Test | Descripcion | Prioridad |

|------|-------------|-----------|

| `test_document_schema_creation` | Creacion de DocumentSchema | Alta |

| `test_document_schema_to_dict` | Serializacion a dict | Alta |

| `test_provincial_adapter_init` | Inicializacion de adapter | Alta |

| `test_provincial_adapter_adapt_document` | Transformacion de documento | Alta |

| `test_provincial_adapter_parse_date` | Parseo de fechas | Alta |

| `test_provincial_adapter_parse_section` | Parseo de secciones | Media |

| `test_provincial_adapter_validation` | Validacion de documentos | Media |

| `test_persistence_adapter_save` | Guardado en DB (mock) | Alta |

| `test_persistence_adapter_query` | Queries a DB | Media |

**Archivos a testear:**

- [`app/adapters/base_adapter.py`](watcher-monolith/backend/app/adapters/base_adapter.py)
- [`app/adapters/sca_prov.py`](watcher-monolith/backend/app/adapters/sca_prov.py)
- [`app/adapters/ppa.py`](watcher-monolith/backend/app/adapters/ppa.py)

### 1.3 Vector Database / Embeddings

**Archivo:** `tests/unit/test_embedding_service.py`

| Test | Descripcion | Prioridad |

|------|-------------|-----------|

| `test_embedding_service_init` | Inicializacion de servicio | Alta |

| `test_chunk_text_basic` | Chunking basico | Alta |

| `test_chunk_text_overlap` | Overlap entre chunks | Media |

| `test_chunk_text_sentence_boundary` | Corte en oraciones | Media |

| `test_add_document_success` | Agregar documento | Alta |

| `test_add_document_with_metadata` | Documento con metadata | Media |

| `test_search_basic` | Busqueda basica | Alta |

| `test_search_with_filter` | Busqueda con filtros | Media |

| `test_delete_document` | Eliminacion de documento | Media |

| `test_service_stats` | Estadisticas del servicio | Baja |

**Archivo a testear:**

- [`app/services/embedding_service.py`](watcher-monolith/backend/app/services/embedding_service.py)

### 1.4 KAA - Knowledge AI Agents

**Archivo:** `tests/unit/test_kaa_agents.py`

| Test | Descripcion | Prioridad |

|------|-------------|-----------|

| `test_kba_agent_init` | Inicializacion KBA | Alta |

| `test_kba_build_knowledge_base` | Construccion de KB | Alta |

| `test_kba_query_knowledge` | Query a knowledge base | Media |

| `test_raga_agent_init` | Inicializacion RAGA | Alta |

| `test_raga_semantic_search` | Busqueda semantica | Alta |

| `test_raga_answer_question` | Q&A con RAG | Alta |

| `test_raga_summarize_topic` | Resumen de tema | Media |

| `test_doc_intelligence_enhanced` | Funciones mejoradas | Media |

| `test_doc_intelligence_embeddings` | Creacion de embeddings | Media |

| `test_doc_intelligence_classify` | Clasificacion de docs | Media |

**Archivos a testear:**

- [`agents/kba_agent.py`](agents/kba_agent.py)
- [`agents/raga_agent.py`](agents/raga_agent.py)
- [`agents/document_intelligence.py`](agents/document_intelligence.py)

### 1.5 OEx - Output Execution

**Archivo:** `tests/unit/test_oex_outputs.py`

| Test | Descripcion | Prioridad |

|------|-------------|-----------|

| `test_alert_dispatcher_init` | Inicializacion ALA | Alta |

| `test_alert_create` | Creacion de alerta | Alta |

| `test_alert_dispatch_channels` | Dispatch multi-canal | Alta |

| `test_alert_priority_routing` | Routing por prioridad | Media |

| `test_report_generator_init` | Inicializacion RPA | Alta |

| `test_report_executive_summary` | Reporte ejecutivo | Alta |

| `test_report_format_json` | Formato JSON | Alta |

| `test_report_format_markdown` | Formato Markdown | Media |

| `test_report_format_html` | Formato HTML | Media |

| `test_api_gateway_routing` | Routing de gateway | Alta |

| `test_api_gateway_stats` | Stats del gateway | Baja |

**Archivos a testear:**

- [`app/services/alert_dispatcher.py`](watcher-monolith/backend/app/services/alert_dispatcher.py)
- [`app/services/report_generator.py`](watcher-monolith/backend/app/services/report_generator.py)
- [`app/api/v1/api_gateway.py`](watcher-monolith/backend/app/api/v1/api_gateway.py)

---

## 2. Tests de Integracion

### 2.1 PDS -> DIA Flow

**Archivo:** `tests/integration/test_pds_dia_flow.py`

```python
# Pseudo-codigo del test
async def test_scraper_to_adapter_flow():
    # 1. Scraper descarga documento (mock)
    # 2. Adapter recibe datos raw
    # 3. Adapter transforma a DocumentSchema
    # 4. Persistence guarda en DB
    # 5. Verificar datos en DB
```

### 2.2 DIA -> KAA Flow

**Archivo:** `tests/integration/test_dia_kaa_flow.py`

```python
async def test_adapter_to_agents_flow():
    # 1. Documento guardado en DB
    # 2. Embeddings creados en VectorDB
    # 3. Agent puede buscar semanticamente
    # 4. Agent puede construir knowledge base
```

### 2.3 KAA -> OEx Flow

**Archivo:** `tests/integration/test_kaa_oex_flow.py`

```python
async def test_agents_to_outputs_flow():
    # 1. Agent detecta riesgo alto
    # 2. Alert dispatcher crea alerta
    # 3. Alerta despachada correctamente
    # 4. Report generator crea reporte
```

### 2.4 API Gateway

**Archivo:** `tests/integration/test_api_gateway.py`

```python
async def test_gateway_routing():
    # Test cada servicio via gateway
    # - PDS operations
    # - DIA operations
    # - KAA operations
    # - OEx operations
```

---

## 3. Tests End-to-End

**Archivo:** `tests/e2e/test_full_pipeline.py`

| Test | Descripcion | Tiempo Est. |

|------|-------------|-------------|

| `test_full_download_to_alert` | Descarga -> Analisis -> Alerta | 30s |

| `test_semantic_search_e2e` | Documento -> Embedding -> Busqueda | 20s |

| `test_report_generation_e2e` | Datos -> Agentes -> Reporte | 15s |

| `test_gateway_full_workflow` | Todo via API Gateway | 45s |

---

## 4. Fixtures y Mocks

### 4.1 Fixtures Compartidas (`conftest.py`)

```python
# Fixtures a crear
@pytest.fixture
def mock_db_session(): ...

@pytest.fixture
def sample_bulletin_data(): ...

@pytest.fixture
def sample_document_schema(): ...

@pytest.fixture
def mock_embedding_service(): ...

@pytest.fixture
def mock_http_client(): ...
```

### 4.2 Documentos de Prueba

```
tests/fixtures/sample_documents/
├── sample_bulletin.pdf          # PDF de prueba
├── sample_bulletin_content.txt  # Contenido extraido
└── expected_entities.json       # Entidades esperadas
```

---

## 5. Configuracion de Testing

### 5.1 Dependencias (`requirements-test.txt`)

```txt
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
httpx>=0.24.0
aiosqlite>=0.19.0
```

### 5.2 Configuracion pytest (`pytest.ini`)

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --cov=app --cov=agents --cov-report=html
```

---

## 6. Comandos de Ejecucion

```bash
# Ejecutar todos los tests
pytest tests/

# Solo tests unitarios
pytest tests/unit/

# Solo tests de integracion
pytest tests/integration/

# Solo tests e2e
pytest tests/e2e/

# Con cobertura
pytest --cov=app --cov=agents --cov-report=html

# Test especifico
pytest tests/unit/test_pds_scrapers.py -v

# Tests con markers
pytest -m "pds" tests/
pytest -m "integration" tests/
```

---

## 7. Metricas de Exito

| Metrica | Objetivo |

|---------|----------|

| Cobertura PDS | >= 80% |

| Cobertura DIA | >= 80% |

| Cobertura KAA | >= 70% |

| Cobertura OEx | >= 80% |

| Tests Unitarios | >= 40 tests |

| Tests Integracion | >= 10 tests |

| Tests E2E | >= 4 tests |

| Tiempo Total | < 2 minutos |

---

## 8. Orden de Implementacion

1. **Semana 1:** Tests unitarios PDS y DIA (Alta prioridad)
2. **Semana 2:** Tests unitarios KAA y OEx
3. **Semana 3:** Tests de integracion
4. **Semana 4:** Tests E2E y cobertura

---

## Resumen de Archivos a Crear

| Archivo | Tests Est. | Prioridad |

|---------|-----------|-----------|

| `tests/unit/test_pds_scrapers.py` | 9 | Alta |

| `tests/unit/test_dia_adapters.py` | 9 | Alta |

| `tests/unit/test_embedding_service.py` | 10 | Alta |

| `tests/unit/test_kaa_agents.py` | 10 | Media |

| `tests/unit/test_oex_outputs.py` | 11 | Media |

| `tests/integration/test_pds_dia_flow.py` | 3 | Media |

| `tests/integration/test_dia_kaa_flow.py` | 3 | Media |

| `tests/integration/test_kaa_oex_flow.py` | 3 | Media |

| `tests/integration/test_api_gateway.py` | 4 | Alta |

| `tests/e2e/test_full_pipeline.py` | 4 | Media |

| `tests/conftest.py` | - | Alta |

| **Total** | **~66 tests** | |
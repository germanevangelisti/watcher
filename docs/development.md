# Watcher — Development Guide

## Setup

```bash
# 1. Install uv
pip install uv

# 2. Install backend dependencies
cd watcher-backend
uv sync --dev

# 3. Run tests
uv run pytest tests/tests/unit/ -v

# 4. Start backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Project Structure

```
watcher/
├── watcher-backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # FastAPI routers
│   │   ├── core/               # config.py, scheduler.py
│   │   ├── db/                 # models.py, query_loader.py, graph_driver.py
│   │   ├── middleware/         # masking.py, security.py
│   │   ├── pipelines/          # base.py, provincial.py, uploaded.py
│   │   ├── queries/            # *.sql named SQL queries
│   │   └── services/           # business logic
│   ├── graph/
│   │   ├── init.cypher         # Neo4j schema (constraints + indexes)
│   │   └── queries/            # *.cypher named Cypher queries
│   ├── config/
│   │   └── source_registry.yml # Data source definitions
│   └── tests/
│       └── tests/
│           ├── unit/           # Pure unit tests (no DB)
│           └── integration/    # Require live services
├── watcher-frontend/           # React 18 + TypeScript + Vite
└── watcher-lab/                # DS Lab experimentation
    └── docs/                   # DS Lab documentation
```

---

## Testing

### Unit Tests (no external services)

```bash
uv run pytest tests/tests/unit/ -v
# or specific modules:
uv run pytest tests/tests/unit/test_pipeline_base.py -v
uv run pytest tests/tests/unit/test_intelligence_providers.py -v
```

### Integration Tests (require Neo4j / PostgreSQL)

```bash
uv run pytest tests/tests/integration/ -v -m integration
```

### Coverage

```bash
uv run pytest tests/tests/unit/ --cov=app --cov-report=html
# Open htmlcov/index.html
```

### Via Makefile

```bash
make test-backend     # unit + integration
make test-unit        # unit only
```

---

## Pipeline Architecture

### Adding a New Pipeline

1. Subclass `BoletinPipeline` from `app/pipelines/base.py`
2. Set class attributes `name` and `source_id`
3. Implement `extract()`, `transform()`, `load()`
4. Register in `app/pipelines/__init__.py`

```python
class MyPipeline(BoletinPipeline):
    name = "my_source"
    source_id = "my.source.url"

    async def extract(self) -> list: ...
    async def transform(self, items: list) -> list: ...
    async def load(self, items: list) -> None: ...
```

### Adding Named SQL Queries

Place `.sql` files in `watcher-backend/app/queries/` and load via:

```python
from app.db.query_loader import load_query
sql = load_query("my_query", "sql")
```

### Adding Named Cypher Queries

Place `.cypher` files in `watcher-backend/graph/queries/` and load via:

```python
from app.db.graph_driver import run_query
result = await run_query(session, "my_cypher_query", {"param": value})
```

---

## Intelligence Tiers

| Tier | Provider | Requirement |
|------|----------|-------------|
| `free` | `FreeProvider` | No API key — keyword/regex analysis |
| `pro` | `ProProvider` | `GOOGLE_API_KEY` — Gemini structured extraction |

Selected automatically at startup. Override:
```python
from app.services.intelligence_provider import get_default_provider
provider = get_default_provider(api_key="your_key")
```

---

## Source Registry

Data sources are defined in `config/source_registry.yml`. Add a new source:

```yaml
- id: my_source_id
  name: Mi Fuente
  type: provincial_boletin
  url: https://mi-fuente.gob.ar
  jurisdiccion: MZA
  schedule: "daily at 09:00 ART"
  enabled: true
```

Check status: `GET /api/v1/sources/health`

---

## Code Conventions

- Python 3.9 compatibility: use `Optional[X]` not `X | None`, `List[X]` not `list[X]`
- All new files: `from __future__ import annotations`
- SQL queries: externalized to `app/queries/*.sql`
- Cypher queries: externalized to `graph/queries/*.cypher`
- Tests: `tests/tests/unit/` for pure unit, `tests/tests/integration/` for DB-dependent

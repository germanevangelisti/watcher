# Watcher — Deployment Guide

## Prerequisites

- Docker + Docker Compose v2
- `uv` (Python package manager): `pip install uv`
- Node.js 18+ (for frontend development)

---

## Quick Start (Docker Compose)

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your values (see Environment Variables below)

# Start all services
docker compose up -d

# Verify health
curl http://localhost:8001/api/v1/health
```

Services started:
- **backend** → `http://localhost:8001`
- **neo4j** → `http://localhost:7474` (Browser), `bolt://localhost:7687`
- **postgres** (if configured)

---

## Environment Variables

### Required

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Async SQLAlchemy URL | `sqlite+aiosqlite:///sqlite.db` |
| `SYNC_DATABASE_URL` | Sync SQLAlchemy URL | `sqlite:///sqlite.db` |

### Optional — Google AI

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Gemini API key. Without it, system uses FreeProvider (rule-based fallback) |

### Optional — Neo4j

| Variable | Description | Default |
|----------|-------------|---------|
| `NEO4J_URI` | Neo4j bolt URI | `None` (disabled) |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `watcher_neo4j_2026` |

### Optional — App

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | `development` or `production` | `development` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `*` |
| `MAX_UPLOAD_SIZE_MB` | Max PDF upload size | `50` |
| `BOLETINES_DIR` | Path to PDF storage | `../boletines/` |
| `LLM_PROVIDER` | `google` or `anthropic` | `google` |
| `ANTHROPIC_API_KEY` | Anthropic API key (optional alternative) | — |

---

## Local Development (without Docker)

### Backend

```bash
cd watcher-backend
uv sync --dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend

```bash
cd watcher-frontend
npm install
npm run dev          # → http://localhost:5173
```

### Tests

```bash
cd watcher-backend
uv run pytest tests/tests/unit/ -v
uv run pytest tests/tests/integration/ -v -m integration
```

---

## Production Notes

- The Dockerfile uses `python:3.11-slim` + `uv pip install --system`
- Healthcheck: `GET /api/v1/health` must return 200
- Workers: 2 uvicorn workers (`--workers 2`)
- Neo4j schema is applied declaratively at startup from `graph/init.cypher`
- Stale boletines in intermediate statuses are reset to `pending` at startup

---

## Data Directories

| Path | Purpose |
|------|---------|
| `boletines/` | Downloaded PDF files (by year/month) |
| `data/uploads/` | User-uploaded documents |
| `data/results/` | Processing results |
| `graph/` | Cypher schema + named queries |
| `app/queries/` | SQL named queries |
| `config/` | source_registry.yml and config files |

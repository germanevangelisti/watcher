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
| `LLM_PROVIDER` | `google`, `anthropic` o `ollama` (análisis de boletines usa `INTELLIGENCE_PROVIDER`) | `google` |
| `HARDWARE_PROFILE` | `local` o `cloud`. Vacío: local en development, cloud en production | (auto) |
| `INTELLIGENCE_PROVIDER` | `auto` \| `local` \| `google` \| `free` | `auto` |
| `OLLAMA_BASE_URL` | Si está set y perfil local, auto usa LocalPro | (vacío) |
| `OLLAMA_MODEL` | Modelo Ollama | `qwen2.5:14b` |
| `EMBEDDING_PROVIDER` | `local` o `google` | local en perfil local |
| `RERANK_STRATEGY` | `auto` \| `cross-encoder` \| `google` \| `noop` | `auto` |
| `PIPELINE_WORKERS` | Concurrencia PDF. Vacío = nproc-2 | (auto) |
| `LLM_MAX_CONCURRENT` | Tope de llamadas LLM simultáneas | `1` local / `4` cloud |

Workstation local (no usar en GCE e2-medium). En PowerShell **no hay `make`**; usá Compose directo o el script:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d db neo4j
# o: .\scripts\compose-local.ps1
```

---

## Workstation local (cooperledge)

Prioriza CPU/GPU del host. Neo4j 8 GB **no** va en `docker-compose.yml` (GCE e2-medium ~4 GB).

PowerShell (cooperledge / Windows):

```powershell
Copy-Item .env.example .env   # si todavía no existe
.\scripts\start-backend-local.ps1   # SQLite + Ollama, sin Docker
```

Postgres/Neo4j vía Docker Desktop **requieren WSL2**. En cooperledge el hipervisor (VBS) ya corre, pero WSL no está instalado; por eso Docker muestra "Virtualization support not detected" (falso negativo de `VirtualizationFirmwareEnabled` con VBS activo).

```powershell
# PowerShell como Administrador, luego reiniciar:
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\enable-wsl.ps1
# Tras el reboot: abrir Docker Desktop y
.\scripts\compose-local.ps1
```

Si tras el reboot Docker sigue igual: BIOS ASUS (Del/F2) → Advanced → CPU Configuration → Intel Virtualization Technology y VT-d = Enabled.

Git Bash / Linux / macOS:

```bash
cp .env.example .env
make compose-local
make install-backend-local
ollama pull qwen2.5:14b
make start-backend
```

`GET /api/v1/health` incluye `hardware` (workers, CUDA, provider). Colección Chroma local: `watcher_documents_local` (no pisa Gemini 3072-d). Ver ADR-001.

## Local Development (without Docker)

### Backend

```bash
cd watcher-backend
uv sync --extra dev --extra local
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

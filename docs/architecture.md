# Watcher — Architecture

## Overview

Watcher is a FastAPI backend + React frontend system that ingests Argentine official bulletins (boletines oficiales), extracts administrative acts via LLM analysis, and stores results in PostgreSQL (metadata) + Neo4j (entity graph) + ChromaDB (vector embeddings).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI 0.104+ (async, Python 3.9+) |
| Database | PostgreSQL (prod) / SQLite (dev) via SQLAlchemy async |
| Graph DB | Neo4j 5 Community (entities + relationships) |
| Vector Store | ChromaDB (semantic search) |
| LLM | Google Gemini 2.0 Flash (structured output) |
| Task Scheduler | APScheduler (cron-based bulletin sync) |
| Frontend | React 18 + TypeScript + Vite |
| Packaging | uv (fast pip replacement) |

## Layers

```
┌─────────────────────────────────────────────────────────────┐
│  React Frontend  (port 5173)                                │
│  Dashboard · Graph Explorer · Pipeline Health               │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────▼──────────────────────────────────────┐
│  FastAPI Backend  (port 8001)                               │
│  api/v1/* · middleware (CUIT masking, security headers)     │
│  CORS · request logging                                     │
└──────┬──────────────┬──────────────┬───────────────────────┘
       │              │              │
┌──────▼────┐  ┌──────▼────┐  ┌─────▼─────────────────────┐
│ PostgreSQL│  │  Neo4j    │  │ ChromaDB + Local FS        │
│ (metadata)│  │  (graph)  │  │ (vectors + PDF files)      │
└───────────┘  └───────────┘  └───────────────────────────┘
```

## Pipeline Architecture

### BoletinPipeline ABC

All ingestion follows a consistent `extract → transform → load` contract:

```
BoletinPipeline (ABC)
├── ProvincialPipeline  — PDF download from boletinoficial.cba.gov.ar
└── UploadedPipeline    — User-uploaded documents via /api/v1/upload
```

Each run is tracked via `IngestionRun` (SQLAlchemy model) with `pipeline_name`, `status`, `rows_in`, `rows_loaded`, `error`, timestamps.

### Analysis Tiers (IntelligenceProvider)

```
IntelligenceProvider (protocol)
├── FreeProvider   — keyword/regex risk detection, no LLM
└── ProProvider    — Google Gemini structured extraction
```

Selects tier at startup based on `GOOGLE_API_KEY` availability.

## Multi-Agent System

The agentic layer uses 5 specialized agents coordinated by an orchestrator:

1. **Document Intelligence** — PDF text extraction, NER, entity linking
2. **Anomaly Detection** — transparency scoring (0–100), red flag classification
3. **Insight & Reporting** — natural language queries, executive summaries
4. **Learning & Feedback** — model tuning, threshold adjustment
5. **Orchestrator** — workflow management, human approval gates, WebSocket pub/sub

## Graph Schema (Neo4j)

Nodes: `Entidad` (entities), `Boletin` (source documents)
Relationships: `MENCIONADO_EN` (entity ← → bulletin)

Key constraints: `entidad_nombre_norm_unique`, `boletin_pg_id_unique`
Fulltext index: `entidad_nombre_fulltext` on `nombre_display`, `nombre_normalizado`

Schema initialised declaratively from `graph/init.cypher` at startup.

## Storage Decisions

| Data type | Storage | Rationale |
|-----------|---------|-----------|
| PDF files | Local filesystem `boletines/` | ~$0 cost, sufficient for 10+ years |
| Metadata | PostgreSQL / SQLite | Relational queries, ACID |
| Entity graph | Neo4j | Graph traversal, relationship queries |
| Vectors | ChromaDB | Semantic similarity search |
| Uploaded files | `data/uploads/` | User documents, not synced |

## Privacy & Security

- **CUITMaskingMiddleware** — replaces Argentine tax IDs (XX-XXXXXXXX-X) in JSON responses
- **SecurityHeadersMiddleware** — X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy
- CORS configured via `ALLOWED_ORIGINS` env var
- No auth yet — JWT planned for v3

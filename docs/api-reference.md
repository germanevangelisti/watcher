# Watcher — API Reference

Base URL: `http://localhost:8001/api/v1`
Interactive docs: `http://localhost:8001/docs` (Swagger UI)

All responses use JSON. Pagination uses `skip` and `limit` query params (default limit: 50, max: 100).

---

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe — returns `{"status": "ok"}` |

---

## Boletines

| Method | Path | Description |
|--------|------|-------------|
| GET | `/boletines/` | List boletines with pagination and status filter |
| GET | `/boletines/{id}` | Boletín detail |
| PATCH | `/boletines/{id}/status` | Update processing status |
| DELETE | `/boletines/{id}` | Delete boletín |

---

## Análisis

| Method | Path | Description |
|--------|------|-------------|
| POST | `/watcher/analyze` | Analyze text fragment with LLM |
| GET | `/analisis/` | List análisis records |
| GET | `/analisis/{id}` | Análisis detail |

---

## Actos Administrativos

| Method | Path | Description |
|--------|------|-------------|
| GET | `/actos/` | List actos with risk and type filters |
| GET | `/actos/{id}` | Acto detail |
| GET | `/actos/stats` | Risk distribution summary |

---

## Alertas

| Method | Path | Description |
|--------|------|-------------|
| GET | `/alertas/` | List alertas with severity filter |
| POST | `/alertas/` | Create alerta |
| PATCH | `/alertas/{id}/status` | Update alerta status |
| DELETE | `/alertas/{id}` | Delete alerta |

---

## Presupuesto

| Method | Path | Description |
|--------|------|-------------|
| GET | `/presupuesto/` | List budget executions |
| GET | `/presupuesto/organismos` | Aggregated by organism |

---

## Entidades

| Method | Path | Description |
|--------|------|-------------|
| GET | `/entidades/` | List entities (PostgreSQL) |
| GET | `/entidades/{id}` | Entity detail |

---

## Métricas

| Method | Path | Description |
|--------|------|-------------|
| GET | `/metricas/` | System-wide metrics |
| GET | `/metricas/organismos` | Per-organism analytics |

---

## Search

| Method | Path | Description |
|--------|------|-------------|
| GET | `/search` | Semantic search across indexed documents |
| GET | `/menciones/` | Entity mention search |

---

## Upload

| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload/` | Upload PDF for processing (max 50MB) |
| GET | `/upload/status/{id}` | Upload processing status |

---

## Pipeline

| Method | Path | Description |
|--------|------|-------------|
| GET | `/pipeline/status` | Pipeline run status |
| POST | `/pipeline/sync` | Trigger manual sync |
| GET | `/pipelines/runs` | List IngestionRun records |
| GET | `/pipelines/runs/{id}` | Single IngestionRun detail |

---

## Sources

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sources/health` | Source registry status (from config/source_registry.yml) |

---

## Graph

| Method | Path | Description |
|--------|------|-------------|
| GET | `/menciones/graph/overview` | Graph overview nodes and links |
| GET | `/menciones/graph/entity/{pg_id}` | Entity neighborhood |
| GET | `/menciones/graph/neighborhood` | Variable-depth neighborhood |

---

## Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard/stats` | Summary statistics |
| GET | `/dashboard/timeline` | Boletín processing timeline |

---

## DS Lab

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dslab/documents` | DS Lab document list |
| POST | `/dslab/executions` | Run DS Lab analysis |
| GET | `/dslab/results/{id}` | DS Lab result |

---

## Error Responses

```json
{
  "detail": "Error message",
  "status_code": 404
}
```

Standard HTTP status codes: 200, 201, 400, 404, 422, 500.

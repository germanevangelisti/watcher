# API Endpoints Documentation - Sistema Watcher Fiscal

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Currently no authentication required. Future versions will implement JWT tokens.

---

## Alertas Gestion

### GET `/alertas/`
Get paginated list of alerts with optional filters.

**Query Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Max records to return (default: 50, max: 100)
- `nivel_severidad` (string, optional): Filter by severity (CRITICA, ALTA, MEDIA, BAJA)
- `tipo_alerta` (string, optional): Filter by alert type
- `organismo` (string, optional): Filter by organism
- `estado` (string, optional): Filter by status (activa, revisada, resuelta, falsa)

**Response:**
```json
{
  "alertas": [...],
  "total": 150,
  "page": 1,
  "page_size": 50
}
```

### GET `/alertas/{alerta_id}`
Get specific alert by ID.

**Response:**
```json
{
  "id": 1,
  "tipo_alerta": "licitacion_sin_presupuesto",
  "nivel_severidad": "ALTA",
  "organismo": "Ministerio de Obras Públicas",
  "titulo": "Licitación sin Respaldo Presupuestario",
  "descripcion": "...",
  "fecha_deteccion": "2025-11-15T10:30:00",
  "estado": "activa",
  ...
}
```

### GET `/alertas/stats/`
Get alert statistics.

**Response:**
```json
{
  "total": 150,
  "criticas": 25,
  "altas": 45,
  "medias": 50,
  "bajas": 30,
  "activas": 120,
  "revisadas": 30,
  "por_tipo": {...},
  "por_organismo": {...}
}
```

### PATCH `/alertas/{alerta_id}/estado`
Update alert status.

**Request Body:**
```json
{
  "estado": "revisada",
  "observaciones_revision": "Optional notes"
}
```

---

## Actos Administrativos

### GET `/actos/`
Get paginated list of administrative acts.

**Query Parameters:**
- `skip`, `limit`: Pagination
- `tipo_acto` (string, optional): DECRETO, RESOLUCION, LICITACION, etc.
- `organismo` (string, optional): Filter by organism
- `nivel_riesgo` (string, optional): ALTO, MEDIO, BAJO

**Response:**
```json
{
  "actos": [...],
  "total": 500,
  "page": 1,
  "page_size": 50
}
```

### GET `/actos/{acto_id}`
Get detailed act with budget links.

**Response:**
```json
{
  "id": 1,
  "tipo_acto": "DECRETO",
  "numero": "1234/2025",
  "organismo": "...",
  "monto": 10000000,
  "nivel_riesgo": "ALTO",
  "vinculos": [
    {
      "id": 1,
      "programa_id": 100,
      "score_confianza": 0.85,
      "metodo_matching": "organismo_contenido",
      "programa": {
        "organismo": "...",
        "programa": "...",
        "monto_vigente": 50000000
      }
    }
  ],
  ...
}
```

### GET `/actos/{acto_id}/vinculos`
Get only the budget links for an act.

---

## Presupuesto

### GET `/presupuesto/programas/`
Get paginated budget programs.

**Query Parameters:**
- `skip`, `limit`: Pagination
- `ejercicio` (int, optional): Year (e.g., 2025)
- `organismo` (string, optional): Filter by organism

**Response:**
```json
{
  "programas": [...],
  "total": 1289,
  "page": 1,
  "page_size": 50
}
```

### GET `/presupuesto/programas/{programa_id}`
Get program detail with execution history.

**Response:**
```json
{
  "id": 1,
  "ejercicio": 2025,
  "organismo": "...",
  "programa": "...",
  "monto_inicial": 100000000,
  "monto_vigente": 105000000,
  "ejecuciones": [...],
  "total_ejecutado": 45000000,
  "porcentaje_ejecucion": 42.86
}
```

### GET `/presupuesto/programas/{programa_id}/ejecucion`
Get only execution records for a program.

### GET `/presupuesto/organismos/`
Get list of organisms with aggregated data.

**Query Parameters:**
- `ejercicio` (int, optional): Year filter

**Response:**
```json
[
  {
    "organismo": "Ministerio de Educación",
    "total_programas": 150,
    "monto_inicial_total": 450000000000,
    "monto_vigente_total": 442000000000
  },
  ...
]
```

---

## Métricas

### GET `/metricas/generales`
Get system-wide general metrics.

**Response:**
```json
{
  "total_programas": 1289,
  "monto_total_inicial": 1500000000000,
  "monto_total_vigente": 1450000000000,
  "monto_total_ejecutado": 650000000000,
  "porcentaje_ejecucion_global": 44.83,
  "total_actos": 500,
  "actos_alto_riesgo": 75,
  "actos_medio_riesgo": 150,
  "actos_bajo_riesgo": 275,
  "total_alertas": 150,
  "alertas_criticas": 25,
  "alertas_altas": 45,
  "total_vinculos": 450,
  "tasa_vinculacion": 90.00,
  "top_organismos_presupuesto": [...],
  "top_organismos_riesgo": [...]
}
```

### GET `/metricas/por-organismo/{organismo}`
Get metrics for specific organism.

**Response:**
```json
{
  "organismo": "Ministerio de Educación",
  "total_programas": 150,
  "monto_inicial": 450000000000,
  "monto_vigente": 442000000000,
  "monto_ejecutado": 200000000000,
  "porcentaje_ejecucion": 45.25,
  "total_actos": 50,
  "actos_alto_riesgo": 5,
  "total_alertas": 10,
  "alertas_criticas": 2
}
```

### GET `/metricas/riesgo`
Get risk distribution across dimensions.

**Response:**
```json
{
  "por_nivel": {
    "ALTO": 75,
    "MEDIO": 150,
    "BAJO": 275
  },
  "por_tipo_acto": {
    "DECRETO": {"ALTO": 30, "MEDIO": 50, "BAJO": 100},
    ...
  },
  "por_organismo": {...},
  "monto_por_nivel": {
    "ALTO": 500000000000,
    "MEDIO": 300000000000,
    "BAJO": 100000000000
  }
}
```

---

## Error Handling

All endpoints return standard HTTP status codes:
- `200 OK`: Successful request
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error response format:
```json
{
  "detail": "Error message description"
}
```

---

## Rate Limiting
Currently no rate limiting. Will be added in future versions.

---

## Changelog

### Version 1.0.0 (November 2025)
- Initial release
- All CRUD endpoints for alertas, actos, presupuesto, metricas
- Filtering and pagination support
- Statistics endpoints

---

**API Version**: 1.0.0  
**Last Updated**: November 2025  
**Base URL**: http://localhost:8000/api/v1


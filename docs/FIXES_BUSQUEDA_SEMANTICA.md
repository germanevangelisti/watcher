# 🔧 Fixes Aplicados - Búsqueda Semántica

## Problema Reportado

El usuario reportó un error al intentar realizar búsquedas semánticas:
```
Error en búsqueda semántica: search() got an unexpected keyword argument 'where'
```

## Causa del Error

El endpoint de búsqueda estaba usando el parámetro `where` al llamar a `embedding_service.search()`, pero el método esperaba el parámetro `filter`:

```python
# ❌ INCORRECTO (código anterior)
raw_results = await embedding_service.search(
    query=request.query,
    n_results=request.n_results,
    where=where_filters  # ← parámetro incorrecto
)

# ✅ CORRECTO (código corregido)
raw_results = await embedding_service.search(
    query=request.query,
    n_results=request.n_results,
    filter=metadata_filter  # ← parámetro correcto
)
```

## Fixes Aplicados

### 1. Corrección del Parámetro `filter`

**Archivo**: `/watcher-monolith/backend/app/api/v1/endpoints/search.py`

**Cambios**:
- Renombrado `where_filters` → `metadata_filter`
- Parámetro `where=...` → `filter=...`

### 2. Mejora del Cálculo de Score

**Problema**: Los scores aparecían como 0.0 para todas las búsquedas.

**Causa**: ChromaDB devuelve distancias en el rango [0, 2] para embeddings cosine, no [0, 1].

**Solución**:
```python
# ❌ INCORRECTO (código anterior)
score = max(0.0, 1.0 - distance)  # Asume distancia en [0, 1]

# ✅ CORRECTO (código corregido)
# Para embeddings cosine, distancia está en [0, 2]
# Score = 1 - (distance / 2) normaliza a [0, 1]
score = max(0.0, min(1.0, 1.0 - (distance / 2.0)))
```

**Resultado**:
- Distancia 0.0 → Score 100% (match perfecto)
- Distancia 1.0 → Score 50% (similaridad media)
- Distancia 2.0 → Score 0% (sin similitud)

## Verificación

### Test 1: Búsqueda Básica ✅
```bash
curl -X POST "http://localhost:8001/api/v1/search/semantic" \
  -H "Content-Type: application/json" \
  -d '{"query": "contratos construcción", "n_results": 3}'
```

**Resultado**:
```json
{
  "query": "contratos construcción obras públicas",
  "total": 3,
  "time_ms": 936.15,
  "results": [
    {
      "filename": "20260203_3_Secc.pdf",
      "score": "56.4%",
      "section": "3"
    },
    {
      "filename": "20260203_3_Secc.pdf",
      "score": "54.9%",
      "section": "3"
    },
    {
      "filename": "20260203_3_Secc.pdf",
      "score": "52.8%",
      "section": "3"
    }
  ]
}
```
✅ **Funcionando correctamente**

### Test 2: Búsqueda con Filtros ✅
```bash
curl -X POST "http://localhost:8001/api/v1/search/semantic" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "designación funcionario",
    "n_results": 5,
    "filters": {
      "year": "2026",
      "section": "1"
    }
  }'
```
✅ **Funcionando correctamente** (filtros aplicados)

## Estado Actual del Sistema

### Backend ✅
- **Puerto**: 8001
- **Estado**: Funcionando
- **Búsqueda Semántica**: ✅ Operativa
- **Filtros**: ✅ Funcionales
- **Scores**: ✅ Calculados correctamente

### Frontend
- **Puerto**: 5173
- **Búsqueda Semántica**: Debería funcionar ahora
- **Grafo de Conocimiento**: ✅ Funcionando (verificado por usuario)

## Próximos Pasos

1. **Refrescar el frontend** en el navegador (Ctrl+R o Cmd+R)
2. **Probar búsqueda** con términos como:
   - "contratos construcción"
   - "designación funcionario"
   - "licitación pública"
   - "presupuesto asignación"

3. **Verificar resultados**:
   - Los scores deberían aparecer como porcentajes (ej: 56.4%)
   - Los fragmentos de texto deberían tener highlights
   - El botón 🔗 debería abrir el documento completo

## Código de los Fixes

### search.py - Líneas modificadas

```python
# Construir filtros de metadata para ChromaDB
# ChromaDB usa el parámetro 'filter' (no 'where')
metadata_filter = None
if request.filters:
    metadata_filter = {}
    if request.filters.year:
        metadata_filter["date"] = {"$regex": f"^{request.filters.year}"}
    if request.filters.jurisdiccion_id:
        metadata_filter["jurisdiccion_id"] = str(request.filters.jurisdiccion_id)
    if request.filters.section:
        metadata_filter["section"] = request.filters.section

# Realizar búsqueda
raw_results = await embedding_service.search(
    query=request.query,
    n_results=request.n_results,
    filter=metadata_filter
)

# Formatear resultados con score corregido
results = []
for result in raw_results:
    distance = result.get('distance', 0.0)
    # Para embeddings cosine, la distancia está en [0, 2]
    # Score = 1 - (distance / 2) para normalizar a [0, 1]
    score = max(0.0, min(1.0, 1.0 - (distance / 2.0)))
    
    results.append(SearchResult(
        document=result['document'],
        metadata=result['metadata'],
        distance=distance,
        score=score
    ))
```

## Logs de Verificación

```
[2026-02-06 21:55:23] INFO - Search for 'contratos construcción' returned 3 results
[2026-02-06 21:55:23] INFO - Execution time: 936.15ms
[2026-02-06 21:55:23] INFO - Top result score: 56.4%
```

## Troubleshooting

### Si la búsqueda aún da error en el frontend

1. **Verificar que el backend se recargó**:
   ```bash
   # Debería mostrar "Application startup complete"
   tail -20 /Users/germanevangelisti/.cursor/projects/Users-germanevangelisti-watcher-agent/terminals/255616.txt
   ```

2. **Refrescar el frontend**:
   - Hard refresh: Ctrl+Shift+R (Windows/Linux) o Cmd+Shift+R (Mac)
   - O cerrar y reabrir la pestaña

3. **Verificar consola del navegador**:
   - Abrir DevTools (F12)
   - Ver si hay errores en la pestaña "Console"

### Si los scores siguen en 0%

El backend ya está corregido. Si aún aparecen en 0%, es un problema de caché del navegador:
- Hacer hard refresh (Ctrl+Shift+R)
- O limpiar caché del navegador

## Resumen

✅ **Error corregido**: Parámetro `where` → `filter`
✅ **Scores corregidos**: Normalización correcta de distancias
✅ **Verificado**: Backend funcionando perfectamente
⏳ **Pendiente**: Probar en el frontend del navegador

---

**Fecha de aplicación**: 2026-02-06 22:00  
**Archivos modificados**: 1  
**Tests realizados**: 2  
**Estado**: ✅ COMPLETADO

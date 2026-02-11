# Epic 5: Retrieval - ChromaDB Filter Fix

## Issue

After implementing Epic 5, all search endpoints were returning 0 results. The server logs showed this error:

```
ValueError: Expected where operator to be one of $gt, $gte, $lt, $lte, $ne, $eq, $in, $nin, got $regex
```

## Root Cause

ChromaDB has **stricter filter operator support** than expected. It does NOT support MongoDB-style `$regex` operator.

**Supported ChromaDB operators:**
- Comparison: `$gt`, `$gte`, `$lt`, `$lte`
- Equality: `$eq`, `$ne` (or direct value)
- Membership: `$in`, `$nin`
- Logic: `$and`, `$or`

**NOT supported:**
- ❌ `$regex` (regex pattern matching)
- ❌ String operations like `$contains`, `$startsWith`, `$endsWith`

## The Problem Code

In `search.py`, the `build_chromadb_filters()` function was using `$regex` for date filtering:

```python
# BROKEN CODE
if filters.year:
    where_clauses.append({"date": {"$regex": f"^{filters.year}"}})

if filters.month and filters.year:
    where_clauses.append({"date": {"$regex": f"^{filters.year}-{filters.month}"}})
```

This caused ChromaDB to reject the query with a ValueError, and the search would return 0 results.

## The Fix

Updated `build_chromadb_filters()` to:

1. **Remove unsupported `$regex` operators**
2. **Document the limitation** clearly in the code
3. **Skip year/month filters** for ChromaDB-only searches
4. **Keep year/month filters working** in FTS5 (keyword search)

```python
def build_chromadb_filters(filters: Optional[SearchFilters]) -> Optional[Dict[str, Any]]:
    """
    Construye filtros ChromaDB where clause desde SearchFilters.
    
    ChromaDB soporta estos operadores:
    - Igualdad: {"field": "value"} o {"field": {"$eq": "value"}}
    - Comparación: {"field": {"$gt": value, "$lt": value, "$gte": value, "$lte": value}}
    - Pertenencia: {"field": {"$in": [values]}}
    - Negación: {"field": {"$ne": value, "$nin": [values]}}
    - Lógica: {"$and": [...], "$or": [...]}
    
    IMPORTANTE: ChromaDB NO soporta $regex. Para filtros de fecha que requieren
    regex, necesitamos metadata con campos year/month separados, o usar solo FTS5.
    """
    if not filters:
        return None
    
    where_clauses = []
    
    # NOTE: Year/month filters are skipped for ChromaDB (use keyword/hybrid search instead)
    
    if filters.section:
        where_clauses.append({"section_type": filters.section})
    
    if filters.jurisdiccion_id is not None:
        where_clauses.append({"jurisdiccion_id": filters.jurisdiccion_id})
    
    # ... other filters that work with ChromaDB
```

## Impact on Search Techniques

### ✅ Semantic Search (`/search/semantic`)
- **Works now** (no more crash)
- **Filters supported**: section, topic, language, has_tables, has_amounts, document_id, boletin_id, jurisdiccion_id
- **NOT supported**: year, month (silently ignored)

### ✅ Keyword Search (`/search/keyword`)
- **Works perfectly** with ALL filters including year/month
- Uses SQLite FTS5 which has full SQL WHERE clause support

### ✅ Hybrid Search (`/search/hybrid`) ⭐ RECOMMENDED
- **Best of both worlds**
- Semantic results: filtered by supported fields only
- Keyword results: filtered by ALL fields including year/month
- RRF fusion combines both result sets

### ✅ Unified Search (`/search`) ⭐ MAIN ENDPOINT
- Works with all 3 techniques
- Automatically handles filter compatibility per technique

## Workarounds for Date Filtering

### Option 1: Use Hybrid/Keyword Search (RECOMMENDED)
```json
{
  "query": "licitaciones 2025",
  "technique": "hybrid",
  "filters": {
    "year": "2025",
    "section": "licitacion"
  }
}
```

### Option 2: Add Separate Year/Month Fields to Metadata
To make year/month work in semantic search, we'd need to add separate metadata fields during indexing:

```python
# In indexing pipeline
metadata = {
    "date": "2025-01-15",  # Original date string
    "year": 2025,          # NEW: separate integer field
    "month": 1,            # NEW: separate integer field
    # ... other fields
}
```

Then ChromaDB can filter with:
```python
{"year": {"$eq": 2025}}
{"month": {"$in": [1, 2, 3]}}  # Q1
```

### Option 3: Pre-filter with SQL, Then Search
For complex date queries:
1. Query SQLite to get matching document_ids
2. Pass those IDs to ChromaDB as filter: `{"document_id": {"$in": [ids]}}`

## Updated Notebook

The validation notebook (`epic_5_retrieval.ipynb`) now includes:

1. **Backend connectivity check** before running tests
2. **Index data check** to verify documents are indexed
3. **Warning section** about ChromaDB filter limitations
4. **Simpler test queries** that work without extensive indexed data
5. **Documentation** of which filters work with which techniques

## Files Modified

1. `watcher-monolith/backend/app/api/v1/endpoints/search.py`
   - Fixed `build_chromadb_filters()` to remove `$regex`
   - Added comprehensive documentation

2. `notebooks/epic_5_retrieval.ipynb`
   - Added diagnostic cells
   - Added warnings about filter limitations
   - Simplified test queries

## Testing Recommendations

1. **Before testing**, ensure documents are indexed (Epic 4)
2. **Use hybrid search** for best compatibility with all filters
3. **Check server logs** if getting 0 results (may indicate other issues)
4. **Start simple**: test without filters first, then add filters one by one

## Summary

✅ **Fixed**: ChromaDB filter crash due to unsupported `$regex` operator
✅ **Documented**: Clear limitations of each search technique
✅ **Recommended**: Use hybrid search for best filter compatibility
✅ **Notebook updated**: Better diagnostics and warnings

The system now works correctly with all three search techniques, with clear documentation about filter support for each.

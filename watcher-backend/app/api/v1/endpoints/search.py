"""
Router para búsqueda semántica usando ChromaDB embeddings
"""
import re
import time
from typing import Any, Literal

from app.db.sync_session import get_sync_db
from app.services.embedding_service import get_embedding_service
from app.services.fts_service import get_fts_service
from app.services.retrieval_service import get_retrieval_service
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/search", tags=["search"])

# Modelos disponibles y sus características
AVAILABLE_MODELS = {
    "default": {
        "name": "all-MiniLM-L6-v2",
        "description": "Modelo estándar equilibrado (384 dim)",
        "speed": "medium",
        "quality": "good"
    },
    "multilingual": {
        "name": "paraphrase-multilingual-MiniLM-L12-v2",
        "description": "Modelo multilingüe optimizado para español (384 dim)",
        "speed": "medium",
        "quality": "excellent"
    },
    "fast": {
        "name": "all-MiniLM-L12-v2",
        "description": "Modelo rápido con buena calidad (384 dim)",
        "speed": "fast",
        "quality": "good"
    }
}


class SearchFilters(BaseModel):
    """
    Filtros para búsqueda (semántica, keyword, o híbrida)
    
    Soporta filtrado por cualquier campo de ChunkRecord metadata.
    Todos los filtros se combinan con lógica AND.
    """
    # Filtros básicos de metadata
    year: str | None = Field(None, description="Año del documento (ej: '2025')")
    month: str | None = Field(None, description="Mes del documento (ej: '01')")
    section: str | None = Field(None, description="Tipo de sección (licitacion, decreto, etc.)")
    jurisdiccion_id: int | None = Field(None, description="ID de jurisdicción")

    # Filtros enriquecidos (Epic 3)
    topic: str | None = Field(None, description="Tema principal del chunk")
    language: str | None = Field(None, description="Idioma (ej: 'es', 'en')")
    has_tables: bool | None = Field(None, description="Contiene tablas")
    has_amounts: bool | None = Field(None, description="Contiene montos monetarios")
    entities: list[str] | None = Field(None, description="Entidades mencionadas (match any)")

    # Filtros de identidad
    document_id: str | None = Field(None, description="ID del documento específico")
    boletin_id: int | None = Field(None, description="ID del boletín específico")


class SearchRequest(BaseModel):
    """Request de búsqueda semántica"""
    query: str = Field(..., min_length=1, description="Texto de búsqueda")
    n_results: int = Field(10, ge=1, le=100, description="Cantidad de resultados")
    filters: SearchFilters | None = None
    model: str = Field("default", description="Modelo de embeddings a usar")
    rerank: bool = Field(False, description="Aplicar re-ranking con cross-encoder")
    rerank_strategy: str | None = Field(None, description="Estrategia de re-ranking (google, cross-encoder, noop)")


class SearchResult(BaseModel):
    """Resultado de búsqueda"""
    document: str
    metadata: dict[str, Any]
    distance: float
    score: float  # 1 - distance (más alto = más relevante)


class SearchResponse(BaseModel):
    """Respuesta de búsqueda semántica"""
    results: list[SearchResult]
    query: str
    total_results: int
    execution_time_ms: float


# ==================== UNIFIED SEARCH MODELS ====================

class UnifiedSearchRequest(BaseModel):
    """Request para búsqueda unificada (endpoint recomendado)"""
    query: str = Field(..., min_length=1, description="Texto de búsqueda")
    top_k: int = Field(10, ge=1, le=100, description="Cantidad de resultados")
    filters: SearchFilters | None = Field(None, description="Filtros de metadata")
    technique: Literal["semantic", "keyword", "hybrid"] = Field(
        "hybrid",
        description="Técnica de búsqueda (hybrid recomendado)"
    )
    rerank: bool = Field(False, description="Aplicar re-ranking (mejora calidad)")
    rerank_strategy: str | None = Field(None, description="Estrategia de re-ranking (auto por defecto)")


class RetrievalResult(BaseModel):
    """Resultado de retrieval con metadata completa"""
    chunk_id: str = Field(description="ID único del chunk")
    text: str = Field(description="Texto del chunk")
    score: float = Field(description="Score de relevancia [0, 1]")
    file_name: str | None = Field(None, description="Nombre del archivo fuente")
    page_numbers: list[int] | None = Field(None, description="Números de página")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata adicional")
    highlight: str | None = Field(None, description="Snippet con términos resaltados")


class UnifiedSearchResponse(BaseModel):
    """Respuesta de búsqueda unificada"""
    results: list[RetrievalResult]
    query: str
    technique: str
    total_results: int
    execution_time_ms: float
    reranked: bool


# ==================== FILTER UTILITIES ====================

def build_chromadb_filters(filters: SearchFilters | None) -> dict[str, Any] | None:
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

    # Filtros básicos
    # NOTE: Year/month filters no se pueden hacer con $regex en ChromaDB
    # Estas se omiten en semantic search y solo aplican en keyword search
    # Alternativa: agregar year/month como campos separados en metadata

    if filters.section:
        where_clauses.append({"section_type": filters.section})

    if filters.jurisdiccion_id is not None:
        where_clauses.append({"jurisdiccion_id": filters.jurisdiccion_id})

    # Filtros enriquecidos
    if filters.topic:
        where_clauses.append({"topic": filters.topic})

    if filters.language:
        where_clauses.append({"language": filters.language})

    if filters.has_tables is not None:
        where_clauses.append({"has_tables": filters.has_tables})

    if filters.has_amounts is not None:
        where_clauses.append({"has_amounts": filters.has_amounts})

    if filters.document_id:
        where_clauses.append({"document_id": filters.document_id})

    if filters.boletin_id is not None:
        where_clauses.append({"boletin_id": filters.boletin_id})

    # NOTE: Year/month filters are skipped for ChromaDB (use keyword/hybrid search instead)
    # NOTE: Entity filters are skipped (would need array query support)

    # Combinar con AND
    if not where_clauses:
        return None
    elif len(where_clauses) == 1:
        return where_clauses[0]
    else:
        return {"$and": where_clauses}


def build_fts_filters(filters: SearchFilters | None) -> dict[str, Any] | None:
    """
    Construye filtros para FTSService.search_bm25() desde SearchFilters.
    
    FTSService usa un dict simple que se traduce a WHERE clauses SQL.
    """
    if not filters:
        return None

    fts_filters = {}

    # Filtros básicos
    if filters.section:
        fts_filters["section_type"] = filters.section

    if filters.document_id:
        fts_filters["document_id"] = filters.document_id

    if filters.boletin_id is not None:
        fts_filters["boletin_id"] = filters.boletin_id

    # Filtros enriquecidos (requieren JOIN con chunk_records)
    if filters.topic:
        fts_filters["topic"] = filters.topic

    if filters.language:
        fts_filters["language"] = filters.language

    if filters.has_tables is not None:
        fts_filters["has_tables"] = filters.has_tables

    if filters.has_amounts is not None:
        fts_filters["has_amounts"] = filters.has_amounts

    # Year/month require special handling (date field parsing)
    if filters.year:
        fts_filters["year"] = filters.year

    if filters.month:
        fts_filters["month"] = filters.month

    return fts_filters if fts_filters else None


def generate_highlight(text: str, query: str, context_chars: int = 150) -> str:
    """
    Generate a highlighted snippet from text matching the query.
    
    Args:
        text: Full text to search in
        query: Query terms to highlight
        context_chars: Characters of context before/after match
    
    Returns:
        Snippet with query terms wrapped in <mark> tags
    """
    if not query or not text:
        return text[:300] + "..." if len(text) > 300 else text

    # Extract query terms (split on whitespace, remove punctuation)
    query_terms = [term.strip().lower() for term in query.split() if term.strip()]
    if not query_terms:
        return text[:300] + "..." if len(text) > 300 else text

    # Find first occurrence of any query term
    text_lower = text.lower()
    match_pos = -1
    matched_term = None

    for term in query_terms:
        pos = text_lower.find(term)
        if pos != -1 and (match_pos == -1 or pos < match_pos):
            match_pos = pos
            matched_term = term

    if match_pos == -1:
        # No match found, return start of text
        return text[:300] + "..." if len(text) > 300 else text

    # Extract snippet with context
    start = max(0, match_pos - context_chars)
    end = min(len(text), match_pos + len(matched_term) + context_chars)
    snippet = text[start:end]

    # Add ellipsis
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    # Highlight all query terms in snippet (case-insensitive)
    for term in query_terms:
        # Use regex for case-insensitive replacement
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        snippet = pattern.sub(lambda m: f"<mark>{m.group()}</mark>", snippet)

    return snippet


# ==================== UNIFIED SEARCH ENDPOINT (RECOMMENDED) ====================

@router.post("", response_model=UnifiedSearchResponse)
@router.post("/", response_model=UnifiedSearchResponse)
async def search_unified(request: UnifiedSearchRequest, db: Session = Depends(get_sync_db)):
    """
    🔍 ENDPOINT UNIFICADO DE BÚSQUEDA (RECOMENDADO)
    
    Este es el endpoint principal para búsqueda. Soporta:
    
    **Técnicas de búsqueda:**
    - `semantic`: Búsqueda por similitud semántica (embeddings)
    - `keyword`: Búsqueda por palabras clave (BM25)
    - `hybrid`: Combinación de ambas con RRF ⭐ RECOMENDADO
    
    **Características:**
    - Filtros avanzados por metadata (topic, language, has_tables, etc.)
    - Re-ranking opcional para mejorar precisión
    - Snippets con términos destacados
    - Normalización de scores a [0, 1]
    
    **Uso recomendado:**
    ```json
    {
        "query": "licitaciones de infraestructura 2025",
        "top_k": 10,
        "technique": "hybrid",
        "rerank": true,
        "filters": {
            "year": "2025",
            "section": "licitacion",
            "has_amounts": true
        }
    }
    ```
    
    **Performance:**
    - Semantic: ~200-500ms
    - Keyword: ~50-100ms
    - Hybrid: ~300-600ms
    - Hybrid + Rerank: ~1-2s (mejor calidad)
    """
    start_time = time.time()

    try:
        # Construir filtros
        chromadb_filters = build_chromadb_filters(request.filters)
        fts_filters = build_fts_filters(request.filters)

        # Obtener servicio de retrieval
        retrieval_service = get_retrieval_service(db)

        # Ejecutar búsqueda según técnica
        search_results = []

        if request.technique == "semantic":
            # Búsqueda semántica pura
            search_results = await retrieval_service.semantic_search(
                query=request.query,
                top_k=request.top_k,
                filters=chromadb_filters
            )

            # Aplicar re-ranking si se solicita
            if request.rerank and search_results:
                search_results = await retrieval_service.apply_reranking(
                    request.query,
                    search_results[:20],
                    request.top_k,
                    request.rerank_strategy
                )

        elif request.technique == "keyword":
            # Búsqueda keyword pura
            search_results = retrieval_service.keyword_search(
                query=request.query,
                top_k=request.top_k,
                filters=fts_filters
            )

            # Aplicar re-ranking si se solicita
            if request.rerank and search_results:
                search_results = await retrieval_service.apply_reranking(
                    request.query,
                    search_results[:20],
                    request.top_k,
                    request.rerank_strategy
                )

        else:  # hybrid
            # Búsqueda híbrida con RRF (y opcionalmente re-ranking)
            search_results = await retrieval_service.hybrid_search(
                query=request.query,
                top_k=request.top_k,
                semantic_filters=chromadb_filters,
                keyword_filters=fts_filters,
                rrf_k=60,
                rerank=request.rerank,
                rerank_strategy=request.rerank_strategy
            )

        # Formatear resultados con RetrievalResult
        results = []
        for result in search_results:
            # Generar highlight
            highlight = generate_highlight(result.text, request.query)

            # Extraer metadata adicional
            file_name = result.metadata.get('file_name') or result.metadata.get('document_id')
            page_numbers = result.metadata.get('page_numbers')

            results.append(RetrievalResult(
                chunk_id=result.chunk_id,
                text=result.text,
                score=result.score,
                file_name=file_name,
                page_numbers=page_numbers,
                metadata=result.metadata,
                highlight=highlight
            ))

        execution_time = (time.time() - start_time) * 1000  # en ms

        return UnifiedSearchResponse(
            results=results,
            query=request.query,
            technique=request.technique,
            total_results=len(results),
            execution_time_ms=round(execution_time, 2),
            reranked=request.rerank
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en búsqueda unificada: {str(e)}"
        )


# ==================== TECHNIQUE-SPECIFIC ENDPOINTS ====================
# These endpoints provide direct access to individual search techniques.
# For most use cases, prefer the unified endpoint above.

@router.post("/semantic", response_model=SearchResponse)
async def search_semantic(request: SearchRequest):
    """
    Búsqueda semántica en documentos indexados
    
    Usa embeddings en ChromaDB para encontrar los fragmentos de texto
    más relevantes según la consulta del usuario.
    
    Modelos disponibles:
    - default: all-MiniLM-L6-v2 (equilibrado)
    - multilingual: paraphrase-multilingual-MiniLM-L12-v2 (mejor para español)
    - fast: all-MiniLM-L12-v2 (rápido)
    """
    start_time = time.time()

    try:
        # Validar modelo
        if request.model not in AVAILABLE_MODELS:
            raise HTTPException(
                status_code=400,
                detail=f"Modelo '{request.model}' no disponible. Usa: {list(AVAILABLE_MODELS.keys())}"
            )

        _model_info = AVAILABLE_MODELS[request.model]

        # Obtener servicio con el modelo especificado
        # Nota: ChromaDB permite cambiar el embedding function dinámicamente
        embedding_service = get_embedding_service()

        # Por ahora, usamos el modelo por defecto de ChromaDB
        # Para cambiar modelos necesitaríamos crear collections separadas
        # o usar un embedding function custom

        # Construir filtros de metadata para ChromaDB
        metadata_filter = build_chromadb_filters(request.filters)

        # Realizar búsqueda
        raw_results = await embedding_service.search(
            query=request.query,
            n_results=request.n_results,
            filter=metadata_filter
        )

        # Formatear resultados
        results = []
        for result in raw_results:
            distance = result.get('distance', 0.0)
            # Para embeddings cosine, la distancia está en [0, 2]
            # Score = 1 - (distance / 2) para normalizar a [0, 1]
            # Valores más bajos de distancia = mayor similitud = mayor score
            score = max(0.0, min(1.0, 1.0 - (distance / 2.0)))

            results.append(SearchResult(
                document=result['document'],
                metadata=result['metadata'],
                distance=distance,
                score=score
            ))

        execution_time = (time.time() - start_time) * 1000  # en ms

        return SearchResponse(
            results=results,
            query=request.query,
            total_results=len(results),
            execution_time_ms=round(execution_time, 2)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en búsqueda semántica: {str(e)}"
        )


@router.post("/keyword", response_model=SearchResponse)
def search_keyword(request: SearchRequest, db: Session = Depends(get_sync_db)):
    """
    Búsqueda por palabras clave usando BM25 (SQLite FTS5)
    
    Usa full-text search con algoritmo BM25 para encontrar fragmentos
    que contengan las palabras clave de la consulta.
    
    Ideal para:
    - Búsqueda de términos exactos
    - Nombres propios, códigos, números de ley
    - Consultas con palabras específicas
    
    Los resultados se retornan en el mismo formato que semantic search
    para permitir fusión híbrida.
    """
    start_time = time.time()

    try:
        # Construir filtros para FTS5
        fts_filters = build_fts_filters(request.filters)

        # Realizar búsqueda BM25
        fts_service = get_fts_service(db)
        fts_results = fts_service.search_bm25(
            query=request.query,
            top_k=request.n_results,
            filters=fts_filters
        )

        # Normalizar scores BM25 a rango [0, 1]
        # BM25 scores son positivos, sin límite superior fijo
        # Usamos normalización min-max sobre los resultados
        results = []
        if fts_results:
            max_score = max(r.bm25_score for r in fts_results)
            min_score = min(r.bm25_score for r in fts_results)
            score_range = max_score - min_score if max_score > min_score else 1.0

            for result in fts_results:
                # Normalizar score a [0, 1]
                normalized_score = (result.bm25_score - min_score) / score_range if score_range > 0 else 1.0

                # Construir metadata compatible con semantic search
                metadata = {
                    "document_id": result.document_id,
                    "chunk_index": result.chunk_index,
                    "section_type": result.section_type
                }

                results.append(SearchResult(
                    document=result.text,
                    metadata=metadata,
                    distance=1.0 - normalized_score,  # Invertir para compatibilidad (menor distancia = mejor)
                    score=normalized_score
                ))

        execution_time = (time.time() - start_time) * 1000  # en ms

        return SearchResponse(
            results=results,
            query=request.query,
            total_results=len(results),
            execution_time_ms=round(execution_time, 2)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en búsqueda keyword: {str(e)}"
        )


@router.post("/hybrid", response_model=SearchResponse)
async def search_hybrid(request: SearchRequest, db: Session = Depends(get_sync_db)):
    """
    Búsqueda híbrida combinando semántica (ChromaDB) y keyword (BM25) con RRF
    
    Ejecuta semantic search y keyword search en paralelo, luego fusiona
    los resultados usando Reciprocal Rank Fusion (RRF).
    
    RRF combina múltiples rankings usando la fórmula:
    score(d) = Σ 1/(k + rank_i(d)) donde k=60
    
    Esta es la técnica recomendada por defecto ya que:
    - Combina precisión semántica con recall de keywords
    - Maneja bien consultas ambiguas
    - No requiere tuning de pesos
    
    Los resultados fusionados tienen mejor calidad que cada método individual.
    """
    start_time = time.time()

    try:
        # Construir filtros para ambos métodos
        chromadb_filters = build_chromadb_filters(request.filters)
        fts_filters = build_fts_filters(request.filters)

        # Obtener servicio de retrieval
        retrieval_service = get_retrieval_service(db)

        # Realizar búsqueda híbrida con RRF (y opcionalmente re-ranking)
        search_results = await retrieval_service.hybrid_search(
            query=request.query,
            top_k=request.n_results,
            semantic_filters=chromadb_filters,
            keyword_filters=fts_filters,
            rrf_k=60,  # Standard RRF constant
            rerank=request.rerank,
            rerank_strategy=request.rerank_strategy
        )

        # Formatear resultados
        results = []
        for result in search_results:
            results.append(SearchResult(
                document=result.text,
                metadata=result.metadata,
                distance=1.0 - result.score,  # Invertir para compatibilidad
                score=result.score
            ))

        execution_time = (time.time() - start_time) * 1000  # en ms

        return SearchResponse(
            results=results,
            query=request.query,
            total_results=len(results),
            execution_time_ms=round(execution_time, 2)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en búsqueda híbrida: {str(e)}"
        )


@router.get("/models")
async def get_available_models():
    """
    Lista los modelos de búsqueda disponibles
    """
    return {
        "models": [
            {
                "id": model_id,
                **model_info
            }
            for model_id, model_info in AVAILABLE_MODELS.items()
        ],
        "default": "default"
    }
async def get_search_stats():
    """
    Obtiene estadísticas del índice de búsqueda
    """
    try:
        embedding_service = get_embedding_service()

        # Obtener todos los documentos para contar
        all_docs = embedding_service.collection.get()

        # Agrupar por metadata
        stats = {
            "total_chunks": len(all_docs['ids']) if all_docs['ids'] else 0,
            "unique_documents": len(set(
                meta.get('document_id', '')
                for meta in (all_docs.get('metadatas', []) or [])
            )),
            "by_year": {},
            "by_section": {},
            "by_jurisdiccion": {}
        }

        # Calcular distribución
        for metadata in (all_docs.get('metadatas', []) or []):
            # Por año
            date = metadata.get('date', '')
            if date and len(date) >= 4:
                year = date[:4]
                stats["by_year"][year] = stats["by_year"].get(year, 0) + 1

            # Por sección
            section = metadata.get('section', 'Sin sección')
            stats["by_section"][section] = stats["by_section"].get(section, 0) + 1

            # Por jurisdicción
            juris = metadata.get('jurisdiccion_id', 'Sin jurisdicción')
            stats["by_jurisdiccion"][juris] = stats["by_jurisdiccion"].get(juris, 0) + 1

        return stats

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )

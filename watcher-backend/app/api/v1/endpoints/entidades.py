"""
API endpoints para entidades y Knowledge Graph
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_

from app.db.database import get_db
from app.db.models import EntidadExtraida, MencionEntidad, RelacionEntidad
from agents.historical_intelligence import HistoricalIntelligenceAgent
from agents.historical_intelligence.patterns import get_all_patterns

router = APIRouter()

historical_agent = HistoricalIntelligenceAgent()


# ---------------------------------------------------------------------------
# Helpers Neo4j
# ---------------------------------------------------------------------------

def _neo4j_available() -> bool:
    from app.db.neo4j_client import get_driver
    return get_driver() is not None


# ---------------------------------------------------------------------------
# Endpoints — orden crítico: estáticos antes que /{entidad_id}
# ---------------------------------------------------------------------------

@router.get("/")
async def listar_entidades(
    tipo: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Lista entidades con filtros opcionales."""
    query = select(EntidadExtraida)
    if tipo:
        query = query.where(EntidadExtraida.tipo == tipo)
    if search:
        query = query.where(
            or_(
                EntidadExtraida.nombre_normalizado.like(f"%{search.upper()}%"),
                EntidadExtraida.nombre_display.like(f"%{search}%"),
            )
        )
    query = query.order_by(EntidadExtraida.total_menciones.desc())

    count_query = select(func.count()).select_from(EntidadExtraida)
    if tipo:
        count_query = count_query.where(EntidadExtraida.tipo == tipo)
    if search:
        count_query = count_query.where(
            or_(
                EntidadExtraida.nombre_normalizado.like(f"%{search.upper()}%"),
                EntidadExtraida.nombre_display.like(f"%{search}%"),
            )
        )
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.offset(skip).limit(limit))
    entidades = result.scalars().all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "entidades": [
            {
                "id": e.id,
                "tipo": e.tipo,
                "nombre": e.nombre_display,
                "primera_aparicion": e.primera_aparicion.isoformat() if e.primera_aparicion else None,
                "ultima_aparicion": e.ultima_aparicion.isoformat() if e.ultima_aparicion else None,
                "total_menciones": e.total_menciones,
            }
            for e in entidades
        ],
    }


@router.get("/stats")
async def estadisticas_entidades(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Estadísticas globales del grafo de entidades."""
    por_tipo = dict(
        (await db.execute(
            select(EntidadExtraida.tipo, func.count().label("count"))
            .group_by(EntidadExtraida.tipo)
        )).all()
    )
    total_menciones = (await db.execute(select(func.count()).select_from(MencionEntidad))).scalar()
    total_relaciones = (await db.execute(select(func.count()).select_from(RelacionEntidad))).scalar()
    total_entidades = (await db.execute(select(func.count()).select_from(EntidadExtraida))).scalar()

    return {
        "total_entidades": total_entidades,
        "total_menciones": total_menciones,
        "total_relaciones": total_relaciones,
        "entidades_por_tipo": por_tipo,
    }


@router.get("/graph")
async def get_knowledge_graph(
    max_nodes: int = Query(50, ge=10, le=2000),
    min_mentions: int = Query(3, ge=1),
    entity_types: Optional[List[str]] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Grafo de conocimiento para visualización.
    Lee desde Neo4j si está disponible, sino fallback a PostgreSQL.
    """
    if _neo4j_available():
        from app.db.neo4j_client import get_neo4j_session
        from app.services import graph_service
        async with get_neo4j_session() as neo:
            result = await graph_service.get_graph_overview(
                neo,
                max_nodes=max_nodes,
                min_mentions=min_mentions,
                entity_types=entity_types,
            )
        if result["nodes"]:
            result["source"] = "neo4j"
            return result
        # Neo4j vacío → fallback a SQLite

    # Fallback SQLite/PostgreSQL
    query = select(EntidadExtraida).where(EntidadExtraida.total_menciones >= min_mentions)
    if entity_types:
        query = query.where(EntidadExtraida.tipo.in_(entity_types))
    query = query.order_by(EntidadExtraida.total_menciones.desc()).limit(max_nodes)
    entities = (await db.execute(query)).scalars().all()

    type_to_group = {"persona": 1, "organismo": 2, "empresa": 3, "contrato": 4, "monto": 5}
    nodes = [
        {
            "id": e.id,
            "label": (e.nombre_display or e.nombre_normalizado)[:30],
            "type": e.tipo,
            "mentions": e.total_menciones,
            "group": type_to_group.get(e.tipo, 0),
        }
        for e in entities
    ]
    entity_ids = [e.id for e in entities]
    relations = (await db.execute(
        select(RelacionEntidad).where(
            and_(
                RelacionEntidad.entidad_origen_id.in_(entity_ids),
                RelacionEntidad.entidad_destino_id.in_(entity_ids),
            )
        )
    )).scalars().all()
    links = [
        {
            "source": r.entidad_origen_id,
            "target": r.entidad_destino_id,
            "type": r.tipo_relacion,
            "weight": 1,
            "confidence": r.confianza,
        }
        for r in relations
    ]
    return {"nodes": nodes, "links": links, "source": "sqlite"}


@router.get("/centralidad")
async def centralidad_entidades(
    top_n: int = Query(20, ge=5, le=100),
) -> Dict[str, Any]:
    """Top entidades por PageRank (requiere Neo4j)."""
    if not _neo4j_available():
        raise HTTPException(status_code=503, detail="Graph database no disponible")
    from app.db.neo4j_client import get_neo4j_session
    from app.services import graph_service
    async with get_neo4j_session() as neo:
        ranking = await graph_service.compute_pagerank(neo, top_n=top_n)
    return {"top_n": top_n, "ranking": ranking}


@router.get("/comunidades")
async def comunidades_entidades() -> Dict[str, Any]:
    """Clusters de comunidades via algoritmo Louvain (requiere Neo4j)."""
    if not _neo4j_available():
        raise HTTPException(status_code=503, detail="Graph database no disponible")
    from app.db.neo4j_client import get_neo4j_session
    from app.services import graph_service
    async with get_neo4j_session() as neo:
        communities = await graph_service.compute_communities(neo)
    return {"total_communities": len(communities), "communities": communities}


@router.get("/camino/{id_a}/{id_b}")
async def camino_entre_entidades(
    id_a: int,
    id_b: int,
    max_depth: int = Query(6, ge=2, le=10),
) -> Dict[str, Any]:
    """Camino más corto entre dos entidades (requiere Neo4j)."""
    if not _neo4j_available():
        raise HTTPException(status_code=503, detail="Graph database no disponible")
    from app.db.neo4j_client import get_neo4j_session
    from app.services import graph_service
    async with get_neo4j_session() as neo:
        result = await graph_service.find_shortest_path(neo, id_a, id_b, max_depth)
    if not result["found"]:
        raise HTTPException(status_code=404, detail="No se encontró camino entre las entidades")
    return result


@router.get("/{entidad_id}/timeline")
async def timeline_entidad(
    entidad_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Timeline de apariciones de una entidad."""
    result = await historical_agent.build_entity_timeline(entidad_id, db)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Entity not found"))
    return result


@router.get("/{entidad_id}/relaciones")
async def relaciones_entidad(
    entidad_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Grafo de relaciones de una entidad.
    Lee desde Neo4j si disponible, sino fallback a PostgreSQL.
    """
    if _neo4j_available():
        from app.db.neo4j_client import get_neo4j_session
        from app.services import graph_service
        async with get_neo4j_session() as neo:
            return await graph_service.get_entity_relationships(neo, entidad_id)

    result = await historical_agent.get_entity_relationships(entidad_id, db)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Entity not found"))
    return result


@router.get("/{entidad_id}/vecinos")
async def vecinos_entidad(
    entidad_id: int,
    depth: int = Query(2, ge=1, le=4),
) -> Dict[str, Any]:
    """Subgrafo de vecinos a N saltos (requiere Neo4j)."""
    if not _neo4j_available():
        raise HTTPException(status_code=503, detail="Graph database no disponible")
    from app.db.neo4j_client import get_neo4j_session
    from app.services import graph_service
    async with get_neo4j_session() as neo:
        return await graph_service.get_neighborhood(neo, entidad_id, depth)


@router.get("/{entidad_id}")
async def detalle_entidad(
    entidad_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Detalle completo de una entidad."""
    entidad = (await db.execute(
        select(EntidadExtraida).where(EntidadExtraida.id == entidad_id)
    )).scalar_one_or_none()
    if not entidad:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")

    total_relaciones_db = (await db.execute(
        select(func.count()).select_from(RelacionEntidad).where(
            or_(
                RelacionEntidad.entidad_origen_id == entidad_id,
                RelacionEntidad.entidad_destino_id == entidad_id,
            )
        )
    )).scalar()

    return {
        "id": entidad.id,
        "tipo": entidad.tipo,
        "nombre": entidad.nombre_display,
        "nombre_normalizado": entidad.nombre_normalizado,
        "variantes": entidad.variantes,
        "primera_aparicion": entidad.primera_aparicion.isoformat() if entidad.primera_aparicion else None,
        "ultima_aparicion": entidad.ultima_aparicion.isoformat() if entidad.ultima_aparicion else None,
        "total_menciones": entidad.total_menciones,
        "total_relaciones": total_relaciones_db,
        "metadata_extra": entidad.metadata_extra,
        "created_at": entidad.created_at.isoformat(),
        "updated_at": entidad.updated_at.isoformat(),
    }


@router.get("/patrones/disponibles")
async def patrones_disponibles() -> Dict[str, Any]:
    """Lista todos los patrones de detección disponibles."""
    patterns = get_all_patterns()
    return {
        "total": len(patterns),
        "patrones": [
            {
                "id": p.id,
                "nombre": p.nombre,
                "descripcion": p.descripcion,
                "severidad": p.severidad,
                "categoria": p.categoria,
                "threshold": p.threshold,
            }
            for p in patterns.values()
        ],
    }


@router.post("/patrones/detectar")
async def detectar_patrones(
    pattern_ids: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Detecta patrones sospechosos en los datos."""
    result = await historical_agent.detect_patterns(pattern_ids, db)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Error detecting patterns"))
    return result


@router.post("/analisis-historico")
async def analisis_historico(
    entity_name: str = Query(...),
    entity_type: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Análisis histórico completo de una entidad."""
    result = await historical_agent.analyze_entity_history(entity_name, entity_type, db)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Entity not found"))
    return result


@router.get("/tipos")
async def tipos_entidades(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Lista los tipos de entidades disponibles con conteos."""
    result = await db.execute(
        select(EntidadExtraida.tipo, func.count().label("count"))
        .group_by(EntidadExtraida.tipo)
        .order_by(func.count().desc())
    )
    return {"tipos": [{"tipo": t, "count": c} for t, c in result.all()]}

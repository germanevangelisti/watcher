"""
API endpoints para entidades y Knowledge Graph
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.db.database import get_db
from app.db.models import EntidadExtraida, MencionEntidad, RelacionEntidad
from agents.historical_intelligence import HistoricalIntelligenceAgent
from agents.historical_intelligence.patterns import get_all_patterns

router = APIRouter()

# Instancia del agente
historical_agent = HistoricalIntelligenceAgent()


@router.get("/")
async def listar_entidades(
    tipo: Optional[str] = Query(None, description="Filtrar por tipo (persona, organismo, empresa, etc.)"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Lista entidades con filtros opcionales
    """
    query = select(EntidadExtraida)
    
    # Aplicar filtros
    if tipo:
        query = query.where(EntidadExtraida.tipo == tipo)
    
    if search:
        query = query.where(
            or_(
                EntidadExtraida.nombre_normalizado.like(f"%{search.upper()}%"),
                EntidadExtraida.nombre_display.like(f"%{search}%")
            )
        )
    
    # Orden por total de menciones
    query = query.order_by(EntidadExtraida.total_menciones.desc())
    
    # Contar total
    count_query = select(func.count()).select_from(EntidadExtraida)
    if tipo:
        count_query = count_query.where(EntidadExtraida.tipo == tipo)
    if search:
        count_query = count_query.where(
            or_(
                EntidadExtraida.nombre_normalizado.like(f"%{search.upper()}%"),
                EntidadExtraida.nombre_display.like(f"%{search}%")
            )
        )
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginar
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
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
                "total_menciones": e.total_menciones
            }
            for e in entidades
        ]
    }


@router.get("/stats")
async def estadisticas_entidades(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Estadísticas globales del grafo de entidades
    """
    # Total por tipo
    tipo_query = select(
        EntidadExtraida.tipo,
        func.count().label('count')
    ).group_by(EntidadExtraida.tipo)
    
    tipo_result = await db.execute(tipo_query)
    por_tipo = {row[0]: row[1] for row in tipo_result.all()}
    
    # Total menciones
    menciones_query = select(func.count()).select_from(MencionEntidad)
    menciones_result = await db.execute(menciones_query)
    total_menciones = menciones_result.scalar()
    
    # Total relaciones
    relaciones_query = select(func.count()).select_from(RelacionEntidad)
    relaciones_result = await db.execute(relaciones_query)
    total_relaciones = relaciones_result.scalar()
    
    # Total entidades
    total_query = select(func.count()).select_from(EntidadExtraida)
    total_result = await db.execute(total_query)
    total_entidades = total_result.scalar()
    
    return {
        "total_entidades": total_entidades,
        "total_menciones": total_menciones,
        "total_relaciones": total_relaciones,
        "entidades_por_tipo": por_tipo
    }


@router.get("/graph")
async def get_knowledge_graph(
    max_nodes: int = Query(50, ge=10, le=200, description="Máximo de nodos"),
    min_mentions: int = Query(3, ge=1, description="Mínimo de menciones"),
    entity_types: Optional[List[str]] = Query(None, description="Tipos de entidad"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Obtiene el grafo de conocimiento para visualización
    
    Devuelve nodos (entidades) y enlaces (relaciones) en formato
    listo para visualización con bibliotecas como D3.js o similar.
    """
    # Query para entidades
    query = select(EntidadExtraida).where(
        EntidadExtraida.total_menciones >= min_mentions
    )
    
    if entity_types:
        query = query.where(EntidadExtraida.tipo.in_(entity_types))
    
    # Ordenar por menciones y limitar
    query = query.order_by(EntidadExtraida.total_menciones.desc()).limit(max_nodes)
    
    result = await db.execute(query)
    entities = result.scalars().all()
    
    # Mapear tipos a grupos numéricos
    type_to_group = {
        'persona': 1,
        'organismo': 2,
        'empresa': 3,
        'contrato': 4,
        'monto': 5
    }
    
    # Crear nodos
    nodes = [
        {
            "id": ent.id,
            "label": ent.nombre_display[:30] if hasattr(ent, 'nombre_display') else ent.nombre_normalizado[:30],
            "type": ent.tipo,
            "mentions": ent.total_menciones,
            "group": type_to_group.get(ent.tipo, 0)
        }
        for ent in entities
    ]
    
    # Obtener relaciones entre estas entidades
    entity_ids = [ent.id for ent in entities]
    
    from sqlalchemy import and_
    
    relations_query = select(RelacionEntidad).where(
        and_(
            RelacionEntidad.entidad_origen_id.in_(entity_ids),
            RelacionEntidad.entidad_destino_id.in_(entity_ids)
        )
    )
    
    relations_result = await db.execute(relations_query)
    relations = relations_result.scalars().all()
    
    # Crear enlaces
    links = [
        {
            "source": rel.entidad_origen_id,
            "target": rel.entidad_destino_id,
            "type": rel.tipo_relacion,
            "weight": rel.total_ocurrencias,
            "confidence": rel.confianza
        }
        for rel in relations
    ]
    
    return {
        "nodes": nodes,
        "links": links
    }


@router.get("/{entidad_id}/timeline")
async def timeline_entidad(
    entidad_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Timeline de apariciones de una entidad
    """
    result = await historical_agent.build_entity_timeline(entidad_id, db)
    
    if not result.get('success'):
        raise HTTPException(status_code=404, detail=result.get('error', 'Entity not found'))
    
    return result


@router.get("/{entidad_id}/relaciones")
async def relaciones_entidad(
    entidad_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Grafo de relaciones de una entidad
    """
    result = await historical_agent.get_entity_relationships(entidad_id, db)
    
    if not result.get('success'):
        raise HTTPException(status_code=404, detail=result.get('error', 'Entity not found'))
    
    return result


@router.get("/{entidad_id}")
async def detalle_entidad(
    entidad_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Detalle completo de una entidad
    """
    # Obtener entidad
    query = select(EntidadExtraida).where(EntidadExtraida.id == entidad_id)
    result = await db.execute(query)
    entidad = result.scalar_one_or_none()
    
    if not entidad:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")
    
    # Contar menciones
    menciones_query = select(func.count()).select_from(MencionEntidad).where(
        MencionEntidad.entidad_id == entidad_id
    )
    menciones_result = await db.execute(menciones_query)
    _total_menciones_db = menciones_result.scalar()
    
    # Contar relaciones
    relaciones_query = select(func.count()).select_from(RelacionEntidad).where(
        or_(
            RelacionEntidad.entidad_origen_id == entidad_id,
            RelacionEntidad.entidad_destino_id == entidad_id
        )
    )
    relaciones_result = await db.execute(relaciones_query)
    total_relaciones_db = relaciones_result.scalar()
    
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
        "updated_at": entidad.updated_at.isoformat()
    }


@router.get("/patrones/disponibles")
async def patrones_disponibles() -> Dict[str, Any]:
    """
    Lista todos los patrones de detección disponibles
    """
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
                "threshold": p.threshold
            }
            for p in patterns.values()
        ]
    }


@router.post("/patrones/detectar")
async def detectar_patrones(
    pattern_ids: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Detecta patrones sospechosos en los datos
    
    Args:
        pattern_ids: Lista de IDs de patrones específicos (None = todos)
    """
    result = await historical_agent.detect_patterns(pattern_ids, db)
    
    if not result.get('success'):
        raise HTTPException(status_code=500, detail=result.get('error', 'Error detecting patterns'))
    
    return result


@router.post("/analisis-historico")
async def analisis_historico(
    entity_name: str = Query(..., description="Nombre de la entidad a analizar"),
    entity_type: str = Query(..., description="Tipo de entidad (persona, organismo, empresa, etc.)"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Análisis histórico completo de una entidad
    
    Incluye timeline, relaciones y patrones detectados
    """
    result = await historical_agent.analyze_entity_history(entity_name, entity_type, db)
    
    if not result.get('success'):
        raise HTTPException(status_code=404, detail=result.get('error', 'Entity not found'))
    
    return result


@router.get("/tipos")
async def tipos_entidades(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Lista los tipos de entidades disponibles con conteos
    """
    query = select(
        EntidadExtraida.tipo,
        func.count().label('count')
    ).group_by(EntidadExtraida.tipo).order_by(func.count().desc())
    
    result = await db.execute(query)
    tipos = result.all()
    
    return {
        "tipos": [
            {"tipo": tipo, "count": count}
            for tipo, count in tipos
        ]
    }


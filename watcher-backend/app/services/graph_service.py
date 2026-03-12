"""
GraphService — todas las operaciones Neo4j para el grafo de conocimiento.

Escritura (idempotente via MERGE):
  upsert_entity()        — nodo :Entidad
  upsert_boletin()       — nodo :Boletin
  upsert_relationship()  — arista tipada (Cypher dinámico, sin APOC)
  upsert_mention_edge()  — arista :MENCIONADO_EN

Lectura:
  get_graph_overview()        — /entidades/graph (mismo shape que PostgreSQL)
  get_entity_relationships()  — /entidades/{id}/relaciones
  find_shortest_path()        — /entidades/camino/{a}/{b}
  get_neighborhood()          — /entidades/{id}/vecinos
  load_graph_into_networkx()  — carga grafo completo en NetworkX DiGraph
  compute_pagerank()          — top N entidades por PageRank
  compute_communities()       — clusters Louvain
"""

import json
import logging
import re as _re
from typing import List, Dict, Any, Optional

import networkx as nx
from neo4j import AsyncSession as Neo4jAsyncSession

from app.db.graph_driver import run_query

logger = logging.getLogger(__name__)

# Mapeo de tipo_relacion (PostgreSQL) → tipo Neo4j
_REL_TYPE_MAP = {
    "contrata": "CONTRATA",
    "designa": "DESIGNA",
    "adjudica": "ADJUDICA",
    "recibe_subsidio": "RECIBE_SUBSIDIO",
    "firma": "FIRMA",
    "transfiere": "TRANSFIERE",
    "autoriza": "AUTORIZA",
    "aprueba": "APRUEBA",
    "otorga": "OTORGA",
    "sanciona": "SANCIONA",
    "apela": "APELA",
    "se_relaciona_con": "SE_RELACIONA_CON",
}

_TYPE_TO_GROUP = {
    "persona": 1, "organismo": 2, "empresa": 3, "contrato": 4, "monto": 5,
}


# ---------------------------------------------------------------------------
# Operaciones de escritura
# ---------------------------------------------------------------------------

async def upsert_entity(
    session: Neo4jAsyncSession,
    *,
    pg_id: int,
    tipo: str,
    nombre_normalizado: str,
    nombre_display: str,
    variantes: List[str],
    total_menciones: int,
    primera_aparicion: Optional[str],
    ultima_aparicion: Optional[str],
    metadata_extra: Optional[Dict],
) -> None:
    """MERGE un nodo :Entidad por nombre_normalizado, actualiza todas las propiedades."""
    await run_query(
        session,
        "upsert_entity",
        {
            "pg_id": pg_id,
            "tipo": tipo,
            "nombre_normalizado": nombre_normalizado,
            "nombre_display": nombre_display,
            "variantes": variantes or [],
            "total_menciones": total_menciones,
            "primera_aparicion": primera_aparicion or "1900-01-01",
            "ultima_aparicion": ultima_aparicion or "1900-01-01",
            "metadata_extra": json.dumps(metadata_extra or {}),
        },
    )


async def upsert_boletin(
    session: Neo4jAsyncSession,
    *,
    pg_id: int,
    filename: str,
    date: str,
) -> None:
    """MERGE un nodo :Boletin liviano (para provenance de aristas)."""
    await run_query(session, "upsert_boletin", {"pg_id": pg_id, "filename": filename, "date": date})


async def upsert_relationship(
    session: Neo4jAsyncSession,
    *,
    origen_nombre_normalizado: str,
    destino_nombre_normalizado: str,
    tipo_relacion: str,
    pg_id: int,
    boletin_pg_id: int,
    fecha: str,
    confianza: float,
    contexto: Optional[str],
    metadata_extra: Optional[Dict],
) -> None:
    """
    MERGE una arista dirigida entre dos nodos :Entidad.
    Usa Cypher dinámico (sin APOC) para tipos de relación variables.
    El tipo se valida contra _REL_TYPE_MAP antes de interpolarlo en el query.
    """
    rel_type = _REL_TYPE_MAP.get(tipo_relacion.lower(), tipo_relacion.upper())
    # Seguridad: el tipo debe ser solo letras mayúsculas y guión bajo
    if not _re.match(r'^[A-Z_]+$', rel_type):
        raise ValueError(f"Tipo de relación Neo4j inválido: {rel_type!r}")
    props = {
        "pg_id": pg_id,
        "boletin_pg_id": boletin_pg_id,
        "fecha": fecha,
        "confianza": confianza,
        "contexto": (contexto or "")[:500],
        "metadata_extra": json.dumps(metadata_extra or {}),
    }
    cypher = f"""
        MATCH (o:Entidad {{nombre_normalizado: $origen}})
        MATCH (d:Entidad {{nombre_normalizado: $destino}})
        MERGE (o)-[r:{rel_type} {{pg_id: $pg_id}}]->(d)
        SET r += $props
    """
    await session.run(
        cypher,
        origen=origen_nombre_normalizado,
        destino=destino_nombre_normalizado,
        pg_id=pg_id,
        props=props,
    )


async def upsert_mention_edge(
    session: Neo4jAsyncSession,
    *,
    entidad_nombre_normalizado: str,
    boletin_pg_id: int,
    pg_id: int,
    fragmento: str,
    confianza: float,
) -> None:
    """MERGE una arista :MENCIONADO_EN entre :Entidad y :Boletin."""
    await run_query(
        session,
        "upsert_mention_edge",
        {
            "nombre_normalizado": entidad_nombre_normalizado,
            "boletin_pg_id": boletin_pg_id,
            "pg_id": pg_id,
            "fragmento": fragmento[:500],
            "confianza": confianza,
        },
    )


# ---------------------------------------------------------------------------
# Operaciones de lectura
# ---------------------------------------------------------------------------

async def get_graph_overview(
    session: Neo4jAsyncSession,
    max_nodes: int = 50,
    min_mentions: int = 3,
    entity_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Grafo de conocimiento para visualización.
    Mantiene el mismo response shape que el endpoint PostgreSQL existente.
    """
    # graph_overview_nodes.cypher doesn't support the optional type filter
    # (dynamic WHERE clause), so we keep the f-string for that case only.
    if entity_types:
        nodes_result = await session.run(
            """
            MATCH (e:Entidad)
            WHERE e.total_menciones >= $min_mentions AND e.tipo IN $types
            WITH e ORDER BY e.total_menciones DESC LIMIT $max_nodes
            RETURN collect(e) AS nodes
            """,
            min_mentions=min_mentions,
            max_nodes=max_nodes,
            types=entity_types,
        )
    else:
        nodes_result = await run_query(
            session,
            "graph_overview_nodes",
            {"min_mentions": min_mentions, "max_nodes": max_nodes},
        )

    nodes_record = await nodes_result.single()
    if not nodes_record:
        return {"nodes": [], "links": []}

    raw_nodes = nodes_record["nodes"]
    node_pg_ids = [n["pg_id"] for n in raw_nodes]

    nodes = [
        {
            "id": n["pg_id"],
            "label": (n["nombre_display"] or "")[:30],
            "type": n["tipo"],
            "mentions": n["total_menciones"],
            "group": _TYPE_TO_GROUP.get(n["tipo"], 0),
        }
        for n in raw_nodes
    ]

    # Aristas solo entre nodos seleccionados
    links_result = await run_query(session, "graph_overview_links", {"ids": node_pg_ids})
    links = []
    async for rec in links_result:
        links.append({
            "source": rec["source"],
            "target": rec["target"],
            "type": rec["rel_type"].lower(),
            "weight": 1,
            "confidence": rec["confidence"] or 0.8,
        })

    return {"nodes": nodes, "links": links}


async def get_entity_relationships(
    session: Neo4jAsyncSession,
    pg_id: int,
) -> Dict[str, Any]:
    """
    Vecindad de 1 salto de una entidad.
    Mismo response shape que el endpoint PostgreSQL existente.
    """
    result = await run_query(
        session,
        "entity_relationships",
        {"pg_id": pg_id},
    )
    record = await result.single()
    if not record:
        return {"success": False, "error": "Entidad no encontrada"}

    main = record["main"]
    nodes = [{
        "id": main["pg_id"],
        "label": main["nombre_display"],
        "type": main["tipo"],
        "is_main": True,
    }] + [
        {"id": n["pg_id"], "label": n["nombre_display"], "type": n["tipo"]}
        for n in record["neighbors"] if n
    ]
    edges = [
        {
            "from": e["from_id"],
            "to": e["to_id"],
            "type": (e["rel_type"] or "").lower(),
            "fecha": e["fecha"],
            "confianza": e["confianza"],
        }
        for e in record["edges"] if e.get("to_id") is not None
    ]
    return {
        "success": True,
        "entity": {
            "id": main["pg_id"],
            "nombre": main["nombre_display"],
            "tipo": main["tipo"],
        },
        "graph": {"nodes": nodes, "edges": edges},
        "stats": {"total_nodes": len(nodes), "total_edges": len(edges)},
    }


async def find_shortest_path(
    session: Neo4jAsyncSession,
    pg_id_a: int,
    pg_id_b: int,
    max_depth: int = 6,
) -> Dict[str, Any]:
    """Camino más corto entre dos entidades (multi-salto nativo Neo4j)."""
    result = await session.run(
        """
        MATCH (a:Entidad {pg_id: $id_a}),
              (b:Entidad {pg_id: $id_b}),
              path = shortestPath((a)-[*1..$max_depth]-(b))
        RETURN path
        LIMIT 1
        """,
        id_a=pg_id_a,
        id_b=pg_id_b,
        max_depth=max_depth,
    )
    record = await result.single()
    if not record:
        return {"found": False, "path": [], "length": 0}

    path = record["path"]
    nodes = [
        {"id": n["pg_id"], "label": n["nombre_display"], "type": n["tipo"]}
        for n in path.nodes
    ]
    rels = [
        {
            "type": r.type.lower(),
            "from": r.start_node["pg_id"],
            "to": r.end_node["pg_id"],
        }
        for r in path.relationships
    ]
    return {"found": True, "length": len(rels), "nodes": nodes, "relationships": rels}


async def get_neighborhood(
    session: Neo4jAsyncSession,
    pg_id: int,
    depth: int = 2,
) -> Dict[str, Any]:
    """Subgrafo de vecinos a N saltos (multi-hop nativo Neo4j)."""
    result = await run_query(session, "neighborhood", {"pg_id": pg_id, "depth": depth})
    record = await result.single()
    if not record:
        return {"nodes": [], "links": [], "center_id": pg_id, "depth": depth}

    nodes = [
        {
            "id": n["pg_id"],
            "label": (n["nombre_display"] or "")[:30],
            "type": n["tipo"],
            "is_center": n["pg_id"] == pg_id,
        }
        for n in record["all_nodes"]
    ]
    links = [
        {
            "source": r["from_id"],
            "target": r["to_id"],
            "type": (r["rel_type"] or "").lower(),
        }
        for r in record["all_rels"] if r.get("to_id") is not None
    ]
    return {"nodes": nodes, "links": links, "center_id": pg_id, "depth": depth}


# ---------------------------------------------------------------------------
# Algoritmos de grafo via NetworkX
# ---------------------------------------------------------------------------

async def load_graph_into_networkx(
    session: Neo4jAsyncSession,
    min_mentions: int = 1,
    max_nodes: int = 5000,
) -> nx.DiGraph:
    """
    Carga el grafo completo de Neo4j en un DiGraph de NetworkX.
    Usado para PageRank y detección de comunidades Louvain.
    """
    G = nx.DiGraph()

    nodes_result = await run_query(
        session,
        "load_for_networkx",
        {"min_mentions": min_mentions, "max_nodes": max_nodes},
    )
    async for record in nodes_result:
        n = record["e"]
        G.add_node(
            n["pg_id"],
            tipo=n["tipo"],
            nombre_display=n["nombre_display"],
            total_menciones=n["total_menciones"],
        )

    if not G.nodes:
        return G

    node_ids = list(G.nodes)
    edges_result = await session.run(
        """
        MATCH (o:Entidad)-[r]->(d:Entidad)
        WHERE o.pg_id IN $ids AND d.pg_id IN $ids
        RETURN o.pg_id AS src, d.pg_id AS dst, type(r) AS rel_type
        """,
        ids=node_ids,
    )
    async for record in edges_result:
        G.add_edge(record["src"], record["dst"], rel_type=record["rel_type"])

    logger.info(
        "Grafo cargado en NetworkX: %d nodos, %d aristas",
        G.number_of_nodes(), G.number_of_edges(),
    )
    return G


async def compute_pagerank(
    session: Neo4jAsyncSession,
    top_n: int = 20,
) -> List[Dict[str, Any]]:
    """
    Calcula PageRank via NetworkX sobre el grafo cargado desde Neo4j.
    Retorna top N entidades ordenadas por score.
    """
    G = await load_graph_into_networkx(session)
    if G.number_of_nodes() == 0:
        return []

    pr = nx.pagerank(G, alpha=0.85, max_iter=100)
    sorted_nodes = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:top_n]

    return [
        {
            "pg_id": pg_id,
            "nombre_display": G.nodes[pg_id].get("nombre_display", ""),
            "tipo": G.nodes[pg_id].get("tipo", ""),
            "pagerank_score": round(score, 6),
        }
        for pg_id, score in sorted_nodes
    ]


async def compute_communities(
    session: Neo4jAsyncSession,
) -> List[Dict[str, Any]]:
    """
    Detección de comunidades Louvain via python-louvain sobre NetworkX.
    Requiere: pip install python-louvain
    Retorna lista de {community_id, size, members}.
    """
    try:
        import community as community_louvain
    except ImportError:
        logger.error("python-louvain no instalado. Ejecutar: pip install python-louvain")
        return []

    G_directed = await load_graph_into_networkx(session)
    if G_directed.number_of_nodes() == 0:
        return []

    G_undirected = G_directed.to_undirected()
    partition = community_louvain.best_partition(G_undirected)

    communities: Dict[int, List] = {}
    for pg_id, community_id in partition.items():
        communities.setdefault(community_id, []).append(pg_id)

    result = []
    for community_id, members in sorted(communities.items(), key=lambda x: -len(x[1])):
        result.append({
            "community_id": community_id,
            "size": len(members),
            "members": [
                {
                    "pg_id": pg_id,
                    "nombre_display": G_directed.nodes[pg_id].get("nombre_display", ""),
                    "tipo": G_directed.nodes[pg_id].get("tipo", ""),
                }
                for pg_id in members
            ],
        })
    return result

// Entity search — fulltext search across all entity types
// Used by: app/services/graph_service.py

CALL db.index.fulltext.queryNodes('entity_search_watcher', $query)
YIELD node, score
RETURN
    elementId(node) AS id,
    labels(node) AS labels,
    node.nombre AS nombre,
    node.descripcion AS descripcion,
    score
ORDER BY score DESC
LIMIT $limit

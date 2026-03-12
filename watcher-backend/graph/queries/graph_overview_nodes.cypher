// Fetch top-N entities by mention count for graph overview visualisation.
// Used by: graph_service.get_graph_overview()
// Parameters: $min_mentions (int), $max_nodes (int)
// Note: caller must apply optional type filter before calling this query.

MATCH (e:Entidad)
WHERE e.total_menciones >= $min_mentions
WITH e ORDER BY e.total_menciones DESC LIMIT $max_nodes
RETURN collect(e) AS nodes

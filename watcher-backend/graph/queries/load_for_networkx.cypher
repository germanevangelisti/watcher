// Load all entity nodes for NetworkX graph algorithms (PageRank, Louvain).
// Used by: graph_service.load_graph_into_networkx() — nodes pass
// Parameters: $min_mentions (int), $max_nodes (int)

MATCH (e:Entidad)
WHERE e.total_menciones >= $min_mentions
RETURN e ORDER BY e.total_menciones DESC LIMIT $max_nodes

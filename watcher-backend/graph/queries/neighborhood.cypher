// Fetch subgraph of N-hop neighbours around a central entity.
// Used by: graph_service.get_neighborhood()
// Parameters: $pg_id (int), $depth (int, 1-4 recommended)

MATCH path = (center:Entidad {pg_id: $pg_id})-[*1..$depth]-(neighbor:Entidad)
WITH nodes(path) AS ns, relationships(path) AS rs
UNWIND ns AS n
WITH collect(DISTINCT n) AS all_nodes, rs
UNWIND rs AS r
RETURN all_nodes,
       collect(DISTINCT {
         from_id:  startNode(r).pg_id,
         to_id:    endNode(r).pg_id,
         rel_type: type(r)
       }) AS all_rels

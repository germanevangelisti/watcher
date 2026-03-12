// Fetch all relationships between a given set of entity pg_ids.
// Used by: graph_service.get_graph_overview() (second query)
// Parameters: $ids (list[int])

MATCH (o:Entidad)-[r]->(d:Entidad)
WHERE o.pg_id IN $ids AND d.pg_id IN $ids
RETURN o.pg_id    AS source,
       d.pg_id    AS target,
       type(r)    AS rel_type,
       r.confianza AS confidence

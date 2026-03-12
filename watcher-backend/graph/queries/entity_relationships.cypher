// Fetch 1-hop neighbourhood of an entity (nodes + edges).
// Used by: graph_service.get_entity_relationships()
// Parameters: $pg_id (int)

MATCH (main:Entidad {pg_id: $pg_id})
OPTIONAL MATCH (main)-[r]-(neighbor:Entidad)
RETURN main,
       collect(DISTINCT neighbor) AS neighbors,
       collect({
         from_id:   startNode(r).pg_id,
         to_id:     endNode(r).pg_id,
         rel_type:  type(r),
         fecha:     toString(r.fecha),
         confianza: r.confianza
       }) AS edges

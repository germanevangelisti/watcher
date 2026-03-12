// Upsert a :MENCIONADO_EN edge between :Entidad and :Boletin.
// Used by: graph_service.upsert_mention_edge()
// Parameters: $nombre_normalizado, $boletin_pg_id, $pg_id, $fragmento, $confianza

MATCH (e:Entidad {nombre_normalizado: $nombre_normalizado})
MATCH (b:Boletin {pg_id: $boletin_pg_id})
MERGE (e)-[r:MENCIONADO_EN {pg_id: $pg_id}]->(b)
SET r.fragmento = $fragmento,
    r.confianza = $confianza

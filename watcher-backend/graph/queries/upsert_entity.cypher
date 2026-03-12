// Upsert a single :Entidad node (idempotent via MERGE on nombre_normalizado).
// Used by: graph_service.upsert_entity()
// Parameters: $pg_id, $tipo, $nombre_normalizado, $nombre_display,
//             $variantes, $total_menciones, $primera_aparicion,
//             $ultima_aparicion, $metadata_extra

MERGE (e:Entidad {nombre_normalizado: $nombre_normalizado})
SET e.pg_id             = $pg_id,
    e.tipo              = $tipo,
    e.nombre_display    = $nombre_display,
    e.variantes         = $variantes,
    e.total_menciones   = $total_menciones,
    e.primera_aparicion = date($primera_aparicion),
    e.ultima_aparicion  = date($ultima_aparicion),
    e.metadata_extra    = $metadata_extra

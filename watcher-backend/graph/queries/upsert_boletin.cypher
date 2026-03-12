// Upsert a lightweight :Boletin node (used for provenance of relationship edges).
// Used by: graph_service.upsert_boletin()
// Parameters: $pg_id, $filename, $date

MERGE (b:Boletin {pg_id: $pg_id})
SET b.filename = $filename,
    b.date     = $date

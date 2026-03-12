-- High-risk analysis entries joined with their source boletines
-- Used by: app/api/v1/endpoints/redflags.py, analisis
-- Parameters: :limit (int, default 50), :offset (int, default 0)

SELECT
    a.id                  AS analisis_id,
    b.filename            AS boletin,
    b.date                AS fecha_boletin,
    b.section             AS seccion,
    a.categoria,
    a.tipo_curro,
    a.organismo,
    a.entidad_beneficiaria,
    a.monto_estimado,
    a.fragmento,
    a.created_at          AS detectado_en
FROM analisis a
JOIN boletines b ON a.boletin_id = b.id
WHERE a.riesgo = 'ALTO'
ORDER BY a.created_at DESC
LIMIT  :limit
OFFSET :offset;

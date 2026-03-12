-- Processing statistics broken down by boletin section
-- Used by: app/api/v1/endpoints/pipeline.py, metricas
-- Parameters: none

SELECT
    section,
    COUNT(*)                                                             AS total_boletines,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END)               AS completados,
    SUM(CASE WHEN status = 'failed'    THEN 1 ELSE 0 END)               AS fallidos,
    SUM(CASE WHEN status = 'pending'   THEN 1 ELSE 0 END)               AS pendientes,
    ROUND(
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    )                                                                    AS tasa_exito_pct
FROM boletines
GROUP BY section
ORDER BY section;

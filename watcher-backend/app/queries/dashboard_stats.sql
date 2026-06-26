-- Dashboard stats: aggregate counts for the main dashboard
-- Used by: app/api/v1/endpoints/dashboard.py

SELECT
    (SELECT COUNT(*) FROM boletines) AS total_boletines,
    (SELECT COUNT(*) FROM boletines WHERE status = 'completed') AS boletines_procesados,
    (SELECT COUNT(*) FROM boletines WHERE status = 'pending') AS boletines_pendientes,
    (SELECT COUNT(*) FROM boletines WHERE status = 'error') AS boletines_error,
    (SELECT COUNT(*) FROM analisis) AS total_analisis,
    (SELECT COUNT(*) FROM analisis WHERE riesgo = 'alto') AS analisis_alto_riesgo,
    (SELECT COUNT(*) FROM alertas_gestion WHERE estado = 'activa') AS alertas_activas,
    (SELECT COUNT(DISTINCT organismo) FROM analisis WHERE organismo IS NOT NULL) AS organismos_unicos;

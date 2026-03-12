-- Boletines grouped by processing status with percentages
-- Used by: app/api/v1/endpoints/pipeline.py, dashboard
-- Parameters: none

SELECT
    status,
    COUNT(*)                                          AS cantidad,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS porcentaje
FROM boletines
GROUP BY status
ORDER BY cantidad DESC;

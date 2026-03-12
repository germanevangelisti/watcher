-- Full-text search index health: chunk distribution by section type
-- Used by: app/services/fts_service.py, observability endpoint
-- Parameters: none

SELECT
    COALESCE(c.section_type, 'unknown')   AS section_type,
    COUNT(*)                              AS total_chunks,
    SUM(CASE WHEN c.indexed_at IS NOT NULL THEN 1 ELSE 0 END) AS indexed_chunks,
    ROUND(
        SUM(CASE WHEN c.indexed_at IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    )                                     AS indexed_pct,
    AVG(c.char_count)                     AS avg_chars
FROM chunk_records c
GROUP BY c.section_type
ORDER BY total_chunks DESC;

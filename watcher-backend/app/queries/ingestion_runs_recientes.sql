-- Recent ingestion pipeline runs with duration and throughput
-- Used by: app/api/v1/endpoints/pipeline_runs.py
-- Parameters: :limit (int, default 20), :pipeline_name (str, optional)

SELECT
    ir.id,
    ir.pipeline_name,
    ir.source_id,
    ir.status,
    ir.rows_in,
    ir.rows_loaded,
    ir.error,
    ir.started_at,
    ir.finished_at,
    ROUND(
        (JULIANDAY(COALESCE(ir.finished_at, CURRENT_TIMESTAMP)) - JULIANDAY(ir.started_at)) * 86400,
        2
    )                                                    AS duration_seconds,
    CASE
        WHEN ir.rows_in > 0
        THEN ROUND(ir.rows_loaded * 100.0 / ir.rows_in, 2)
        ELSE NULL
    END                                                  AS load_rate_pct
FROM ingestion_runs ir
WHERE (:pipeline_name IS NULL OR ir.pipeline_name = :pipeline_name)
ORDER BY ir.started_at DESC
LIMIT :limit;

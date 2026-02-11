-- LIMPIEZA COMPLETA DE BASE DE DATOS
-- Limpia TODOS los datos de procesamiento, mantiene solo estructura y jurisdicciones

BEGIN TRANSACTION;

-- ============================================
-- ANÁLISIS Y RESULTADOS
-- ============================================
DELETE FROM analisis;
DELETE FROM analysis_results;
DELETE FROM analysis_executions;
DELETE FROM analysis_configs;
DELETE FROM analysis_comparisons;

-- ============================================
-- RED FLAGS Y ALERTAS
-- ============================================
DELETE FROM red_flags;
DELETE FROM alertas_gestion;

-- ============================================
-- ACTOS ADMINISTRATIVOS
-- ============================================
DELETE FROM actos_administrativos;
DELETE FROM vinculos_acto_presupuesto;

-- ============================================
-- DOCUMENTOS DE BOLETINES
-- ============================================
DELETE FROM boletin_documents;

-- ============================================
-- MENCIONES JURISDICCIONALES
-- ============================================
DELETE FROM menciones_jurisdiccionales;

-- ============================================
-- WORKFLOWS Y AGENTES
-- ============================================
DELETE FROM agent_tasks;
DELETE FROM agent_workflows;
DELETE FROM workflow_logs;

-- ============================================
-- PRESUPUESTO (ANÁLISIS, NO BASE)
-- ============================================
DELETE FROM ejecucion_presupuestaria;
-- Mantener presupuesto_base ya que es dato base, no análisis

-- ============================================
-- PROCESAMIENTO Y SYNC
-- ============================================
DELETE FROM procesamiento_batch;
DELETE FROM sync_state;
DELETE FROM metricas_gestion;

-- ============================================
-- RESETEAR BOLETINES A PENDING
-- ============================================
UPDATE boletines 
SET status = 'pending',
    error_message = NULL,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;

-- ============================================
-- VERIFICACIÓN FINAL
-- ============================================
SELECT '======================================' as '';
SELECT '    LIMPIEZA COMPLETA FINALIZADA     ' as '';
SELECT '======================================' as '';
SELECT '' as '';

SELECT 'TABLAS LIMPIADAS:' as '';
SELECT '  • Análisis:', COUNT(*) FROM analisis;
SELECT '  • Red Flags:', COUNT(*) FROM red_flags;
SELECT '  • Actos Admin:', COUNT(*) FROM actos_administrativos;
SELECT '  • Documentos:', COUNT(*) FROM boletin_documents;
SELECT '  • Menciones:', COUNT(*) FROM menciones_jurisdiccionales;
SELECT '  • Agent Tasks:', COUNT(*) FROM agent_tasks;
SELECT '  • Workflows:', COUNT(*) FROM agent_workflows;
SELECT '  • Ejecuciones:', COUNT(*) FROM analysis_executions;
SELECT '' as '';

SELECT 'TABLAS MANTENIDAS:' as '';
SELECT '  • Boletines:', COUNT(*), '(status: pending)' FROM boletines;
SELECT '  • Jurisdicciones:', COUNT(*) FROM jurisdicciones;
SELECT '  • Presupuesto Base:', COUNT(*) FROM presupuesto_base;
SELECT '' as '';

SELECT '======================================' as '';
SELECT '  ✅ Base de datos limpia y lista!   ' as '';
SELECT '======================================' as '';

-- Optimizar base de datos
VACUUM;

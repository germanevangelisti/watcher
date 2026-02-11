-- Script de Limpieza de Base de Datos
-- Limpia datos de procesamiento manteniendo estructura y boletines base

-- 1. Verificar estado actual
SELECT '=== ESTADO ACTUAL ===' as info;
SELECT 'Boletines:' as tabla, COUNT(*) as registros FROM boletines
UNION ALL
SELECT 'Jurisdicciones:', COUNT(*) FROM jurisdicciones
UNION ALL
SELECT 'Menciones:', COUNT(*) FROM menciones_jurisdiccionales
UNION ALL
SELECT 'Análisis:', COUNT(*) FROM analisis
UNION ALL
SELECT 'Alertas:', COUNT(*) FROM alertas
UNION ALL
SELECT 'Workflows:', COUNT(*) FROM workflow_executions
UNION ALL
SELECT 'Sync State:', COUNT(*) FROM sync_state;

-- 2. Limpiar menciones jurisdiccionales
SELECT '=== LIMPIANDO MENCIONES ===' as info;
DELETE FROM menciones_jurisdiccionales;

-- 3. Limpiar análisis
SELECT '=== LIMPIANDO ANÁLISIS ===' as info;
DELETE FROM analisis;

-- 4. Limpiar alertas
SELECT '=== LIMPIANDO ALERTAS ===' as info;
DELETE FROM alertas;

-- 5. Limpiar ejecuciones de workflows
SELECT '=== LIMPIANDO WORKFLOWS ===' as info;
DELETE FROM workflow_executions;

-- 6. Resetear estado de sync
SELECT '=== RESETEANDO SYNC ===' as info;
DELETE FROM sync_state;

-- 7. Resetear estados de boletines
SELECT '=== RESETEANDO BOLETINES ===' as info;
UPDATE boletines 
SET status = 'pending',
    error_message = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE status != 'pending';

-- 8. Verificar estado final
SELECT '=== ESTADO FINAL ===' as info;
SELECT 'Boletines:' as tabla, COUNT(*) as registros, status, COUNT(*) as count_status 
FROM boletines 
GROUP BY status
UNION ALL
SELECT 'Jurisdicciones:', COUNT(*), '', 0 FROM jurisdicciones
UNION ALL
SELECT 'Menciones:', COUNT(*), '', 0 FROM menciones_jurisdiccionales
UNION ALL
SELECT 'Análisis:', COUNT(*), '', 0 FROM analisis;

-- 9. Distribución por fuente
SELECT '=== BOLETINES POR FUENTE ===' as info;
SELECT fuente, COUNT(*) as cantidad 
FROM boletines 
GROUP BY fuente;

-- 10. Vacuum para optimizar
VACUUM;

SELECT '=== LIMPIEZA COMPLETADA ===' as info;

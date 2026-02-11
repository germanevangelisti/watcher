-- Script de Limpieza Simple de Base de Datos
-- Solo limpia las tablas que existen

BEGIN TRANSACTION;

-- Limpiar menciones
DELETE FROM menciones_jurisdiccionales;

-- Limpiar análisis
DELETE FROM analisis;

-- Resetear sync si existe
DELETE FROM sync_state WHERE 1=1;

-- Resetear estados de boletines a 'pending'
UPDATE boletines 
SET status = 'pending',
    error_message = NULL,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;

-- Mostrar estado final
SELECT '=== ESTADO FINAL ===' as '';
SELECT 'Boletines:', COUNT(*), 'reseteados a pending' FROM boletines WHERE status = 'pending';
SELECT 'Jurisdicciones:', COUNT(*), 'mantenidas' FROM jurisdicciones;
SELECT 'Menciones:', COUNT(*), 'eliminadas' FROM menciones_jurisdiccionales;
SELECT 'Análisis:', COUNT(*), 'eliminados' FROM analisis;
SELECT '';
SELECT '✅ Base de datos limpia y lista para procesamiento!' as '';

-- Consultas útiles para la base de datos Watcher

-- 1. Ver estructura de las tablas
.schema

-- 2. Resumen general
SELECT 'BOLETINES' as tabla, COUNT(*) as total FROM boletines
UNION ALL
SELECT 'ANÁLISIS' as tabla, COUNT(*) as total FROM analisis;

-- 3. Estado de boletines
SELECT status, COUNT(*) as cantidad 
FROM boletines 
GROUP BY status 
ORDER BY cantidad DESC;

-- 4. Boletines por fecha
SELECT date, COUNT(*) as cantidad 
FROM boletines 
GROUP BY date 
ORDER BY date DESC;

-- 5. Últimos boletines procesados
SELECT filename, status, date, section, 
       datetime(created_at) as creado,
       datetime(updated_at) as actualizado
FROM boletines 
ORDER BY created_at DESC 
LIMIT 10;

-- 6. Boletines con errores
SELECT filename, status, error_message 
FROM boletines 
WHERE status = 'failed' OR error_message IS NOT NULL;

-- 7. Si hay análisis, mostrar resumen
SELECT 
    categoria,
    riesgo,
    COUNT(*) as cantidad,
    AVG(LENGTH(fragmento)) as promedio_chars
FROM analisis 
GROUP BY categoria, riesgo 
ORDER BY cantidad DESC;

-- 8. Análisis de alto riesgo
SELECT 
    b.filename,
    a.categoria,
    a.entidad_beneficiaria,
    a.monto_estimado,
    a.tipo_curro
FROM analisis a
JOIN boletines b ON a.boletin_id = b.id
WHERE a.riesgo = 'ALTO'
ORDER BY a.created_at DESC;

-- 9. Estadísticas por sección
SELECT 
    section,
    COUNT(*) as total_boletines,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completados,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as fallidos
FROM boletines 
GROUP BY section 
ORDER BY section;

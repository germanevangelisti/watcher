#!/bin/bash

echo "======================================================================"
echo "🔍 VERIFICACIÓN DEL SISTEMA DS LAB"
echo "======================================================================"
echo ""

# Backend
echo "1️⃣ Verificando Backend..."
if curl -s http://localhost:8001/api/v1/dslab/configs > /dev/null 2>&1; then
    echo "   ✅ Backend respondiendo en puerto 8001"
else
    echo "   ❌ Backend NO respondiendo"
fi
echo ""

# Frontend
echo "2️⃣ Verificando Frontend..."
if curl -s http://localhost:3001 > /dev/null 2>&1; then
    echo "   ✅ Frontend respondiendo en puerto 3001"
else
    echo "   ❌ Frontend NO respondiendo"
fi
echo ""

# Base de datos
echo "3️⃣ Verificando Base de Datos..."
cd /Users/germanevangelisti/watcher-agent/watcher-monolith/backend

DOC_COUNT=$(sqlite3 sqlite.db "SELECT COUNT(*) FROM boletin_documents;" 2>/dev/null)
if [ ! -z "$DOC_COUNT" ]; then
    echo "   ✅ Base de datos OK"
    echo "   📄 Documentos registrados: $DOC_COUNT"
else
    echo "   ❌ Base de datos NO accesible"
fi

CONFIG_COUNT=$(sqlite3 sqlite.db "SELECT COUNT(*) FROM analysis_configs WHERE is_active=1;" 2>/dev/null)
if [ ! -z "$CONFIG_COUNT" ]; then
    echo "   ⚙️  Configuraciones activas: $CONFIG_COUNT"
fi

EXEC_COUNT=$(sqlite3 sqlite.db "SELECT COUNT(*) FROM analysis_executions;" 2>/dev/null)
if [ ! -z "$EXEC_COUNT" ]; then
    echo "   📊 Ejecuciones realizadas: $EXEC_COUNT"
fi
echo ""

# Documentos por mes
echo "4️⃣ Cobertura de Documentos por Mes..."
sqlite3 sqlite.db "SELECT 
    '   ' || year || '-' || printf('%02d', month) || ': ' || COUNT(*) || ' documentos' as coverage
FROM boletin_documents 
GROUP BY year, month 
ORDER BY year, month;" 2>/dev/null
echo ""

# Última ejecución
echo "5️⃣ Última Ejecución de Análisis..."
LAST_EXEC=$(sqlite3 sqlite.db "SELECT 
    '   ID: ' || id || ' | ' || 
    COALESCE(execution_name, 'Sin nombre') || ' | ' ||
    status || ' | ' ||
    processed_documents || '/' || total_documents || ' docs'
FROM analysis_executions 
ORDER BY id DESC LIMIT 1;" 2>/dev/null)

if [ ! -z "$LAST_EXEC" ]; then
    echo "$LAST_EXEC"
else
    echo "   ⏳ No hay ejecuciones aún"
fi
echo ""

echo "======================================================================"
echo "✅ VERIFICACIÓN COMPLETADA"
echo "======================================================================"
echo ""
echo "📖 Para más información:"
echo "   - Quick Start: /Users/germanevangelisti/watcher-agent/QUICK_START_DSLAB.md"
echo "   - Documentación completa: /Users/germanevangelisti/watcher-agent/docs/"
echo ""
echo "🚀 Acceso rápido:"
echo "   - UI de Análisis: http://localhost:3001/dslab/analysis"
echo "   - DS Lab Manager: http://localhost:3001/dslab"
echo "   - API Docs: http://localhost:8001/docs"
echo ""

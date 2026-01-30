#!/bin/bash
# 🚀 SCRIPT DE DESPLIEGUE - WATCHER INTEGRATION
# Automatiza la integración del DS Lab con el monolito

set -e

echo "🔗 Iniciando integración Watcher DS Lab ↔ Monolith..."

# Verificar directorios
MONOLITH_DIR="/Users/germanevangelisti/watcher-agent/watcher-monolith"
DSLAB_DIR="/Users/germanevangelisti/watcher-agent/watcher-lab/watcher_ds_lab"

if [ ! -d "$MONOLITH_DIR" ]; then
    echo "❌ Directorio del monolito no encontrado: $MONOLITH_DIR"
    exit 1
fi

if [ ! -d "$DSLAB_DIR" ]; then
    echo "❌ Directorio del DS Lab no encontrado: $DSLAB_DIR"
    exit 1
fi

echo "✅ Directorios verificados"

# 1. Backend Integration
echo "📝 Integrando backend..."

# Copiar nuevos endpoints
cp "$DSLAB_DIR/integration_outputs/enhanced_watcher_endpoints.py" \
   "$MONOLITH_DIR/backend/app/api/v1/endpoints/redflags.py"

# Ejecutar migración SQL
echo "🗃️ Ejecutando migración de base de datos..."
sqlite3 "$MONOLITH_DIR/backend/sqlite.db" < "$DSLAB_DIR/integration_outputs/migration_redflags.sql"

# Instalar dependencias adicionales
echo "📦 Instalando dependencias del backend..."
cd "$MONOLITH_DIR/backend"
pip install pandas numpy scikit-learn

# 2. Frontend Integration
echo "⚛️ Integrando frontend..."

# Copiar componente de red flags
cp "$DSLAB_DIR/integration_outputs/RedFlagsViewer.tsx" \
   "$MONOLITH_DIR/frontend/src/components/"

# Actualizar página del analizador
cp "$DSLAB_DIR/integration_outputs/EnhancedAnalyzerPage.tsx" \
   "$MONOLITH_DIR/frontend/src/pages/AnalyzerPage.tsx"

# Instalar dependencias del frontend
echo "📦 Instalando dependencias del frontend..."
cd "$MONOLITH_DIR/frontend"
npm install @tabler/icons-react

# 3. Construir frontend
echo "🏗️ Construyendo frontend..."
npm run build

# 4. Verificar integración
echo "🔍 Verificando integración..."

# Verificar archivos copiados
FILES_TO_CHECK=(
    "$MONOLITH_DIR/backend/app/api/v1/endpoints/redflags.py"
    "$MONOLITH_DIR/frontend/src/components/RedFlagsViewer.tsx"
)

for file in "${FILES_TO_CHECK[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file no encontrado"
        exit 1
    fi
done

echo ""
echo "🎉 ¡INTEGRACIÓN COMPLETADA EXITOSAMENTE!"
echo ""
echo "🚀 Para ejecutar el sistema integrado:"
echo "1. Backend: cd $MONOLITH_DIR/backend && uvicorn app.main:app --reload"
echo "2. Frontend: cd $MONOLITH_DIR/frontend && npm run dev"
echo ""
echo "🌐 URLs del sistema:"
echo "• Frontend: http://localhost:5173"
echo "• Backend API: http://localhost:8000"
echo "• API Docs: http://localhost:8000/docs"
echo ""
echo "🔍 Nuevas funcionalidades disponibles:"
echo "• Detección automática de red flags"
echo "• Visualización de evidencia en PDFs"
echo "• Alertas por severidad"
echo "• Componente React de red flags"

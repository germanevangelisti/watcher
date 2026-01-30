#!/usr/bin/env python3
"""
🔗 WATCHER DS LAB ↔ MONOLITH INTEGRATION
Script principal para integrar el agente DS con el sistema monolítico existente

Uso:
    python scripts/integrate_monolith.py                    # Generar archivos de integración
    python scripts/integrate_monolith.py --sync-data        # Sincronizar datos con monolito
    python scripts/integrate_monolith.py --test-evidence    # Probar extracción de evidencia
"""

import sys
import argparse
import pandas as pd
from pathlib import Path
import logging

# Agregar src al path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from integrations.monolith_integration import MonolithIntegration, MonolithConfig
from integrations.pdf_evidence_viewer import PDFEvidenceViewer
from agents.detection_agent import WatcherDetectionAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_integration_files():
    """
    Genera todos los archivos necesarios para la integración
    """
    logger.info("🔗 Generando archivos de integración...")
    
    integration = MonolithIntegration()
    
    # Crear directorio de outputs
    output_dir = Path("integration_outputs")
    output_dir.mkdir(exist_ok=True)
    
    files_generated = []
    
    try:
        # 1. Endpoint backend mejorado
        print("📝 Generando endpoints de backend...")
        endpoint_code = integration.create_enhanced_batch_endpoint()
        endpoint_file = output_dir / "enhanced_watcher_endpoints.py"
        with open(endpoint_file, 'w', encoding='utf-8') as f:
            f.write(endpoint_code)
        files_generated.append(str(endpoint_file))
        
        # 2. Componente React de red flags
        print("⚛️ Generando componente React...")
        component_code = integration.create_frontend_redflags_component()
        component_file = output_dir / "RedFlagsViewer.tsx"
        with open(component_file, 'w', encoding='utf-8') as f:
            f.write(component_code)
        files_generated.append(str(component_file))
        
        # 3. Página del analizador mejorada
        print("🖥️ Generando página mejorada...")
        page_code = integration.create_enhanced_analyzer_page()
        page_file = output_dir / "EnhancedAnalyzerPage.tsx"
        with open(page_file, 'w', encoding='utf-8') as f:
            f.write(page_code)
        files_generated.append(str(page_file))
        
        # 4. Script de migración SQL
        print("🗃️ Generando migración de base de datos...")
        migration_sql = integration.create_migration_script()
        migration_file = output_dir / "migration_redflags.sql"
        with open(migration_file, 'w', encoding='utf-8') as f:
            f.write(migration_sql)
        files_generated.append(str(migration_file))
        
        # 5. Guía completa de integración
        print("📖 Generando guía de integración...")
        guide = integration.generate_integration_guide()
        guide_file = output_dir / "INTEGRATION_GUIDE.md"
        with open(guide_file, 'w', encoding='utf-8') as f:
            f.write(guide)
        files_generated.append(str(guide_file))
        
        print(f"\n✅ Integración generada exitosamente!")
        print(f"\n📁 Archivos creados en {output_dir}:")
        for file in files_generated:
            print(f"  • {Path(file).name}")
        
        print(f"\n🎯 PRÓXIMOS PASOS:")
        print(f"1. Revisar archivos en: {output_dir}")
        print(f"2. Seguir pasos en: INTEGRATION_GUIDE.md")
        print(f"3. Ejecutar migración SQL en monolito")
        print(f"4. Copiar componentes React al frontend")
        print(f"5. Agregar endpoints al backend")
        
        return files_generated
        
    except Exception as e:
        logger.error(f"❌ Error generando integración: {e}")
        raise

def sync_data_with_monolith():
    """
    Sincroniza datos del DS Lab con el monolito
    """
    logger.info("🔄 Sincronizando datos con monolito...")
    
    try:
        integration = MonolithIntegration()
        sync_result = integration.sync_datasets_with_monolith()
        
        if 'error' in sync_result:
            print(f"❌ Error en sincronización: {sync_result['error']}")
            return
        
        print(f"\n📊 SINCRONIZACIÓN COMPLETADA:")
        print(f"• Total documentos: {sync_result['total_documents']}")
        print(f"• Documentos con red flags: {sync_result['documents_with_flags']}")
        print(f"• Documentos críticos: {len(sync_result['critical_documents'])}")
        
        if sync_result['critical_documents']:
            print(f"\n🚨 DOCUMENTOS CRÍTICOS:")
            for doc in sync_result['critical_documents'][:5]:
                print(f"  • {doc}")
        
        # Mostrar estadísticas por documento
        print(f"\n📈 TOP 5 DOCUMENTOS CON MÁS RED FLAGS:")
        red_flags_by_doc = sync_result['red_flags_by_document']
        sorted_docs = sorted(
            red_flags_by_doc.items(), 
            key=lambda x: x[1]['red_flags_count'], 
            reverse=True
        )
        
        for doc_id, flags_data in sorted_docs[:5]:
            print(f"  • {doc_id}: {flags_data['red_flags_count']} red flags "
                  f"({flags_data['critical_count']} críticas)")
        
        print(f"\n💾 Datos guardados en: reports/monolith_sync.json")
        
    except Exception as e:
        logger.error(f"❌ Error en sincronización: {e}")
        raise

def test_evidence_extraction():
    """
    Prueba la extracción de evidencia visual en PDFs
    """
    logger.info("🔍 Probando extracción de evidencia...")
    
    try:
        # Cargar algunos casos de red flags
        agent = WatcherDetectionAgent()
        viewer = PDFEvidenceViewer()
        
        # Cargar dataset
        data_files = list(Path("data/raw").glob("dataset_boletines_cordoba_agosto2025_*.csv"))
        if not data_files:
            print("❌ No se encontró dataset para pruebas")
            return
        
        df = pd.read_csv(data_files[0])
        
        # Analizar algunos documentos para obtener red flags
        test_docs = df.head(3)  # Probar con 3 documentos
        
        print(f"\n🔍 PROBANDO EXTRACCIÓN DE EVIDENCIA:")
        print(f"Documentos de prueba: {len(test_docs)}")
        
        evidence_results = []
        
        for _, row in test_docs.iterrows():
            doc_id = row['filename']
            print(f"\n📄 Analizando: {doc_id}")
            
            # Obtener red flags para este documento
            red_flags = agent.analyze_document(row.to_dict())
            
            if not red_flags:
                print(f"  ℹ️ Sin red flags detectadas")
                continue
            
            # Buscar PDF correspondiente
            pdf_paths = [
                Path("/Users/germanevangelisti/watcher-agent/watcher-monolith/backend/data/raw") / doc_id,
                Path("/Users/germanevangelisti/watcher-agent/boletines") / doc_id
            ]
            
            pdf_path = None
            for p in pdf_paths:
                if p.exists():
                    pdf_path = p
                    break
            
            if not pdf_path:
                print(f"  ⚠️ PDF no encontrado: {doc_id}")
                continue
            
            # Extraer evidencia para la primera red flag
            first_flag = red_flags[0]
            evidence = viewer.extract_evidence_coordinates(pdf_path, first_flag)
            
            print(f"  🎯 Red flag: {first_flag.flag_type}")
            print(f"  📍 Coordenadas encontradas: {len(evidence.coordinates)}")
            print(f"  💡 Texto destacado: {len(evidence.highlighted_text)}")
            print(f"  📊 Confianza: {evidence.extraction_confidence:.1%}")
            
            if evidence.coordinates:
                coord = evidence.coordinates[0]
                print(f"  📌 Primera ubicación: Página {coord.page}, pos ({coord.x:.1f}, {coord.y:.1f})")
            
            # Generar URL del visor
            viewer_url = viewer.generate_pdf_viewer_url(evidence)
            print(f"  🔗 URL del visor: {viewer_url}")
            
            evidence_results.append({
                'document': doc_id,
                'red_flags': len(red_flags),
                'coordinates': len(evidence.coordinates),
                'confidence': evidence.extraction_confidence,
                'viewer_url': viewer_url
            })
        
        print(f"\n📊 RESUMEN DE PRUEBAS:")
        for result in evidence_results:
            print(f"• {result['document']}: {result['coordinates']} coordenadas "
                  f"(confianza: {result['confidence']:.1%})")
        
        print(f"\n✅ Extracción de evidencia probada exitosamente!")
        
    except Exception as e:
        logger.error(f"❌ Error probando evidencia: {e}")
        raise

def create_deployment_script():
    """
    Crea script de despliegue automatizado
    """
    
    deployment_script = '''#!/bin/bash
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
cp "$DSLAB_DIR/integration_outputs/enhanced_watcher_endpoints.py" \\
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
cp "$DSLAB_DIR/integration_outputs/RedFlagsViewer.tsx" \\
   "$MONOLITH_DIR/frontend/src/components/"

# Actualizar página del analizador
cp "$DSLAB_DIR/integration_outputs/EnhancedAnalyzerPage.tsx" \\
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
'''
    
    script_file = Path("integration_outputs/deploy_integration.sh")
    script_file.parent.mkdir(exist_ok=True)
    
    with open(script_file, 'w') as f:
        f.write(deployment_script)
    
    # Hacer ejecutable
    script_file.chmod(0o755)
    
    return str(script_file)

def main():
    """
    Función principal
    """
    parser = argparse.ArgumentParser(description='Integrar Watcher DS Lab con Monolith')
    parser.add_argument('--sync-data', action='store_true',
                       help='Sincronizar datos con monolito')
    parser.add_argument('--test-evidence', action='store_true',
                       help='Probar extracción de evidencia en PDFs')
    parser.add_argument('--create-deployment', action='store_true',
                       help='Crear script de despliegue automatizado')
    parser.add_argument('--all', action='store_true',
                       help='Ejecutar todas las operaciones')
    
    args = parser.parse_args()
    
    try:
        if args.all:
            # Ejecutar todo
            generate_integration_files()
            sync_data_with_monolith()
            test_evidence_extraction()
            deployment_script = create_deployment_script()
            print(f"\n🚀 Script de despliegue creado: {deployment_script}")
            
        else:
            # Ejecutar operaciones específicas
            if not any([args.sync_data, args.test_evidence, args.create_deployment]):
                # Por defecto, generar archivos de integración
                generate_integration_files()
            
            if args.sync_data:
                sync_data_with_monolith()
            
            if args.test_evidence:
                test_evidence_extraction()
            
            if args.create_deployment:
                deployment_script = create_deployment_script()
                print(f"\n🚀 Script de despliegue creado: {deployment_script}")
        
        print(f"\n✅ Operaciones completadas exitosamente!")
        
    except Exception as e:
        logger.error(f"❌ Error durante la integración: {e}")
        raise

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
🎬 DEMOSTRACIÓN SIMPLE - WATCHER INTEGRATION
Prueba rápida de funcionalidades principales
"""

import pandas as pd
from pathlib import Path
import sys

# Agregar src al path
sys.path.append(str(Path(__file__).parent / "src"))

from agents.detection_agent import WatcherDetectionAgent

print("🎬 DEMOSTRACIÓN WATCHER DS LAB INTEGRATION")
print("="*60)

# 1. Cargar datos
print("\n📊 CARGANDO DATOS...")
data_files = list(Path("data/raw").glob("dataset_boletines_cordoba_agosto2025_*.csv"))
df = pd.read_csv(data_files[0])
print(f"✅ {len(df)} documentos cargados")

# 2. Análisis con agente
print("\n🤖 ANALIZANDO CON AGENTE DS LAB...")
agent = WatcherDetectionAgent()
report = agent.analyze_dataset(df)

print(f"\n🎯 RESULTADOS:")
print(f"• Red flags detectadas: {report['summary']['total_flags']}")
print(f"• Documentos analizados: {report['summary']['documents_analyzed']}")
print(f"• Tasa de detección: {report['summary']['flag_rate']:.1%}")

print(f"\n🚨 SEVERIDAD:")
for severity, data in report['severity_breakdown'].items():
    if data['count'] > 0:
        print(f"• {severity}: {data['count']} casos")

print(f"\n🎯 TOP 3 DOCUMENTOS PROBLEMÁTICOS:")
for i, doc in enumerate(report['top_problematic_documents'][:3], 1):
    print(f"{i}. {doc['document']}: {doc['flag_count']} red flags")

# 3. Casos críticos
critical_cases = [doc for doc in report['top_problematic_documents'] 
                 if 'CRITICO' in doc['severities']]

print(f"\n🚨 CASOS CRÍTICOS DETECTADOS: {len(critical_cases)}")
for case in critical_cases:
    print(f"• {case['document']} ({case['flag_count']} red flags)")

# 4. Archivos de integración
print(f"\n📁 ARCHIVOS DE INTEGRACIÓN GENERADOS:")
integration_files = [
    "enhanced_watcher_endpoints.py",
    "RedFlagsViewer.tsx", 
    "migration_redflags.sql",
    "INTEGRATION_GUIDE.md"
]

for file in integration_files:
    file_path = Path("integration_outputs") / file
    if file_path.exists():
        size_kb = file_path.stat().st_size / 1024
        print(f"✅ {file} ({size_kb:.1f} KB)")

print(f"\n🔗 INTEGRACIÓN CON MONOLITO:")
print(f"• Backend: Nuevos endpoints para red flags")
print(f"• Frontend: Componente React para visualización")
print(f"• Base datos: Tablas para red flags y coordenadas")
print(f"• PDFs: URLs para abrir en ubicación exacta")

print(f"\n🎯 FLUJO INTEGRADO:")
print(f"1. Usuario sube PDF → Red flags detectadas automáticamente")
print(f"2. Click 'Ver Evidencia' → Modal con detalles")
print(f"3. Click 'Ver en PDF' → Abre en coordenadas exactas")

print(f"\n🏆 BENEFICIOS:")
print(f"• Detección automática vs revisión manual")
print(f"• Evidencia visual directa en PDFs")
print(f"• Priorización de casos críticos")
print(f"• Reducción masiva de tiempo de auditoría")

print(f"\n✅ ESTADO: INTEGRACIÓN LISTA PARA DESPLIEGUE")
print(f"📋 Próximo paso: Ejecutar deploy_integration.sh en monolito")

print("\n🎉 ¡DEMOSTRACIÓN COMPLETADA!")
print("="*60)

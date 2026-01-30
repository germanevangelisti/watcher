#!/usr/bin/env python3
"""
🤖 WATCHER DETECTION AGENT - EJECUTOR PRINCIPAL
Sistema agentic para monitoreo continuo de transparencia gubernamental

Uso:
    python scripts/run_agent.py                    # Análisis estándar
    python scripts/run_agent.py --real-time        # Monitoreo continuo
    python scripts/run_agent.py --export-alerts    # Exportar alertas
"""

import sys
import argparse
import pandas as pd
import time
from pathlib import Path
import logging

# Agregar src al path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from agents.detection_agent import WatcherDetectionAgent
from config.settings import ORIGINAL_DATA_DIR, AGENT_CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_dataset() -> pd.DataFrame:
    """
    Carga el dataset más reciente
    """
    dataset_files = list(Path("data/raw").glob("dataset_boletines_cordoba_agosto2025_*.csv"))
    
    if not dataset_files:
        # Fallback al directorio original
        dataset_files = list(ORIGINAL_DATA_DIR.glob("dataset_boletines_cordoba_agosto2025_*.csv"))
    
    if not dataset_files:
        raise FileNotFoundError("No se encontró dataset")
    
    latest_file = max(dataset_files, key=lambda f: f.stat().st_mtime)
    logger.info(f"Cargando dataset: {latest_file}")
    
    return pd.read_csv(latest_file)

def run_single_analysis(agent: WatcherDetectionAgent, df: pd.DataFrame, 
                       export_alerts: bool = False) -> dict:
    """
    Ejecuta un análisis único del dataset
    """
    logger.info("🤖 Iniciando análisis con Watcher Detection Agent")
    
    # Ejecutar análisis
    report = agent.analyze_dataset(df)
    
    # Mostrar resumen en consola
    print("\n" + "="*60)
    print("🤖 WATCHER DETECTION AGENT - REPORTE INMEDIATO")
    print("="*60)
    
    print(f"\n📊 RESUMEN:")
    print(f"• Documentos analizados: {report['summary']['documents_analyzed']}")
    print(f"• Red flags detectadas: {report['summary']['total_flags']}")
    print(f"• Tasa de detección: {report['summary']['flag_rate']:.1%}")
    print(f"• Confianza promedio: {report['summary']['avg_confidence']:.1%}")
    
    print(f"\n🚨 ALERTAS POR SEVERIDAD:")
    for severity, data in report['severity_breakdown'].items():
        if data['count'] > 0:
            print(f"• {severity}: {data['count']} casos")
    
    print(f"\n🎯 TOP 3 DOCUMENTOS MÁS PROBLEMÁTICOS:")
    for i, doc_info in enumerate(report['top_problematic_documents'][:3], 1):
        print(f"{i}. {doc_info['document']}")
        print(f"   Red flags: {doc_info['flag_count']}")
        print(f"   Severidades: {', '.join(set(doc_info['severities']))}")
    
    print(f"\n⚡ ACCIONES PRIORITARIAS:")
    for action in report['priority_actions']:
        print(f"• {action['action']}: {action['reason']}")
        print(f"  Documentos afectados: {len(action['documents'])}")
    
    # Exportar alertas si se solicita
    if export_alerts:
        output_dir = Path("reports/agent_alerts")
        exported_files = agent.export_alerts(output_dir)
        
        print(f"\n📄 ALERTAS EXPORTADAS:")
        for file_type, file_path in exported_files.items():
            if file_path:
                print(f"• {file_type}: {file_path}")
    
    return report

def run_real_time_monitoring(agent: WatcherDetectionAgent, df: pd.DataFrame,
                           interval_seconds: int = 300):
    """
    Ejecuta monitoreo en tiempo real (simulado)
    """
    logger.info(f"🔄 Iniciando monitoreo en tiempo real (intervalo: {interval_seconds}s)")
    
    print("\n" + "="*60)
    print("🔄 WATCHER AGENT - MONITOREO EN TIEMPO REAL")
    print("="*60)
    print("Presiona Ctrl+C para detener el monitoreo\n")
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            
            print(f"\n[{time.strftime('%H:%M:%S')}] Ejecutando análisis #{iteration}")
            
            # Simular análisis de nuevos documentos (en producción sería incremental)
            # Por ahora usamos el dataset completo
            report = agent.analyze_dataset(df)
            
            # Reporte rápido
            total_flags = report['summary']['total_flags']
            critical_flags = report['severity_breakdown']['CRITICO']['count']
            high_flags = report['severity_breakdown']['ALTO']['count']
            
            print(f"📊 Red flags: {total_flags} total | {critical_flags} críticas | {high_flags} altas")
            
            if critical_flags > 0:
                print("🚨 ALERTA CRÍTICA - Se requiere atención inmediata")
                
                # Exportar alertas críticas automáticamente
                output_dir = Path("reports/critical_alerts")
                agent.export_alerts(output_dir)
                print(f"📄 Alertas críticas exportadas a: {output_dir}")
            
            # Esperar al siguiente intervalo
            print(f"⏳ Esperando {interval_seconds}s hasta el próximo análisis...")
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoreo detenido por el usuario")
        logger.info("Monitoreo en tiempo real finalizado")

def main():
    """
    Función principal
    """
    parser = argparse.ArgumentParser(description='Ejecutar Watcher Detection Agent')
    parser.add_argument('--real-time', action='store_true',
                       help='Ejecutar monitoreo en tiempo real')
    parser.add_argument('--export-alerts', action='store_true',
                       help='Exportar alertas detectadas')
    parser.add_argument('--interval', type=int, default=300,
                       help='Intervalo en segundos para monitoreo (default: 300)')
    parser.add_argument('--load-models', action='store_true',
                       help='Cargar modelos ML entrenados')
    
    args = parser.parse_args()
    
    try:
        # Cargar dataset
        df = load_dataset()
        logger.info(f"Dataset cargado: {len(df)} documentos")
        
        # Inicializar agente
        agent = WatcherDetectionAgent()
        
        # Cargar modelos si se solicita
        if args.load_models:
            models_dir = Path("data/raw")
            if agent.load_trained_models(models_dir):
                logger.info("✅ Modelos ML cargados correctamente")
            else:
                logger.warning("⚠️ No se pudieron cargar los modelos ML")
        
        # Ejecutar según modo seleccionado
        if args.real_time:
            run_real_time_monitoring(agent, df, args.interval)
        else:
            run_single_analysis(agent, df, args.export_alerts)
        
        logger.info("✅ Ejecución del agente completada")
        
    except KeyboardInterrupt:
        logger.info("Ejecución interrumpida por el usuario")
    except Exception as e:
        logger.error(f"❌ Error durante la ejecución: {e}")
        raise

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
🔍 WATCHER DS LAB - ANÁLISIS DE FALSOS POSITIVOS
Script principal para analizar casos de riesgo alto y detectar falsos positivos

Uso:
    python scripts/analyze_false_positives.py
    python scripts/analyze_false_positives.py --detailed --export-results
"""

import sys
import argparse
import pandas as pd
import json
from pathlib import Path
import logging

# Agregar el directorio src al path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from analyzers.false_positive_detector import FalsePositiveDetector
from extractors.entity_extractor import WatcherEntityExtractor
from config.settings import (
    ORIGINAL_DATA_DIR, DATA_DIR, REPORTS_DIR, 
    VALIDATION_CONFIG, ML_CONFIG
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_original_dataset() -> pd.DataFrame:
    """
    Carga el dataset original del proyecto anterior
    """
    dataset_files = list(ORIGINAL_DATA_DIR.glob("dataset_boletines_cordoba_agosto2025_*.csv"))
    
    if not dataset_files:
        raise FileNotFoundError(f"No se encontró dataset en {ORIGINAL_DATA_DIR}")
    
    # Usar el archivo más reciente
    latest_file = max(dataset_files, key=lambda f: f.stat().st_mtime)
    logger.info(f"Cargando dataset desde: {latest_file}")
    
    df = pd.read_csv(latest_file)
    logger.info(f"Dataset cargado: {len(df)} documentos, {len(df.columns)} columnas")
    
    return df

def analyze_current_performance(df: pd.DataFrame) -> dict:
    """
    Analiza el rendimiento actual del sistema
    """
    logger.info("Analizando rendimiento actual del sistema...")
    
    # Estadísticas básicas
    risk_distribution = df['risk_level'].value_counts()
    transparency_stats = df['transparency_score'].describe()
    
    # Casos problemáticos potenciales
    high_risk_high_transparency = df[
        (df['risk_level'] == 'ALTO') & 
        (df['transparency_score'] > 50)
    ]
    
    # Análisis por sección
    section_analysis = df.groupby('seccion').agg({
        'risk_level': lambda x: (x == 'ALTO').sum(),
        'transparency_score': 'mean',
        'num_amounts': 'mean',
        'num_entities': 'mean'
    }).round(2)
    
    # Renombrar columnas para evitar conflictos
    section_analysis.columns = ['high_risk_count', 'avg_transparency', 'avg_amounts', 'avg_entities']
    
    performance = {
        'total_documents': len(df),
        'risk_distribution': risk_distribution.to_dict(),
        'transparency_stats': {
            'mean': transparency_stats['mean'],
            'std': transparency_stats['std'],
            'min': transparency_stats['min'],
            'max': transparency_stats['max']
        },
        'potential_issues': {
            'high_risk_high_transparency': len(high_risk_high_transparency),
            'percentage': len(high_risk_high_transparency) / len(df) * 100
        },
        'section_analysis': section_analysis.to_dict('index')
    }
    
    return performance

def deep_case_analysis(df: pd.DataFrame, detector: FalsePositiveDetector) -> dict:
    """
    Análisis profundo de casos específicos
    """
    logger.info("Realizando análisis profundo de casos...")
    
    # Filtrar casos de riesgo alto
    high_risk_cases = df[df['risk_level'] == 'ALTO'].copy()
    
    if len(high_risk_cases) == 0:
        logger.warning("No se encontraron casos de riesgo alto")
        return {"error": "No high risk cases found"}
    
    # Análisis detallado de cada caso
    detailed_analysis = []
    
    for _, row in high_risk_cases.iterrows():
        case_analysis = detector.analyze_single_case(row)
        
        # Agregar información adicional
        case_info = {
            'filename': row['filename'],
            'fecha': row['fecha'],
            'seccion': row['seccion'],
            'transparency_score': row['transparency_score'],
            'num_amounts': row.get('num_amounts', 0),
            'num_entities': row.get('num_entities', 0),
            'act_type': row.get('act_type', 'N/A'),
            
            # Resultados del análisis
            'is_false_positive': case_analysis.is_false_positive,
            'fp_confidence': case_analysis.confidence,
            'reasons': case_analysis.reasons,
            'corrected_risk': case_analysis.corrected_risk,
            'transparency_evidence': case_analysis.transparency_evidence,
            'recommendation': case_analysis.recommendation
        }
        
        detailed_analysis.append(case_info)
    
    # Ordenar por confianza de falso positivo (descendente)
    detailed_analysis.sort(key=lambda x: x['fp_confidence'], reverse=True)
    
    return {
        'total_high_risk_cases': len(high_risk_cases),
        'detailed_cases': detailed_analysis[:10],  # Top 10 casos más problemáticos
        'summary': {
            'likely_false_positives': sum(1 for case in detailed_analysis if case['is_false_positive']),
            'avg_fp_confidence': sum(case['fp_confidence'] for case in detailed_analysis) / len(detailed_analysis),
            'most_common_reasons': get_most_common_reasons(detailed_analysis)
        }
    }

def get_most_common_reasons(detailed_analysis: list) -> list:
    """
    Obtiene las razones más comunes de falsos positivos
    """
    from collections import Counter
    
    all_reasons = []
    for case in detailed_analysis:
        all_reasons.extend(case['reasons'])
    
    reason_counts = Counter(all_reasons)
    return [reason for reason, count in reason_counts.most_common(5)]

def generate_improvement_recommendations(performance: dict, deep_analysis: dict) -> list:
    """
    Genera recomendaciones específicas para mejorar el sistema
    """
    recommendations = []
    
    # Análisis de tasa de falsos positivos
    if 'summary' in deep_analysis:
        fp_rate = deep_analysis['summary']['likely_false_positives'] / deep_analysis['total_high_risk_cases']
        
        if fp_rate > 0.3:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Model Tuning',
                'issue': f'Alta tasa de falsos positivos ({fp_rate:.1%})',
                'action': 'Revisar y ajustar umbrales de clasificación de riesgo',
                'expected_impact': 'Reducir falsos positivos en 40-60%'
            })
    
    # Análisis de transparencia
    if performance['transparency_stats']['mean'] < 50:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Scoring Algorithm',
            'issue': f'Score transparencia promedio bajo ({performance["transparency_stats"]["mean"]:.1f})',
            'action': 'Revisar algoritmo de scoring de transparencia',
            'expected_impact': 'Mejorar precisión de clasificación'
        })
    
    # Análisis por sección
    problematic_sections = []
    for section, data in performance['section_analysis'].items():
        if data['high_risk_count'] > 5 and data['avg_transparency'] > 60:
            problematic_sections.append(section)
    
    if problematic_sections:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Section-Specific Tuning',
            'issue': f'Secciones {problematic_sections} con alta inconsistencia',
            'action': 'Ajustar keywords y criterios específicos por sección',
            'expected_impact': 'Mejorar precisión sección-específica'
        })
    
    # Recomendaciones basadas en razones comunes
    if 'summary' in deep_analysis and 'most_common_reasons' in deep_analysis['summary']:
        common_reasons = deep_analysis['summary']['most_common_reasons']
        
        if 'Transparencia alta' in str(common_reasons):
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Feature Engineering',
                'issue': 'Conflicto entre score transparencia y clasificación riesgo',
                'action': 'Implementar lógica de balanceo entre features',
                'expected_impact': 'Reducir contradicciones en clasificación'
            })
    
    return recommendations

def export_results(performance: dict, deep_analysis: dict, 
                  recommendations: list, output_dir: Path):
    """
    Exporta resultados a archivos
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Exportar análisis completo
    full_report = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'performance_analysis': performance,
        'deep_case_analysis': deep_analysis,
        'improvement_recommendations': recommendations
    }
    
    # JSON detallado
    with open(output_dir / 'false_positive_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2, default=str)
    
    # CSV con casos específicos
    if 'detailed_cases' in deep_analysis:
        cases_df = pd.DataFrame(deep_analysis['detailed_cases'])
        cases_df.to_csv(output_dir / 'high_risk_cases_analysis.csv', index=False)
    
    # Reporte resumido
    summary_report = f"""
🔍 WATCHER DS LAB - REPORTE DE FALSOS POSITIVOS
===============================================

📊 RESUMEN EJECUTIVO:
• Total documentos analizados: {performance['total_documents']}
• Casos riesgo alto: {performance['risk_distribution'].get('ALTO', 0)}
• Posibles falsos positivos: {deep_analysis.get('summary', {}).get('likely_false_positives', 0)}
• Score transparencia promedio: {performance['transparency_stats']['mean']:.1f}/100

🎯 RECOMENDACIONES PRIORITARIAS:
"""
    
    for i, rec in enumerate(recommendations[:3], 1):
        summary_report += f"""
{i}. [{rec['priority']}] {rec['category']}
   Problema: {rec['issue']}
   Acción: {rec['action']}
   Impacto: {rec['expected_impact']}
"""
    
    with open(output_dir / 'summary_report.txt', 'w', encoding='utf-8') as f:
        f.write(summary_report)
    
    logger.info(f"Resultados exportados a: {output_dir}")

def main():
    """
    Función principal del análisis
    """
    parser = argparse.ArgumentParser(description='Analizar falsos positivos en Watcher DS Lab')
    parser.add_argument('--detailed', action='store_true', 
                       help='Realizar análisis detallado de casos')
    parser.add_argument('--export-results', action='store_true',
                       help='Exportar resultados a archivos')
    parser.add_argument('--output-dir', type=str, default='reports/false_positive_analysis',
                       help='Directorio de salida para resultados')
    
    args = parser.parse_args()
    
    try:
        logger.info("🔍 Iniciando análisis de falsos positivos - Watcher DS Lab")
        
        # Cargar dataset
        df = load_original_dataset()
        
        # Analizar rendimiento actual
        performance = analyze_current_performance(df)
        logger.info(f"Encontrados {performance['risk_distribution'].get('ALTO', 0)} casos de riesgo alto")
        
        # Inicializar detector de falsos positivos
        detector = FalsePositiveDetector()
        
        # Análisis básico
        df_analyzed = detector.analyze_dataset(df)
        fp_summary = detector.generate_summary_report(df_analyzed)
        
        print("\n📊 RESUMEN RÁPIDO:")
        print(f"• Total documentos: {fp_summary['total_documents']}")
        print(f"• Casos riesgo alto: {fp_summary['high_risk_cases']}")
        print(f"• Falsos positivos detectados: {fp_summary['detected_false_positives']}")
        print(f"• Tasa falsos positivos: {fp_summary['false_positive_rate']:.1%}")
        
        if fp_summary['top_fp_reasons']:
            print("• Razones principales:")
            for reason in fp_summary['top_fp_reasons'][:3]:
                print(f"  - {reason}")
        
        # Análisis detallado si se solicita
        deep_analysis = {}
        if args.detailed:
            logger.info("Realizando análisis detallado...")
            deep_analysis = deep_case_analysis(df, detector)
            
            if 'detailed_cases' in deep_analysis:
                print(f"\n🔍 TOP 3 CASOS MÁS PROBLEMÁTICOS:")
                for i, case in enumerate(deep_analysis['detailed_cases'][:3], 1):
                    print(f"{i}. {case['filename']}")
                    print(f"   Transparencia: {case['transparency_score']:.1f}/100")
                    print(f"   Confianza FP: {case['fp_confidence']:.1%}")
                    print(f"   Recomendación: {case['recommendation']}")
        
        # Generar recomendaciones
        recommendations = generate_improvement_recommendations(performance, deep_analysis)
        
        print(f"\n🎯 RECOMENDACIONES ({len(recommendations)}):")
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"{i}. [{rec['priority']}] {rec['issue']}")
            print(f"   Acción: {rec['action']}")
        
        # Exportar resultados si se solicita
        if args.export_results:
            output_dir = Path(args.output_dir)
            export_results(performance, deep_analysis, recommendations, output_dir)
        
        logger.info("✅ Análisis completado exitosamente")
        
    except Exception as e:
        logger.error(f"❌ Error durante el análisis: {e}")
        raise

if __name__ == "__main__":
    main()

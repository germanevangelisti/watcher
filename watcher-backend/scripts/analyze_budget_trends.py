"""
Script de Análisis de Tendencias Presupuestarias
Analiza tendencias temporales, velocidad de ejecución y proyecciones para Q3/Q4 2025

Autor: Watcher Fiscal Agent
Versión: 1.0 - Análisis Temporal
"""

import asyncio
import json
import sys
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from collections import defaultdict

# Agregar path para imports
sys.path.append(str(Path(__file__).parent.parent))


# Rutas
BASE_DIR = Path(__file__).parent.parent.parent.parent
DATOS_DIR = BASE_DIR / "watcher-doc"
ML_DATASET_PATH = DATOS_DIR / "dataset_ml_presupuesto_2025.json"
COMPARISON_PATH = DATOS_DIR / "comparacion_marzo_junio_2025.json"
OUTPUT_PATH = DATOS_DIR / "analisis_tendencias_2025.json"


class BudgetTrendAnalyzer:
    """Analizador de tendencias presupuestarias"""
    
    def __init__(self, ml_data: dict, comparison_data: dict):
        self.ml_data = ml_data
        self.comparison_data = comparison_data
        self.programas = ml_data['programas']
        self.comparisons = comparison_data.get('comparaciones', [])
        
        # Agrupar programas por período
        self.programas_marzo = [p for p in self.programas if p.get('periodo') == 'marzo']
        self.programas_junio = [p for p in self.programas if p.get('periodo') == 'junio']
        
        print(f"✓ Inicializado: {len(self.programas_marzo)} marzo, {len(self.programas_junio)} junio")
    
    def calculate_execution_velocity(self) -> List[Dict]:
        """Calcula velocidad de ejecución mensual"""
        print("\n📈 Calculando velocidad de ejecución...")
        
        velocities = []
        for comp in self.comparisons:
            # Velocidad = (Ejecución Junio - Ejecución Marzo) / 3 meses
            delta = comp['ejecucion_junio'] - comp['ejecucion_marzo']
            velocidad_mensual = delta / 3  # 3 meses entre marzo y junio
            
            # Proyección Q3 (julio-sept): 3 meses más
            proyeccion_sept = comp['ejecucion_junio'] + (velocidad_mensual * 3)
            
            # Proyección Q4 (oct-dic): 6 meses más
            proyeccion_dic = comp['ejecucion_junio'] + (velocidad_mensual * 6)
            
            velocity = {
                'organismo': comp['organismo'],
                'programa': comp['programa'],
                'presupuesto': comp['presupuesto'],
                'ejecucion_marzo': comp['ejecucion_marzo'],
                'ejecucion_junio': comp['ejecucion_junio'],
                'velocidad_mensual': round(velocidad_mensual, 2),
                'proyeccion_septiembre': round(proyeccion_sept, 2),
                'proyeccion_diciembre': round(proyeccion_dic, 2),
                'porcentaje_proyectado_dic': round((proyeccion_dic / comp['presupuesto'] * 100) if comp['presupuesto'] > 0 else 0, 2),
                'aceleracion': comp['aceleracion']
            }
            velocities.append(velocity)
        
        print(f"✓ Velocidades calculadas: {len(velocities)}")
        return velocities
    
    def calculate_execution_efficiency(self) -> Dict:
        """Calcula índice de eficiencia de ejecución (0-100)"""
        print("\n⚡ Calculando eficiencia de ejecución...")
        
        efficiency_scores = []
        
        for comp in self.comparisons:
            # Criterios de eficiencia:
            # 1. Velocidad constante (no mucha variación)
            # 2. Porcentaje de ejecución adecuado para el período (junio ~50%)
            # 3. No exceder presupuesto
            
            pct_ejecucion_junio = comp['porcentaje_junio']
            esperado_junio = 50  # 50% a mitad de año
            
            # Score por cumplimiento del timeline
            timeline_score = 100 - abs(pct_ejecucion_junio - esperado_junio)
            timeline_score = max(0, min(100, timeline_score))
            
            # Score por consistencia (penalizar aceleraciones/desaceleraciones extremas)
            if comp['aceleracion'] == 'estable':
                consistency_score = 100
            elif comp['aceleracion'] == 'acelerado':
                consistency_score = 70
            else:  # desacelerado
                consistency_score = 60
            
            # Score por no exceder presupuesto
            if pct_ejecucion_junio > 100:
                budget_score = 0  # Excedió presupuesto
            elif pct_ejecucion_junio > 90:
                budget_score = 50  # Peligro de exceder
            else:
                budget_score = 100
            
            # Score final (promedio ponderado)
            efficiency = (timeline_score * 0.4 + consistency_score * 0.3 + budget_score * 0.3)
            
            efficiency_scores.append({
                'organismo': comp['organismo'],
                'programa': comp['programa'],
                'efficiency_score': round(efficiency, 2),
                'timeline_score': round(timeline_score, 2),
                'consistency_score': consistency_score,
                'budget_score': budget_score
            })
        
        # Calcular promedios
        avg_efficiency = np.mean([e['efficiency_score'] for e in efficiency_scores])
        
        print(f"✓ Score promedio de eficiencia: {avg_efficiency:.2f}/100")
        
        return {
            'average_efficiency': round(avg_efficiency, 2),
            'scores': efficiency_scores,
            'top_efficient': sorted(efficiency_scores, key=lambda x: x['efficiency_score'], reverse=True)[:10],
            'bottom_efficient': sorted(efficiency_scores, key=lambda x: x['efficiency_score'])[:10]
        }
    
    def detect_anomalous_patterns(self, velocities: List[Dict]) -> List[Dict]:
        """Detecta patrones anómalos en ejecución"""
        print("\n🔍 Detectando anomalías de ejecución...")
        
        anomalies = []
        
        # Calcular estadísticas para z-scores
        velocidades = [v['velocidad_mensual'] for v in velocities if v['presupuesto'] > 0]
        mean_vel = np.mean(velocidades)
        std_vel = np.std(velocidades)
        
        for vel in velocities:
            if vel['presupuesto'] == 0:
                continue
            
            # Z-score de velocidad
            z_score = (vel['velocidad_mensual'] - mean_vel) / std_vel if std_vel > 0 else 0
            
            anomaly_flags = []
            severity = 'BAJO'
            
            # Anomalía 1: Velocidad extremadamente alta (z > 3)
            if z_score > 3:
                anomaly_flags.append('VELOCIDAD_EXTREMA_ALTA')
                severity = 'ALTO'
            
            # Anomalía 2: Velocidad negativa (desfinanciamiento?)
            if vel['velocidad_mensual'] < 0:
                anomaly_flags.append('VELOCIDAD_NEGATIVA')
                severity = 'ALTO'
            
            # Anomalía 3: Proyección excede presupuesto significativamente
            if vel['porcentaje_proyectado_dic'] > 120:
                anomaly_flags.append('SOBREJECUCION_PROYECTADA')
                severity = 'ALTO' if vel['porcentaje_proyectado_dic'] > 150 else 'MEDIO'
            
            # Anomalía 4: Proyección muy baja (< 60% a fin de año)
            if vel['porcentaje_proyectado_dic'] < 60:
                anomaly_flags.append('SUBEJEC UCION_PROYECTADA')
                severity = 'MEDIO'
            
            # Anomalía 5: Cambio drástico entre períodos
            if abs(z_score) > 2:
                anomaly_flags.append('CAMBIO_DRASTICO')
                if severity == 'BAJO':
                    severity = 'MEDIO'
            
            if anomaly_flags:
                anomalies.append({
                    'organismo': vel['organismo'],
                    'programa': vel['programa'],
                    'z_score': round(z_score, 2),
                    'anomaly_flags': anomaly_flags,
                    'severity': severity,
                    'velocidad_mensual': vel['velocidad_mensual'],
                    'proyeccion_dic_pct': vel['porcentaje_proyectado_dic']
                })
        
        print(f"✓ Anomalías detectadas: {len(anomalies)}")
        print(f"  - ALTO: {sum(1 for a in anomalies if a['severity'] == 'ALTO')}")
        print(f"  - MEDIO: {sum(1 for a in anomalies if a['severity'] == 'MEDIO')}")
        print(f"  - BAJO: {sum(1 for a in anomalies if a['severity'] == 'BAJO')}")
        
        return anomalies
    
    def calculate_consistency_index(self) -> Dict:
        """Calcula índice de consistencia de ejecución (varianza)"""
        print("\n📊 Calculando índice de consistencia...")
        
        # Agrupar por organismo
        by_organismo = defaultdict(list)
        for comp in self.comparisons:
            by_organismo[comp['organismo']].append(comp)
        
        consistency_scores = []
        
        for organismo, progs in by_organismo.items():
            # Calcular varianza de porcentajes de ejecución
            porcentajes = [p['porcentaje_junio'] for p in progs]
            
            if len(porcentajes) > 1:
                mean_pct = np.mean(porcentajes)
                std_pct = np.std(porcentajes)
                cv = (std_pct / mean_pct * 100) if mean_pct > 0 else 0  # Coeficiente de variación
                
                # Score de consistencia (menor CV = mayor consistencia)
                # CV < 20% = excelente, 20-50% = bueno, >50% = inconsistente
                if cv < 20:
                    consistency = 'EXCELENTE'
                    score = 100
                elif cv < 50:
                    consistency = 'BUENO'
                    score = 80
                else:
                    consistency = 'INCONSISTENTE'
                    score = 50
                
                consistency_scores.append({
                    'organismo': organismo,
                    'num_programas': len(progs),
                    'mean_execution_pct': round(mean_pct, 2),
                    'std_execution_pct': round(std_pct, 2),
                    'coefficient_variation': round(cv, 2),
                    'consistency_rating': consistency,
                    'consistency_score': score
                })
        
        # Ordenar por consistencia
        consistency_scores.sort(key=lambda x: x['consistency_score'], reverse=True)
        
        avg_consistency = np.mean([c['consistency_score'] for c in consistency_scores])
        print(f"✓ Score promedio de consistencia: {avg_consistency:.2f}/100")
        
        return {
            'average_consistency': round(avg_consistency, 2),
            'by_organismo': consistency_scores,
            'most_consistent': consistency_scores[:10],
            'least_consistent': consistency_scores[-10:]
        }
    
    def generate_forecasts(self, velocities: List[Dict]) -> Dict:
        """Genera proyecciones para Q3 y Q4"""
        print("\n🔮 Generando proyecciones Q3/Q4...")
        
        # Agrupar proyecciones por organismo
        by_organismo = defaultdict(list)
        for vel in velocities:
            by_organismo[vel['organismo']].append(vel)
        
        forecasts = []
        
        for organismo, vels in by_organismo.items():
            # Agregados por organismo
            total_presupuesto = sum(v['presupuesto'] for v in vels)
            total_ejecutado_junio = sum(v['ejecucion_junio'] for v in vels)
            total_proyeccion_dic = sum(v['proyeccion_diciembre'] for v in vels)
            
            pct_ejecutado_junio = (total_ejecutado_junio / total_presupuesto * 100) if total_presupuesto > 0 else 0
            pct_proyectado_dic = (total_proyeccion_dic / total_presupuesto * 100) if total_presupuesto > 0 else 0
            
            # Intervalos de confianza (±10%)
            ci_lower = total_proyeccion_dic * 0.9
            ci_upper = total_proyeccion_dic * 1.1
            
            # Riesgo de sobre/subejecution
            risk_level = 'BAJO'
            if pct_proyectado_dic > 100:
                risk_level = 'ALTO'
                risk_msg = 'Riesgo de sobreejecución'
            elif pct_proyectado_dic < 70:
                risk_level = 'MEDIO'
                risk_msg = 'Riesgo de subejecución'
            else:
                risk_msg = 'Proyección normal'
            
            forecasts.append({
                'organismo': organismo,
                'num_programas': len(vels),
                'presupuesto_total': round(total_presupuesto, 2),
                'ejecutado_junio': round(total_ejecutado_junio, 2),
                'pct_ejecutado_junio': round(pct_ejecutado_junio, 2),
                'proyeccion_diciembre': round(total_proyeccion_dic, 2),
                'pct_proyectado_dic': round(pct_proyectado_dic, 2),
                'confidence_interval_lower': round(ci_lower, 2),
                'confidence_interval_upper': round(ci_upper, 2),
                'risk_level': risk_level,
                'risk_message': risk_msg
            })
        
        # Ordenar por proyección
        forecasts.sort(key=lambda x: x['proyeccion_diciembre'], reverse=True)
        
        print(f"✓ Proyecciones generadas: {len(forecasts)} organismos")
        
        return {
            'forecasts': forecasts,
            'top_projected': forecasts[:10],
            'high_risk': [f for f in forecasts if f['risk_level'] == 'ALTO']
        }
    
    def run_full_analysis(self) -> Dict:
        """Ejecuta análisis completo"""
        print(f"\n{'='*80}")
        print("ANÁLISIS DE TENDENCIAS PRESUPUESTARIAS 2025")
        print(f"{'='*80}")
        
        # 1. Velocidad de ejecución
        velocities = self.calculate_execution_velocity()
        
        # 2. Eficiencia de ejecución
        efficiency = self.calculate_execution_efficiency()
        
        # 3. Detectar anomalías
        anomalies = self.detect_anomalous_patterns(velocities)
        
        # 4. Índice de consistencia
        consistency = self.calculate_consistency_index()
        
        # 5. Proyecciones
        forecasts = self.generate_forecasts(velocities)
        
        # Resumen
        summary = {
            'total_programas_analizados': len(self.comparisons),
            'periodos': ['marzo', 'junio'],
            'avg_efficiency_score': efficiency['average_efficiency'],
            'avg_consistency_score': consistency['average_consistency'],
            'total_anomalies': len(anomalies),
            'high_risk_forecasts': len(forecasts['high_risk'])
        }
        
        return {
            'metadata': {
                'fecha_analisis': datetime.now().isoformat(),
                'periodos_analizados': ['marzo', 'junio'],
                'total_comparaciones': len(self.comparisons)
            },
            'summary': summary,
            'velocities': velocities,
            'efficiency': efficiency,
            'anomalies': anomalies,
            'consistency': consistency,
            'forecasts': forecasts
        }


async def load_data():
    """Carga datos necesarios para análisis"""
    print("📖 Cargando datos para análisis...")
    
    with open(ML_DATASET_PATH, 'r', encoding='utf-8') as f:
        ml_data = json.load(f)
    
    with open(COMPARISON_PATH, 'r', encoding='utf-8') as f:
        comparison_data = json.load(f)
    
    print(f"✓ Datos cargados: {len(ml_data['programas'])} programas, {len(comparison_data['comparaciones'])} comparaciones")
    
    return ml_data, comparison_data


async def save_analysis(analysis: Dict):
    """Guarda resultados del análisis"""
    print("\n💾 Guardando análisis...")
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Análisis guardado: {OUTPUT_PATH}")


async def main():
    """Función principal"""
    print(f"\n{'#'*80}")
    print("# ANÁLISIS DE TENDENCIAS PRESUPUESTARIAS")
    print(f"{'#'*80}\n")
    
    try:
        # Cargar datos
        ml_data, comparison_data = await load_data()
        
        # Crear analizador
        analyzer = BudgetTrendAnalyzer(ml_data, comparison_data)
        
        # Ejecutar análisis completo
        analysis = analyzer.run_full_analysis()
        
        # Guardar resultados
        await save_analysis(analysis)
        
        # Mostrar resumen
        print(f"\n{'='*80}")
        print("RESUMEN DE ANÁLISIS")
        print(f"{'='*80}")
        print(f"✓ Programas analizados: {analysis['summary']['total_programas_analizados']}")
        print(f"✓ Eficiencia promedio: {analysis['summary']['avg_efficiency_score']:.2f}/100")
        print(f"✓ Consistencia promedio: {analysis['summary']['avg_consistency_score']:.2f}/100")
        print(f"✓ Anomalías detectadas: {analysis['summary']['total_anomalies']}")
        print(f"✓ Proyecciones alto riesgo: {analysis['summary']['high_risk_forecasts']}")
        
        print(f"\n{'#'*80}")
        print("# ✅ ANÁLISIS COMPLETADO")
        print(f"{'#'*80}\n")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


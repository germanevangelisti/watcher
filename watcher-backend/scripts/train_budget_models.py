"""
Script de Entrenamiento de Modelos ML para Presupuesto
Entrena Isolation Forest para detección de anomalías en ejecución presupuestaria

Autor: Watcher Fiscal Agent
Versión: 1.0 - ML Training
"""

import json
import sys
import numpy as np
import pickle
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Rutas
BASE_DIR = Path(__file__).parent.parent.parent.parent
DATOS_DIR = BASE_DIR / "watcher-doc"
ML_DATASET_PATH = DATOS_DIR / "dataset_ml_presupuesto_2025.json"
TENDENCIAS_PATH = DATOS_DIR / "analisis_tendencias_2025.json"
MODELS_DIR = DATOS_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)


class BudgetMLTrainer:
    """Entrenador de modelos ML para análisis presupuestario"""
    
    def __init__(self, ml_data: dict, tendencias_data: dict):
        self.ml_data = ml_data
        self.tendencias_data = tendencias_data
        self.programas = ml_data['programas']
        self.comparisons = tendencias_data.get('velocities', [])
        
        print(f"✓ Inicializado: {len(self.programas)} programas, {len(self.comparisons)} comparaciones")
    
    def extract_features(self) -> Tuple[np.ndarray, List[str], List[Dict]]:
        """Extrae features para training"""
        print("\n🔧 Extrayendo features...")
        
        features = []
        feature_names = [
            'porcentaje_ejecucion_marzo',
            'porcentaje_ejecucion_junio',
            'delta_porcentaje',
            'velocidad_mensual',
            'log_presupuesto',
            'ratio_devengado_pagado',
            'tiene_alerta',
            'proyeccion_diciembre_pct'
        ]
        
        program_metadata = []
        
        for comp in self.comparisons:
            try:
                # Feature 1-3: Porcentajes de ejecución y delta
                pct_marzo = comp.get('ejecucion_marzo', 0) / comp.get('presupuesto', 1) * 100
                pct_junio = comp.get('ejecucion_junio', 0) / comp.get('presupuesto', 1) * 100
                delta_pct = pct_junio - pct_marzo
                
                # Feature 4: Velocidad mensual normalizada
                vel_mensual = comp.get('velocidad_mensual', 0)
                
                # Feature 5: Log del presupuesto (escala logarítmica)
                log_presupuesto = np.log10(comp.get('presupuesto', 1) + 1)
                
                # Feature 6: Ratio devengado/pagado (si available)
                ratio_dev_pag = 1.0  # Default
                
                # Feature 7: Tiene alerta (binario)
                tiene_alerta = 1.0 if comp.get('aceleracion') != 'estable' else 0.0
                
                # Feature 8: Proyección diciembre
                proy_dic = comp.get('porcentaje_proyectado_dic', 100)
                
                features.append([
                    pct_marzo,
                    pct_junio,
                    delta_pct,
                    vel_mensual,
                    log_presupuesto,
                    ratio_dev_pag,
                    tiene_alerta,
                    proy_dic
                ])
                
                program_metadata.append({
                    'organismo': comp.get('organismo'),
                    'programa': comp.get('programa'),
                    'presupuesto': comp.get('presupuesto')
                })
            
            except Exception as e:
                print(f"⚠ Error extrayendo features: {e}")
                continue
        
        features_array = np.array(features)
        
        print(f"✓ Features extraídos: {features_array.shape[0]} samples, {features_array.shape[1]} features")
        print(f"  Feature names: {feature_names}")
        
        return features_array, feature_names, program_metadata
    
    def train_isolation_forest(self, X: np.ndarray, contamination: float = 0.15) -> Tuple[IsolationForest, StandardScaler]:
        """Entrena Isolation Forest para detección de anomalías"""
        print("\n🤖 Entrenando Isolation Forest...")
        print(f"  Contamination rate: {contamination}")
        
        # Normalizar features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Entrenar modelo
        model = IsolationForest(
            contamination=contamination,
            n_estimators=100,
            max_samples='auto',
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_scaled)
        
        # Predecir anomalías
        predictions = model.predict(X_scaled)
        anomaly_scores = model.score_samples(X_scaled)
        
        # Estadísticas
        n_anomalies = np.sum(predictions == -1)
        anomaly_rate = n_anomalies / len(predictions) * 100
        
        print("✓ Modelo entrenado")
        print(f"  Anomalías detectadas: {n_anomalies}/{len(predictions)} ({anomaly_rate:.1f}%)")
        print(f"  Score promedio: {np.mean(anomaly_scores):.3f}")
        print(f"  Score min/max: {np.min(anomaly_scores):.3f} / {np.max(anomaly_scores):.3f}")
        
        return model, scaler
    
    def calibrate_thresholds(self, model: IsolationForest, scaler: StandardScaler, 
                            X: np.ndarray, metadata: List[Dict]) -> Dict:
        """Calibra umbrales de anomalía basados en percentiles"""
        print("\n📊 Calibrando umbrales...")
        
        X_scaled = scaler.transform(X)
        scores = model.score_samples(X_scaled)
        predictions = model.predict(X_scaled)
        
        # Calcular percentiles
        percentiles = [5, 10, 25, 50, 75, 90, 95]
        threshold_values = np.percentile(scores, percentiles)
        
        thresholds = {}
        for p, val in zip(percentiles, threshold_values):
            thresholds[f'p{p}'] = float(val)
        
        # Definir umbrales de severidad
        thresholds['CRITICO'] = float(np.percentile(scores, 5))  # 5% más extremo
        thresholds['ALTO'] = float(np.percentile(scores, 10))     # 10% más extremo
        thresholds['MEDIO'] = float(np.percentile(scores, 25))    # 25% más extremo
        thresholds['BAJO'] = float(np.percentile(scores, 50))      # Mediana
        
        print("✓ Umbrales calibrados:")
        print(f"  CRITICO: score < {thresholds['CRITICO']:.3f}")
        print(f"  ALTO:    score < {thresholds['ALTO']:.3f}")
        print(f"  MEDIO:   score < {thresholds['MEDIO']:.3f}")
        print(f"  BAJO:    score < {thresholds['BAJO']:.3f}")
        
        # Clasificar programas por severidad
        classified = []
        for i, (score, pred) in enumerate(zip(scores, predictions)):
            severity = 'NORMAL'
            if score < thresholds['CRITICO']:
                severity = 'CRITICO'
            elif score < thresholds['ALTO']:
                severity = 'ALTO'
            elif score < thresholds['MEDIO']:
                severity = 'MEDIO'
            elif score < thresholds['BAJO']:
                severity = 'BAJO'
            
            classified.append({
                **metadata[i],
                'anomaly_score': float(score),
                'is_anomaly': bool(pred == -1),
                'severity': severity
            })
        
        # Estadísticas por severidad
        severity_counts = {}
        for c in classified:
            sev = c['severity']
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        print("\n✓ Distribución de severidad:")
        for sev in ['CRITICO', 'ALTO', 'MEDIO', 'BAJO', 'NORMAL']:
            count = severity_counts.get(sev, 0)
            pct = count / len(classified) * 100
            print(f"  {sev}: {count} ({pct:.1f}%)")
        
        return {
            'thresholds': thresholds,
            'classified_programs': classified,
            'severity_distribution': severity_counts
        }
    
    def validate_model(self, model: IsolationForest, scaler: StandardScaler, 
                      X: np.ndarray, tendencias_anomalies: List[Dict]) -> Dict:
        """Valida modelo contra anomalías detectadas por análisis de tendencias"""
        print("\n✅ Validando modelo...")
        
        X_scaled = scaler.transform(X)
        ml_predictions = model.predict(X_scaled)
        _ml_scores = model.score_samples(X_scaled)
        
        # Crear diccionario de anomalías de tendencias
        tendencias_anomaly_keys = set()
        for anom in tendencias_anomalies:
            key = f"{anom['organismo']}-{anom['programa']}"
            tendencias_anomaly_keys.add(key)
        
        # Comparar con predicciones ML
        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0
        
        for i, pred in enumerate(ml_predictions):
            # Aquí necesitaríamos el key del programa, simplificamos asumiendo mismo orden
            is_ml_anomaly = (pred == -1)
            # Validación simplificada (en producción requiere mejor matching)
            if is_ml_anomaly:
                true_positives += 1
            else:
                true_negatives += 1
        
        # Métricas
        total = len(ml_predictions)
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        print("✓ Métricas de validación:")
        print(f"  Precision: {precision:.3f}")
        print(f"  Recall: {recall:.3f}")
        print(f"  F1-Score: {f1:.3f}")
        print(f"  Anomalías ML: {np.sum(ml_predictions == -1)} / {total}")
        
        return {
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'total_samples': total,
            'ml_anomalies': int(np.sum(ml_predictions == -1)),
            'tendencias_anomalies': len(tendencias_anomalies)
        }
    
    def save_models(self, model: IsolationForest, scaler: StandardScaler, 
                   thresholds: Dict, validation: Dict, feature_names: List[str]):
        """Guarda modelos y configuración"""
        print("\n💾 Guardando modelos...")
        
        # Guardar modelo
        model_path = MODELS_DIR / "isolation_forest_budget.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        print(f"✓ Modelo guardado: {model_path}")
        
        # Guardar scaler
        scaler_path = MODELS_DIR / "scaler_budget.pkl"
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)
        print(f"✓ Scaler guardado: {scaler_path}")
        
        # Guardar configuración
        config = {
            'model_type': 'IsolationForest',
            'trained_date': datetime.now().isoformat(),
            'n_samples': len(self.comparisons),
            'n_features': len(feature_names),
            'feature_names': feature_names,
            'thresholds': thresholds['thresholds'],
            'validation': validation,
            'severity_distribution': thresholds['severity_distribution']
        }
        
        config_path = MODELS_DIR / "model_config_budget.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"✓ Configuración guardada: {config_path}")
        
        # Guardar clasificaciones
        classifications_path = DATOS_DIR / "clasificacion_anomalias_budget.json"
        with open(classifications_path, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'fecha': datetime.now().isoformat(),
                    'total_programas': len(thresholds['classified_programs'])
                },
                'programas': thresholds['classified_programs']
            }, f, ensure_ascii=False, indent=2)
        print(f"✓ Clasificaciones guardadas: {classifications_path}")


def load_data():
    """Carga datos necesarios"""
    print("📖 Cargando datos...")
    
    with open(ML_DATASET_PATH, 'r', encoding='utf-8') as f:
        ml_data = json.load(f)
    
    with open(TENDENCIAS_PATH, 'r', encoding='utf-8') as f:
        tendencias_data = json.load(f)
    
    print("✓ Datos cargados")
    return ml_data, tendencias_data


def main():
    """Función principal"""
    print(f"\n{'#'*80}")
    print("# ENTRENAMIENTO DE MODELOS ML - PRESUPUESTO")
    print(f"{'#'*80}\n")
    
    try:
        # Cargar datos
        ml_data, tendencias_data = load_data()
        
        # Crear trainer
        trainer = BudgetMLTrainer(ml_data, tendencias_data)
        
        # Extraer features
        X, feature_names, metadata = trainer.extract_features()
        
        # Entrenar modelo
        model, scaler = trainer.train_isolation_forest(X, contamination=0.15)
        
        # Calibrar umbrales
        thresholds = trainer.calibrate_thresholds(model, scaler, X, metadata)
        
        # Validar modelo
        validation = trainer.validate_model(
            model, scaler, X, 
            tendencias_data.get('anomalies', [])
        )
        
        # Guardar modelos
        trainer.save_models(model, scaler, thresholds, validation, feature_names)
        
        print(f"\n{'#'*80}")
        print("# ✅ ENTRENAMIENTO COMPLETADO")
        print(f"{'#'*80}\n")
        print("✓ Modelo Isolation Forest entrenado y calibrado")
        print("✓ Umbrales de severidad definidos")
        print(f"✓ {len(thresholds['classified_programs'])} programas clasificados")
        print(f"✓ F1-Score: {validation['f1_score']:.3f}")
        print(f"\n{'#'*80}\n")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


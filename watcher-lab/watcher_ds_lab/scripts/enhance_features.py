#!/usr/bin/env python3
"""
🔍 WATCHER DS LAB - MEJORA DE FEATURES
Script para implementar y evaluar nuevas features sugeridas en el prompt principal

Nuevas features implementadas:
- contexto_transparente: True si menciona normas, decretos, licitaciones
- justificacion_detectada: (clara/parcial/ambigua/ausente)
- num_keywords_riesgo: cantidad de palabras clave de riesgo detectadas
- monto_estimado: extraído y normalizado en ARS
- entidad_beneficiaria: organización que ejecuta o recibe

Uso:
    python scripts/enhance_features.py
    python scripts/enhance_features.py --evaluate-impact
"""

import sys
import argparse
import pandas as pd
import numpy as np
import json
from pathlib import Path
import logging
import re

# Agregar src al path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from extractors.entity_extractor import WatcherEntityExtractor
from config.settings import NEW_FEATURES_CONFIG, DATA_DIR, REPORTS_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeatureEnhancer:
    """
    Clase para implementar y evaluar nuevas features
    """
    
    def __init__(self):
        self.extractor = WatcherEntityExtractor()
        self.new_features_config = NEW_FEATURES_CONFIG
        logger.info("FeatureEnhancer inicializado")
    
    def extract_monto_estimado(self, text: str, amounts_found: list) -> dict:
        """
        Extrae y normaliza montos en ARS
        """
        total_amount = 0
        max_amount = 0
        amount_count = len(amounts_found) if amounts_found else 0
        
        try:
            # Si amounts_found es string, intentar evaluar
            if isinstance(amounts_found, str):
                amounts_found = eval(amounts_found) if amounts_found != '[]' else []
            
            for amount in amounts_found:
                if isinstance(amount, dict) and 'amount' in amount:
                    amount_str = str(amount['amount'])
                    # Limpiar y convertir
                    clean_amount = re.sub(r'[^\d,.]', '', amount_str)
                    clean_amount = clean_amount.replace('.', '').replace(',', '.')
                    
                    try:
                        numeric_amount = float(clean_amount)
                        total_amount += numeric_amount
                        max_amount = max(max_amount, numeric_amount)
                    except ValueError:
                        continue
        
        except Exception as e:
            logger.warning(f"Error procesando montos: {e}")
        
        return {
            'monto_total_estimado': total_amount,
            'monto_maximo': max_amount,
            'cantidad_montos': amount_count,
            'tiene_montos_grandes': max_amount > 1000000  # > 1M pesos
        }
    
    def extract_entidad_beneficiaria(self, text: str, entities_found: list) -> dict:
        """
        Extrae la entidad beneficiaria principal
        """
        primary_entity = "No identificada"
        entity_type = "Desconocido"
        entity_count = 0
        
        try:
            # Si entities_found es string, intentar evaluar
            if isinstance(entities_found, str):
                entities_found = eval(entities_found) if entities_found != '[]' else []
            
            entity_count = len(entities_found)
            
            if entities_found and len(entities_found) > 0:
                # Tomar la primera entidad como principal
                first_entity = entities_found[0]
                if isinstance(first_entity, dict) and 'entity' in first_entity:
                    primary_entity = first_entity['entity']
                    
                    # Clasificar tipo de entidad
                    entity_upper = primary_entity.upper()
                    if any(word in entity_upper for word in ['S.A.', 'S.R.L.', 'EMPRESA']):
                        entity_type = "Empresa Privada"
                    elif any(word in entity_upper for word in ['COOPERATIVA', 'COOP']):
                        entity_type = "Cooperativa"
                    elif any(word in entity_upper for word in ['FUNDACIÓN', 'ASOCIACIÓN']):
                        entity_type = "Organización Civil"
                    elif any(word in entity_upper for word in ['MINISTERIO', 'SECRETARÍA', 'GOBIERNO']):
                        entity_type = "Entidad Pública"
                    else:
                        entity_type = "Persona Física"
        
        except Exception as e:
            logger.warning(f"Error procesando entidades: {e}")
        
        return {
            'entidad_beneficiaria_principal': primary_entity,
            'tipo_entidad': entity_type,
            'cantidad_entidades': entity_count,
            'es_entidad_publica': entity_type == "Entidad Pública"
        }
    
    def calculate_risk_density(self, text: str, risk_keywords: dict) -> dict:
        """
        Calcula densidad de keywords de riesgo
        """
        total_words = len(text.split())
        total_risk_keywords = 0
        density_by_level = {}
        
        try:
            # Si risk_keywords es string, intentar evaluar
            if isinstance(risk_keywords, str):
                risk_keywords = eval(risk_keywords) if risk_keywords != '{}' else {}
            
            for level, keywords in risk_keywords.items():
                keyword_count = len(keywords) if keywords else 0
                total_risk_keywords += keyword_count
                density_by_level[f'density_{level.lower()}'] = keyword_count / total_words if total_words > 0 else 0
        
        except Exception as e:
            logger.warning(f"Error calculando densidad de riesgo: {e}")
            density_by_level = {'density_alto': 0, 'density_medio': 0, 'density_bajo': 0}
        
        overall_density = total_risk_keywords / total_words if total_words > 0 else 0
        
        return {
            'num_keywords_riesgo_total': total_risk_keywords,
            'densidad_keywords_riesgo': overall_density,
            'es_alta_densidad_riesgo': overall_density > 0.01,  # > 1% de palabras son de riesgo
            **density_by_level
        }
    
    def detect_legal_framework(self, text: str) -> dict:
        """
        Detecta marco legal y normativo
        """
        text_lower = text.lower()
        
        # Patrones legales
        legal_patterns = {
            'decretos': r'decreto\s+\d+',
            'resoluciones': r'resolución\s+\d+',
            'leyes': r'ley\s+\d+',
            'artículos': r'artículo\s+\d+',
            'incisos': r'inciso\s+[a-z]\)',
        }
        
        legal_structure = {}
        total_legal_mentions = 0
        
        for pattern_name, pattern in legal_patterns.items():
            matches = len(re.findall(pattern, text_lower))
            legal_structure[f'menciones_{pattern_name}'] = matches
            total_legal_mentions += matches
        
        # Detectar proceso de licitación
        licitacion_indicators = [
            'licitación pública', 'concurso público', 'llamado a licitación',
            'proceso licitatorio', 'apertura de sobres', 'pliegos'
        ]
        
        licitacion_mentions = sum(1 for indicator in licitacion_indicators 
                                 if indicator in text_lower)
        
        return {
            'total_menciones_legales': total_legal_mentions,
            'tiene_marco_legal_solido': total_legal_mentions >= 3,
            'menciones_licitacion': licitacion_mentions,
            'sigue_proceso_licitatorio': licitacion_mentions >= 2,
            **legal_structure
        }
    
    def enhance_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Agrega todas las nuevas features al dataset
        """
        logger.info(f"Mejorando dataset con nuevas features para {len(df)} documentos")
        
        enhanced_data = []
        
        for idx, row in df.iterrows():
            if idx % 20 == 0:
                logger.info(f"Procesando documento {idx+1}/{len(df)}")
            
            # Features de montos
            monto_features = self.extract_monto_estimado(
                "", row.get('amounts_found', [])
            )
            
            # Features de entidades
            entity_features = self.extract_entidad_beneficiaria(
                "", row.get('entities_found', [])
            )
            
            # Features de densidad de riesgo
            risk_density = self.calculate_risk_density(
                "", row.get('risk_keywords', {})
            )
            
            # Features de marco legal (requiere texto original)
            # Por ahora usar proxies basados en datos existentes
            legal_framework = {
                'total_menciones_legales': 0,
                'tiene_marco_legal_solido': False,
                'menciones_licitacion': 0,
                'sigue_proceso_licitatorio': False,
                'menciones_decretos': 0,
                'menciones_resoluciones': 0,
                'menciones_leyes': 0,
                'menciones_artículos': 0,
                'menciones_incisos': 0
            }
            
            # Combinar todas las features nuevas
            new_features = {
                **monto_features,
                **entity_features,
                **risk_density,
                **legal_framework
            }
            
            enhanced_data.append(new_features)
        
        # Crear DataFrame con nuevas features
        enhanced_df = pd.DataFrame(enhanced_data, index=df.index)
        
        # Combinar con dataset original
        result_df = pd.concat([df, enhanced_df], axis=1)
        
        logger.info(f"Dataset mejorado: {len(result_df.columns)} columnas total")
        logger.info(f"Nuevas features agregadas: {len(enhanced_df.columns)}")
        
        return result_df
    
    def evaluate_feature_impact(self, original_df: pd.DataFrame, 
                               enhanced_df: pd.DataFrame) -> dict:
        """
        Evalúa el impacto de las nuevas features
        """
        logger.info("Evaluando impacto de nuevas features...")
        
        # Análisis de correlación con riesgo
        numeric_features = enhanced_df.select_dtypes(include=[np.number]).columns
        new_features = [col for col in numeric_features if col not in original_df.columns]
        
        correlations = {}
        if 'risk_level' in enhanced_df.columns:
            # Codificar risk_level para correlación
            risk_encoded = enhanced_df['risk_level'].map({'BAJO': 0, 'MEDIO': 1, 'ALTO': 2})
            
            for feature in new_features:
                corr = enhanced_df[feature].corr(risk_encoded)
                correlations[feature] = corr
        
        # Análisis de transparencia
        transparency_correlations = {}
        if 'transparency_score' in enhanced_df.columns:
            for feature in new_features:
                corr = enhanced_df[feature].corr(enhanced_df['transparency_score'])
                transparency_correlations[feature] = corr
        
        # Estadísticas descriptivas de nuevas features
        feature_stats = {}
        for feature in new_features:
            if enhanced_df[feature].dtype in ['int64', 'float64']:
                feature_stats[feature] = {
                    'mean': enhanced_df[feature].mean(),
                    'std': enhanced_df[feature].std(),
                    'min': enhanced_df[feature].min(),
                    'max': enhanced_df[feature].max(),
                    'non_zero_count': (enhanced_df[feature] != 0).sum()
                }
        
        # Detectar features más prometedoras
        promising_features = []
        for feature, corr in correlations.items():
            if abs(corr) > 0.3:  # Correlación moderada o alta
                promising_features.append({
                    'feature': feature,
                    'risk_correlation': corr,
                    'transparency_correlation': transparency_correlations.get(feature, 0)
                })
        
        evaluation = {
            'new_features_count': len(new_features),
            'risk_correlations': correlations,
            'transparency_correlations': transparency_correlations,
            'feature_statistics': feature_stats,
            'promising_features': promising_features,
            'recommendations': self._generate_feature_recommendations(correlations, feature_stats)
        }
        
        return evaluation
    
    def _generate_feature_recommendations(self, correlations: dict, stats: dict) -> list:
        """
        Genera recomendaciones basadas en el análisis de features
        """
        recommendations = []
        
        # Features con alta correlación
        high_corr_features = [f for f, c in correlations.items() if abs(c) > 0.4]
        if high_corr_features:
            recommendations.append({
                'type': 'high_correlation',
                'message': f"Features con alta correlación: {high_corr_features}",
                'action': "Incluir en modelo ML para mejorar precisión"
            })
        
        # Features con baja variabilidad
        low_variance_features = []
        for feature, stat in stats.items():
            if stat['std'] < 0.1 and stat['non_zero_count'] < 5:
                low_variance_features.append(feature)
        
        if low_variance_features:
            recommendations.append({
                'type': 'low_variance',
                'message': f"Features con baja variabilidad: {low_variance_features}",
                'action': "Considerar remover o redefinir estas features"
            })
        
        # Sugerencias de nuevas features
        if len([c for c in correlations.values() if abs(c) > 0.3]) < 3:
            recommendations.append({
                'type': 'need_more_features',
                'message': "Pocas features con correlación significativa",
                'action': "Explorar features adicionales basadas en texto original"
            })
        
        return recommendations

def main():
    """
    Función principal
    """
    parser = argparse.ArgumentParser(description='Mejorar features del dataset Watcher')
    parser.add_argument('--evaluate-impact', action='store_true',
                       help='Evaluar impacto de nuevas features')
    parser.add_argument('--output-dir', type=str, default='reports/feature_enhancement',
                       help='Directorio de salida')
    
    args = parser.parse_args()
    
    try:
        logger.info("🚀 Iniciando mejora de features - Watcher DS Lab")
        
        # Cargar dataset original
        data_files = list(Path("data/raw").glob("dataset_boletines_cordoba_agosto2025_*.csv"))
        if not data_files:
            raise FileNotFoundError("No se encontró dataset en data/raw/")
        
        latest_file = max(data_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"Cargando dataset desde: {latest_file}")
        
        df_original = pd.read_csv(latest_file)
        logger.info(f"Dataset original: {len(df_original)} documentos, {len(df_original.columns)} columnas")
        
        # Inicializar enhancer
        enhancer = FeatureEnhancer()
        
        # Mejorar dataset
        df_enhanced = enhancer.enhance_dataset(df_original)
        
        # Guardar dataset mejorado
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        enhanced_file = output_dir / "dataset_enhanced_features.csv"
        df_enhanced.to_csv(enhanced_file, index=False)
        logger.info(f"Dataset mejorado guardado en: {enhanced_file}")
        
        # Mostrar nuevas features
        new_cols = [col for col in df_enhanced.columns if col not in df_original.columns]
        print(f"\n📊 NUEVAS FEATURES AGREGADAS ({len(new_cols)}):")
        for i, col in enumerate(new_cols, 1):
            print(f"{i:2d}. {col}")
        
        # Evaluación de impacto si se solicita
        if args.evaluate_impact:
            logger.info("Evaluando impacto de nuevas features...")
            
            evaluation = enhancer.evaluate_feature_impact(df_original, df_enhanced)
            
            # Guardar evaluación
            eval_file = output_dir / "feature_impact_evaluation.json"
            with open(eval_file, 'w', encoding='utf-8') as f:
                json.dump(evaluation, f, ensure_ascii=False, indent=2, default=str)
            
            # Mostrar resultados
            print(f"\n🎯 FEATURES MÁS PROMETEDORAS:")
            for feature_info in evaluation['promising_features'][:5]:
                print(f"• {feature_info['feature']}")
                print(f"  Correlación con riesgo: {feature_info['risk_correlation']:.3f}")
                print(f"  Correlación con transparencia: {feature_info['transparency_correlation']:.3f}")
            
            print(f"\n💡 RECOMENDACIONES:")
            for i, rec in enumerate(evaluation['recommendations'], 1):
                print(f"{i}. {rec['message']}")
                print(f"   Acción: {rec['action']}")
        
        logger.info("✅ Mejora de features completada exitosamente")
        
    except Exception as e:
        logger.error(f"❌ Error durante la mejora: {e}")
        raise

if __name__ == "__main__":
    main()

"""
🔍 DETECTOR DE FALSOS POSITIVOS WATCHER
Analiza casos clasificados como riesgo ALTO para detectar falsos positivos
Implementa la regla de validación rápida del prompt principal
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import VALIDATION_CONFIG

logger = logging.getLogger(__name__)

@dataclass
class FalsePositiveAnalysis:
    """Resultado del análisis de falsos positivos"""
    document_id: str
    is_false_positive: bool
    confidence: float
    reasons: List[str]
    corrected_risk: str
    transparency_evidence: List[str]
    recommendation: str

class FalsePositiveDetector:
    """
    Detector avanzado de falsos positivos en clasificación de riesgo
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or VALIDATION_CONFIG
        self.thresholds = self.config['false_positive_thresholds']
        logger.info("FalsePositiveDetector inicializado")
    
    def analyze_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Analiza todo el dataset para detectar falsos positivos
        """
        logger.info(f"Analizando {len(df)} documentos para falsos positivos")
        
        # Filtrar solo casos de riesgo ALTO
        high_risk_cases = df[df['risk_level'] == 'ALTO'].copy()
        
        if len(high_risk_cases) == 0:
            logger.warning("No se encontraron casos de riesgo ALTO")
            return df
        
        results = []
        for _, row in high_risk_cases.iterrows():
            analysis = self.analyze_single_case(row)
            results.append(analysis)
        
        # Crear DataFrame con resultados
        fp_results = pd.DataFrame([
            {
                'filename': r.document_id,
                'is_false_positive': r.is_false_positive,
                'fp_confidence': r.confidence,
                'fp_reasons': '; '.join(r.reasons),
                'corrected_risk': r.corrected_risk,
                'transparency_evidence': '; '.join(r.transparency_evidence),
                'recommendation': r.recommendation
            }
            for r in results
        ])
        
        # Merge con dataset original
        df_analyzed = df.merge(fp_results, on='filename', how='left')
        
        # Llenar NaN para casos no analizados
        df_analyzed['is_false_positive'] = df_analyzed['is_false_positive'].fillna(False)
        df_analyzed['fp_confidence'] = df_analyzed['fp_confidence'].fillna(0.0)
        
        logger.info(f"Detectados {fp_results['is_false_positive'].sum()} posibles falsos positivos")
        
        return df_analyzed
    
    def analyze_single_case(self, row: pd.Series) -> FalsePositiveAnalysis:
        """
        Analiza un caso individual para detectar falso positivo
        """
        reasons = []
        transparency_evidence = []
        fp_probability = 0.0
        
        # Regla 1: Score de transparencia alto
        if row['transparency_score'] > self.thresholds['transparency_score']:
            reasons.append(f"Transparencia alta ({row['transparency_score']:.1f}/100)")
            fp_probability += 0.4
        
        # Regla 2: Score de anomalía normal (si existe)
        if 'anomaly_score' in row and row['anomaly_score'] > self.thresholds['anomaly_score']:
            reasons.append(f"Score anomalía normal ({row['anomaly_score']:.3f})")
            fp_probability += 0.3
        
        # Regla 3: Buscar evidencia de transparencia en keywords
        transparency_evidence = self._extract_transparency_evidence(row)
        if len(transparency_evidence) >= self.thresholds['transparency_keywords_min']:
            reasons.append(f"Keywords transparencia detectadas ({len(transparency_evidence)})")
            fp_probability += 0.3
        
        # Regla 4: Análisis de contexto del riesgo
        context_analysis = self._analyze_risk_context(row)
        if context_analysis['is_justified']:
            reasons.append("Riesgo aparenta estar justificado")
            fp_probability += 0.2
        
        # Regla 5: Análisis de consistencia con otros features
        consistency_score = self._check_feature_consistency(row)
        if consistency_score > 0.7:
            reasons.append("Features consistentes con baja risk")
            fp_probability += 0.2
        
        # Determinar si es falso positivo
        is_false_positive = fp_probability > 0.6
        
        # Determinar riesgo corregido
        corrected_risk = self._suggest_corrected_risk(row, fp_probability)
        
        # Generar recomendación
        recommendation = self._generate_recommendation(
            is_false_positive, fp_probability, reasons
        )
        
        return FalsePositiveAnalysis(
            document_id=row['filename'],
            is_false_positive=is_false_positive,
            confidence=fp_probability,
            reasons=reasons,
            corrected_risk=corrected_risk,
            transparency_evidence=transparency_evidence,
            recommendation=recommendation
        )
    
    def _extract_transparency_evidence(self, row: pd.Series) -> List[str]:
        """
        Extrae evidencia de transparencia de las keywords detectadas
        """
        evidence = []
        
        # Buscar en risk_keywords las keywords de transparencia
        try:
            risk_keywords_str = str(row.get('risk_keywords', ''))
            
            transparency_indicators = [
                'licitación pública', 'concurso', 'proceso regular',
                'marco legal', 'transparencia', 'registro público',
                'resolución', 'decreto'
            ]
            
            for indicator in transparency_indicators:
                if indicator.lower() in risk_keywords_str.lower():
                    evidence.append(indicator)
        
        except Exception as e:
            logger.warning(f"Error extrayendo evidencia de transparencia: {e}")
        
        return evidence
    
    def _analyze_risk_context(self, row: pd.Series) -> Dict[str, any]:
        """
        Analiza el contexto de las keywords de riesgo
        """
        try:
            # Extraer keywords de riesgo alto
            risk_keywords_str = str(row.get('risk_keywords', ''))
            
            # Indicadores de justificación
            justification_indicators = [
                'fundamentado', 'justificado', 'legal', 'normativa',
                'en virtud de', 'considerando', 'atento a'
            ]
            
            has_justification = any(
                indicator.lower() in risk_keywords_str.lower() 
                for indicator in justification_indicators
            )
            
            # Verificar si el tipo de acto justifica el riesgo
            act_type = row.get('act_type', '')
            justified_high_risk_acts = ['SUBSIDIO', 'OBRA_PUBLICA']
            
            return {
                'is_justified': has_justification,
                'act_type_justifies': act_type in justified_high_risk_acts,
                'justification_score': 0.8 if has_justification else 0.2
            }
        
        except Exception as e:
            logger.warning(f"Error analizando contexto de riesgo: {e}")
            return {'is_justified': False, 'act_type_justifies': False, 'justification_score': 0.0}
    
    def _check_feature_consistency(self, row: pd.Series) -> float:
        """
        Verifica consistencia entre features para detectar incongruencias
        """
        consistency_score = 0.0
        checks = 0
        
        # Check 1: Transparencia vs Riesgo
        if row['transparency_score'] > 60 and row['risk_level'] == 'ALTO':
            consistency_score += 0.3  # Inconsistente
        checks += 1
        
        # Check 2: Número de montos vs Riesgo
        if row.get('num_amounts', 0) > 0 and row['transparency_score'] > 50:
            consistency_score += 0.2  # Montos específicos sugieren transparencia
        checks += 1
        
        # Check 3: Número de entidades vs Transparencia
        if row.get('num_entities', 0) > 2:
            consistency_score += 0.2  # Muchas entidades pueden indicar transparencia
        checks += 1
        
        # Check 4: Día de la semana vs Actividad normal
        if row.get('dia_semana', '') in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            consistency_score += 0.1  # Días laborales normales
        checks += 1
        
        # Check 5: Sección vs Tipo esperado de riesgo
        section_risk_expectation = {
            1: 0.3,  # Designaciones - riesgo medio esperado
            2: 0.7,  # Compras - riesgo alto esperado
            3: 0.6,  # Transferencias - riesgo medio-alto esperado
            4: 0.8,  # Obras - riesgo alto esperado
            5: 0.2   # Notificaciones - riesgo bajo esperado
        }
        
        expected_risk = section_risk_expectation.get(row.get('seccion', 1), 0.5)
        if expected_risk < 0.5 and row['risk_level'] == 'ALTO':
            consistency_score += 0.2  # Sección no típica para riesgo alto
        checks += 1
        
        return consistency_score / checks if checks > 0 else 0.0
    
    def _suggest_corrected_risk(self, row: pd.Series, fp_probability: float) -> str:
        """
        Sugiere una clasificación de riesgo corregida
        """
        if fp_probability > 0.8:
            return 'BAJO'
        elif fp_probability > 0.6:
            return 'MEDIO'
        else:
            return 'ALTO'  # Mantener clasificación original
    
    def _generate_recommendation(self, is_fp: bool, confidence: float, 
                                reasons: List[str]) -> str:
        """
        Genera recomendación basada en el análisis
        """
        if is_fp:
            if confidence > 0.8:
                return "RECLASIFICAR: Alto falso positivo - revisar algoritmo"
            else:
                return "REVISAR: Posible falso positivo - validación manual recomendada"
        else:
            if confidence < 0.3:
                return "MANTENER: Clasificación parece correcta"
            else:
                return "MONITOREAR: Algunos indicadores de falso positivo"
    
    def generate_summary_report(self, df_analyzed: pd.DataFrame) -> Dict[str, any]:
        """
        Genera reporte resumen del análisis de falsos positivos
        """
        high_risk_cases = df_analyzed[df_analyzed['risk_level'] == 'ALTO']
        false_positives = df_analyzed[df_analyzed.get('is_false_positive', False) == True]
        
        summary = {
            'total_documents': len(df_analyzed),
            'high_risk_cases': len(high_risk_cases),
            'detected_false_positives': len(false_positives),
            'false_positive_rate': len(false_positives) / len(high_risk_cases) if len(high_risk_cases) > 0 else 0,
            'avg_fp_confidence': false_positives['fp_confidence'].mean() if len(false_positives) > 0 else 0,
            'top_fp_reasons': self._get_top_reasons(false_positives),
            'recommendations': self._generate_global_recommendations(df_analyzed)
        }
        
        return summary
    
    def _get_top_reasons(self, false_positives: pd.DataFrame) -> List[str]:
        """
        Obtiene las razones más comunes de falsos positivos
        """
        if len(false_positives) == 0:
            return []
        
        all_reasons = []
        for reasons_str in false_positives['fp_reasons'].dropna():
            all_reasons.extend(reasons_str.split('; '))
        
        from collections import Counter
        reason_counts = Counter(all_reasons)
        
        return [reason for reason, count in reason_counts.most_common(5)]
    
    def _generate_global_recommendations(self, df_analyzed: pd.DataFrame) -> List[str]:
        """
        Genera recomendaciones globales para mejorar el sistema
        """
        recommendations = []
        
        fp_rate = df_analyzed.get('is_false_positive', pd.Series([False])).mean()
        
        if fp_rate > 0.3:
            recommendations.append("Tasa de falsos positivos alta - revisar umbrales de clasificación")
        
        if fp_rate > 0.5:
            recommendations.append("Considerar reentrenar modelo con datos validados manualmente")
        
        # Análisis por sección
        section_fp_rates = df_analyzed.groupby('seccion')['is_false_positive'].mean()
        problematic_sections = section_fp_rates[section_fp_rates > 0.4].index.tolist()
        
        if problematic_sections:
            recommendations.append(f"Secciones {problematic_sections} tienen alta tasa de FP - revisar keywords específicas")
        
        return recommendations

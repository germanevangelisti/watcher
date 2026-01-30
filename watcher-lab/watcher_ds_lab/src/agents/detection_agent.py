"""
🤖 WATCHER DETECTION AGENT
Sistema agentic autónomo para detección de red flags en transparencia gubernamental
Implementación del agente inteligente basado en los resultados del análisis
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import pickle
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import sys

# Imports locales
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import AGENT_CONFIG, VALIDATION_CONFIG, ML_CONFIG
from extractors.entity_extractor import WatcherEntityExtractor
from analyzers.false_positive_detector import FalsePositiveDetector

logger = logging.getLogger(__name__)

@dataclass
class RedFlag:
    """Estructura para una red flag detectada"""
    id: str
    timestamp: datetime
    document_id: str
    flag_type: str
    severity: str  # CRITICO, ALTO, MEDIO, INFORMATIVO
    confidence: float
    description: str
    evidence: List[str]
    recommendation: str
    transparency_score: float
    risk_factors: Dict[str, any]
    metadata: Dict[str, any]

@dataclass
class AgentStatus:
    """Estado del agente de detección"""
    is_active: bool
    last_analysis: datetime
    documents_processed: int
    red_flags_detected: int
    false_positive_rate: float
    average_confidence: float
    system_health: str
    performance_metrics: Dict[str, float]

class WatcherDetectionAgent:
    """
    Agente autónomo para detección continua de irregularidades
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializa el agente de detección
        """
        self.config = config or AGENT_CONFIG
        self.extractor = WatcherEntityExtractor()
        self.fp_detector = FalsePositiveDetector()
        
        # Estado del agente
        self.status = AgentStatus(
            is_active=False,
            last_analysis=datetime.now(),
            documents_processed=0,
            red_flags_detected=0,
            false_positive_rate=0.0,
            average_confidence=0.0,
            system_health="INITIALIZING",
            performance_metrics={}
        )
        
        # Almacenamiento de red flags
        self.detected_flags: List[RedFlag] = []
        self.models = {}
        
        # Umbrales de alerta
        self.thresholds = self.config['alert_thresholds']
        
        logger.info("WatcherDetectionAgent inicializado")
    
    def load_trained_models(self, models_dir: Path) -> bool:
        """
        Carga los modelos ML entrenados
        """
        try:
            model_files = list(models_dir.glob("*.pkl"))
            
            for model_file in model_files:
                if 'risk_classifier' in model_file.name:
                    with open(model_file, 'rb') as f:
                        self.models['risk_classifier'] = pickle.load(f)
                elif 'anomaly_detector' in model_file.name:
                    with open(model_file, 'rb') as f:
                        self.models['anomaly_detector'] = pickle.load(f)
                elif 'clustering' in model_file.name:
                    with open(model_file, 'rb') as f:
                        self.models['clustering'] = pickle.load(f)
            
            logger.info(f"Modelos cargados: {list(self.models.keys())}")
            return len(self.models) > 0
            
        except Exception as e:
            logger.error(f"Error cargando modelos: {e}")
            return False
    
    def analyze_document(self, document_data: Dict) -> List[RedFlag]:
        """
        Analiza un documento individual y detecta red flags
        """
        flags = []
        doc_id = document_data.get('filename', 'unknown')
        
        try:
            # Análisis básico de transparencia
            transparency_score = document_data.get('transparency_score', 0)
            risk_level = document_data.get('risk_level', 'MEDIO')
            
            # Red flag por transparencia crítica
            if transparency_score < self.thresholds['critical_transparency']:
                flag = self._create_transparency_flag(document_data, transparency_score)
                flags.append(flag)
            
            # Red flag por monto alto
            num_amounts = document_data.get('num_amounts', 0)
            if num_amounts > 0 and transparency_score < 50:
                flag = self._create_amount_flag(document_data)
                flags.append(flag)
            
            # Red flag por anomalía detectada
            if 'is_anomaly' in document_data and document_data['is_anomaly']:
                flag = self._create_anomaly_flag(document_data)
                flags.append(flag)
            
            # Red flag por inconsistencia (falso positivo potencial)
            fp_analysis = self.fp_detector.analyze_single_case(pd.Series(document_data))
            if fp_analysis.is_false_positive:
                flag = self._create_inconsistency_flag(document_data, fp_analysis)
                flags.append(flag)
            
            # Red flag por patrones sospechosos
            pattern_flags = self._detect_suspicious_patterns(document_data)
            flags.extend(pattern_flags)
            
        except Exception as e:
            logger.error(f"Error analizando documento {doc_id}: {e}")
        
        return flags
    
    def _create_transparency_flag(self, doc_data: Dict, score: float) -> RedFlag:
        """
        Crea red flag por transparencia crítica
        """
        severity = "CRITICO" if score < 20 else "ALTO"
        
        return RedFlag(
            id=f"TRANSP_{doc_data['filename']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            document_id=doc_data['filename'],
            flag_type="TRANSPARENCIA_CRITICA",
            severity=severity,
            confidence=0.9 if score < 20 else 0.7,
            description=f"Score de transparencia crítico: {score:.1f}/100",
            evidence=[
                f"Score transparencia: {score:.1f}",
                f"Riesgo clasificado: {doc_data.get('risk_level', 'N/A')}",
                f"Keywords de riesgo: {doc_data.get('num_keywords_riesgo', 0)}"
            ],
            recommendation="Auditoría manual inmediata requerida",
            transparency_score=score,
            risk_factors={
                "transparency_score": score,
                "risk_level": doc_data.get('risk_level'),
                "section": doc_data.get('seccion')
            },
            metadata={"analysis_version": "2.0", "detector": "transparency_monitor"}
        )
    
    def _create_amount_flag(self, doc_data: Dict) -> RedFlag:
        """
        Crea red flag por montos sospechosos
        """
        return RedFlag(
            id=f"AMOUNT_{doc_data['filename']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            document_id=doc_data['filename'],
            flag_type="MONTO_SOSPECHOSO",
            severity="ALTO",
            confidence=0.8,
            description=f"Documento con montos ({doc_data.get('num_amounts', 0)}) y baja transparencia",
            evidence=[
                f"Número de montos: {doc_data.get('num_amounts', 0)}",
                f"Transparencia: {doc_data.get('transparency_score', 0):.1f}/100",
                f"Tipo de acto: {doc_data.get('act_type', 'N/A')}"
            ],
            recommendation="Verificar justificación de montos y proceso de adjudicación",
            transparency_score=doc_data.get('transparency_score', 0),
            risk_factors={
                "num_amounts": doc_data.get('num_amounts', 0),
                "act_type": doc_data.get('act_type')
            },
            metadata={"detector": "amount_monitor"}
        )
    
    def _create_anomaly_flag(self, doc_data: Dict) -> RedFlag:
        """
        Crea red flag por anomalía detectada por ML
        """
        return RedFlag(
            id=f"ANOM_{doc_data['filename']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            document_id=doc_data['filename'],
            flag_type="ANOMALIA_ML",
            severity="MEDIO",
            confidence=0.75,
            description="Documento marcado como anómalo por algoritmo ML",
            evidence=[
                "Detectado por Isolation Forest",
                f"Score transparencia: {doc_data.get('transparency_score', 0):.1f}",
                f"Sección: {doc_data.get('seccion', 'N/A')}"
            ],
            recommendation="Revisión de patrones inusuales en el documento",
            transparency_score=doc_data.get('transparency_score', 0),
            risk_factors={"is_anomaly": True},
            metadata={"detector": "ml_anomaly"}
        )
    
    def _create_inconsistency_flag(self, doc_data: Dict, fp_analysis) -> RedFlag:
        """
        Crea red flag por inconsistencia (falso positivo)
        """
        return RedFlag(
            id=f"INCONS_{doc_data['filename']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            document_id=doc_data['filename'],
            flag_type="INCONSISTENCIA_CLASIFICACION",
            severity="INFORMATIVO",
            confidence=fp_analysis.confidence,
            description="Posible inconsistencia en clasificación de riesgo",
            evidence=fp_analysis.reasons,
            recommendation=fp_analysis.recommendation,
            transparency_score=doc_data.get('transparency_score', 0),
            risk_factors={"fp_confidence": fp_analysis.confidence},
            metadata={"detector": "false_positive_monitor"}
        )
    
    def _detect_suspicious_patterns(self, doc_data: Dict) -> List[RedFlag]:
        """
        Detecta patrones sospechosos específicos
        """
        flags = []
        
        # Patrón: Sección 5 (Notificaciones) con riesgo alto
        if doc_data.get('seccion') == 5 and doc_data.get('risk_level') == 'ALTO':
            flag = RedFlag(
                id=f"PATT_{doc_data['filename']}_SECC5",
                timestamp=datetime.now(),
                document_id=doc_data['filename'],
                flag_type="PATRON_SECCION_INUSUAL",
                severity="MEDIO",
                confidence=0.6,
                description="Sección 5 (Notificaciones) con clasificación de riesgo alto inusual",
                evidence=[
                    "Sección 5 típicamente es bajo riesgo",
                    f"Clasificado como: {doc_data.get('risk_level')}"
                ],
                recommendation="Verificar si la clasificación es correcta",
                transparency_score=doc_data.get('transparency_score', 0),
                risk_factors={"unusual_section_risk": True},
                metadata={"detector": "pattern_monitor"}
            )
            flags.append(flag)
        
        # Patrón: Muchas entidades con baja transparencia
        if doc_data.get('num_entities', 0) > 10 and doc_data.get('transparency_score', 0) < 30:
            flag = RedFlag(
                id=f"PATT_{doc_data['filename']}_ENTITIES",
                timestamp=datetime.now(),
                document_id=doc_data['filename'],
                flag_type="PATRON_ENTIDADES_OPACO",
                severity="ALTO",
                confidence=0.8,
                description="Múltiples entidades con transparencia muy baja",
                evidence=[
                    f"Entidades detectadas: {doc_data.get('num_entities')}",
                    f"Score transparencia: {doc_data.get('transparency_score'):.1f}"
                ],
                recommendation="Auditar relaciones entre entidades mencionadas",
                transparency_score=doc_data.get('transparency_score', 0),
                risk_factors={"multi_entity_opacity": True},
                metadata={"detector": "entity_pattern_monitor"}
            )
            flags.append(flag)
        
        return flags
    
    def analyze_dataset(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Analiza dataset completo y genera reporte de red flags
        """
        logger.info(f"Agente analizando {len(df)} documentos")
        
        all_flags = []
        self.status.documents_processed = 0
        
        for _, row in df.iterrows():
            document_flags = self.analyze_document(row.to_dict())
            all_flags.extend(document_flags)
            self.status.documents_processed += 1
        
        # Actualizar estado del agente
        self.detected_flags = all_flags
        self.status.red_flags_detected = len(all_flags)
        self.status.last_analysis = datetime.now()
        self.status.average_confidence = np.mean([f.confidence for f in all_flags]) if all_flags else 0
        self.status.system_health = "OPERATIONAL"
        
        # Generar reporte
        report = self._generate_detection_report(all_flags)
        
        logger.info(f"Análisis completado: {len(all_flags)} red flags detectadas")
        
        return report
    
    def _generate_detection_report(self, flags: List[RedFlag]) -> Dict[str, any]:
        """
        Genera reporte completo de detección
        """
        # Estadísticas por severidad
        severity_stats = {}
        for severity in ["CRITICO", "ALTO", "MEDIO", "INFORMATIVO"]:
            severity_flags = [f for f in flags if f.severity == severity]
            severity_stats[severity] = {
                "count": len(severity_flags),
                "avg_confidence": np.mean([f.confidence for f in severity_flags]) if severity_flags else 0,
                "documents": [f.document_id for f in severity_flags]
            }
        
        # Estadísticas por tipo
        type_stats = {}
        for flag in flags:
            if flag.flag_type not in type_stats:
                type_stats[flag.flag_type] = 0
            type_stats[flag.flag_type] += 1
        
        # Top documentos más problemáticos
        doc_flag_counts = {}
        for flag in flags:
            if flag.document_id not in doc_flag_counts:
                doc_flag_counts[flag.document_id] = []
            doc_flag_counts[flag.document_id].append(flag)
        
        top_problematic = sorted(
            doc_flag_counts.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:5]
        
        # Recomendaciones prioritarias
        critical_flags = [f for f in flags if f.severity == "CRITICO"]
        high_flags = [f for f in flags if f.severity == "ALTO"]
        
        priority_actions = []
        if critical_flags:
            priority_actions.append({
                "priority": 1,
                "action": "AUDITORIA INMEDIATA",
                "documents": [f.document_id for f in critical_flags],
                "reason": "Red flags críticas detectadas"
            })
        
        if high_flags:
            priority_actions.append({
                "priority": 2,
                "action": "REVISION_URGENTE", 
                "documents": [f.document_id for f in high_flags[:3]],
                "reason": "Múltiples red flags de alta severidad"
            })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "agent_status": asdict(self.status),
            "summary": {
                "total_flags": len(flags),
                "documents_analyzed": self.status.documents_processed,
                "flag_rate": len(flags) / self.status.documents_processed if self.status.documents_processed > 0 else 0,
                "avg_confidence": self.status.average_confidence
            },
            "severity_breakdown": severity_stats,
            "flag_types": type_stats,
            "top_problematic_documents": [
                {
                    "document": doc,
                    "flag_count": len(flags_list),
                    "severities": [f.severity for f in flags_list]
                }
                for doc, flags_list in top_problematic
            ],
            "priority_actions": priority_actions,
            "detailed_flags": [asdict(flag) for flag in flags],
            "recommendations": self._generate_system_recommendations(flags)
        }
    
    def _generate_system_recommendations(self, flags: List[RedFlag]) -> List[Dict]:
        """
        Genera recomendaciones para mejorar el sistema
        """
        recommendations = []
        
        # Análisis de transparencia
        transparency_flags = [f for f in flags if f.flag_type == "TRANSPARENCIA_CRITICA"]
        if len(transparency_flags) > 5:
            recommendations.append({
                "type": "SYSTEM_TUNING",
                "priority": "HIGH",
                "issue": f"Muchos casos de transparencia crítica ({len(transparency_flags)})",
                "action": "Revisar algoritmo de scoring de transparencia",
                "expected_impact": "Reducir alertas falsas de transparencia"
            })
        
        # Análisis de patrones
        pattern_flags = [f for f in flags if "PATRON" in f.flag_type]
        if pattern_flags:
            recommendations.append({
                "type": "PATTERN_ANALYSIS",
                "priority": "MEDIUM",
                "issue": f"Patrones sospechosos detectados ({len(pattern_flags)})",
                "action": "Análisis profundo de patrones específicos",
                "expected_impact": "Mejorar detección de irregularidades sistemáticas"
            })
        
        return recommendations
    
    def export_alerts(self, output_dir: Path) -> Dict[str, str]:
        """
        Exporta alertas en múltiples formatos
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Reporte JSON completo
        report = self._generate_detection_report(self.detected_flags)
        json_file = output_dir / f"watcher_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        # CSV de red flags para análisis
        if self.detected_flags:
            flags_data = []
            for flag in self.detected_flags:
                flags_data.append({
                    'timestamp': flag.timestamp,
                    'document_id': flag.document_id,
                    'flag_type': flag.flag_type,
                    'severity': flag.severity,
                    'confidence': flag.confidence,
                    'description': flag.description,
                    'transparency_score': flag.transparency_score,
                    'recommendation': flag.recommendation
                })
            
            csv_file = output_dir / f"red_flags_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            pd.DataFrame(flags_data).to_csv(csv_file, index=False)
        
        # Reporte ejecutivo en texto
        executive_summary = self._generate_executive_summary(report)
        txt_file = output_dir / f"executive_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(executive_summary)
        
        return {
            "json_report": str(json_file),
            "csv_flags": str(csv_file) if self.detected_flags else None,
            "executive_summary": str(txt_file)
        }
    
    def _generate_executive_summary(self, report: Dict) -> str:
        """
        Genera resumen ejecutivo en texto
        """
        summary = f"""
🤖 REPORTE EJECUTIVO - WATCHER DETECTION AGENT
=============================================

📊 RESUMEN DE ANÁLISIS:
• Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Documentos analizados: {report['summary']['documents_analyzed']}
• Red flags detectadas: {report['summary']['total_flags']}
• Tasa de detección: {report['summary']['flag_rate']:.1%}
• Confianza promedio: {report['summary']['avg_confidence']:.1%}

🚨 ALERTAS POR SEVERIDAD:
"""
        
        for severity, data in report['severity_breakdown'].items():
            if data['count'] > 0:
                summary += f"• {severity}: {data['count']} casos (confianza: {data['avg_confidence']:.1%})\n"
        
        summary += f"\n🎯 DOCUMENTOS MÁS PROBLEMÁTICOS:\n"
        for doc_info in report['top_problematic_documents'][:3]:
            summary += f"• {doc_info['document']}: {doc_info['flag_count']} red flags\n"
        
        summary += f"\n⚡ ACCIONES PRIORITARIAS:\n"
        for action in report['priority_actions']:
            summary += f"{action['priority']}. {action['action']}: {action['reason']}\n"
        
        summary += f"\n💡 RECOMENDACIONES DEL SISTEMA:\n"
        for i, rec in enumerate(report['recommendations'], 1):
            summary += f"{i}. [{rec['priority']}] {rec['issue']}\n"
            summary += f"   Acción: {rec['action']}\n"
        
        summary += f"\n🔍 Estado del Agente: {report['agent_status']['system_health']}"
        summary += f"\n📈 Rendimiento: {report['agent_status']['documents_processed']} docs procesados"
        
        return summary

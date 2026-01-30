"""
Anomaly Detection Agent

Identifica patrones sospechosos y red flags usando ML + reglas heurísticas
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.core.agent_config import AnomalyDetectionConfig
from agents.orchestrator.state import WorkflowState, TaskDefinition, AgentType

logger = logging.getLogger(__name__)


class AnomalyDetectionAgent:
    """
    Agente especializado en detección de anomalías
    
    Capacidades:
    - Detección de anomalías estadísticas
    - Scoring de transparencia
    - Clasificación de riesgo
    - Generación de explicaciones
    """
    
    def __init__(self, config: Optional[AnomalyDetectionConfig] = None):
        """
        Inicializa el agente
        
        Args:
            config: Configuración del agente
        """
        self.config = config or AnomalyDetectionConfig()
        self.agent_type = AgentType.ANOMALY_DETECTION
        
        # Modelos ML (placeholder - cargar modelos entrenados)
        self.models = {}
        
        logger.info("AnomalyDetectionAgent inicializado")
    
    async def execute(self, workflow: WorkflowState, 
                     task: TaskDefinition) -> Dict[str, Any]:
        """
        Ejecuta una tarea del agente
        
        Args:
            workflow: Estado del workflow
            task: Tarea a ejecutar
        
        Returns:
            Resultado de la ejecución
        """
        task_type = task.task_type
        parameters = task.parameters
        
        logger.info(f"Ejecutando tarea: {task_type}")
        
        if task_type == "analyze_document":
            return await self.analyze_document(
                parameters.get("text"),
                parameters.get("entities"),
                parameters.get("document_id")
            )
        elif task_type == "calculate_transparency_score":
            return await self.calculate_transparency_score(
                parameters.get("text"),
                parameters.get("entities")
            )
        elif task_type == "detect_red_flags":
            return await self.detect_red_flags(
                parameters.get("text"),
                parameters.get("entities"),
                parameters.get("transparency_score")
            )
        elif task_type == "analyze_high_risk":
            return await self.analyze_high_risk_documents(
                parameters.get("threshold", 50),
                parameters.get("limit", 20)
            )
        else:
            raise ValueError(f"Tipo de tarea no soportado: {task_type}")
    
    async def analyze_document(self, text: str, entities: Dict[str, Any],
                              document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Análisis completo de un documento
        
        Args:
            text: Texto del documento
            entities: Entidades extraídas
            document_id: ID del documento
        
        Returns:
            Análisis completo con red flags y scores
        """
        try:
            # Calcular score de transparencia
            transparency_score = self._calculate_transparency_score(text, entities)
            
            # Calcular score de anomalía
            anomaly_score = self._calculate_anomaly_score(entities, text)
            
            # Determinar nivel de riesgo
            risk_level = self._determine_risk_level(transparency_score, anomaly_score)
            
            # Detectar red flags
            red_flags = self._detect_red_flags(text, entities, transparency_score)
            
            # Predicciones ML
            ml_predictions = self._run_ml_predictions(entities, transparency_score)
            
            result = {
                "success": True,
                "document_id": document_id,
                "transparency_score": round(transparency_score, 2),
                "anomaly_score": round(anomaly_score, 2),
                "risk_level": risk_level,
                "red_flags": red_flags,
                "num_red_flags": len(red_flags),
                "ml_predictions": ml_predictions,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Documento analizado: risk={risk_level}, "
                       f"transparency={transparency_score:.1f}, "
                       f"red_flags={len(red_flags)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analizando documento: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def calculate_transparency_score(self, text: str,
                                          entities: Dict[str, Any]) -> float:
        """
        Calcula el score de transparencia
        
        Args:
            text: Texto del documento
            entities: Entidades extraídas
        
        Returns:
            Score de transparencia (0-100)
        """
        return self._calculate_transparency_score(text, entities)
    
    async def detect_red_flags(self, text: str, entities: Dict[str, Any],
                              transparency_score: float) -> List[Dict[str, Any]]:
        """
        Detecta red flags en el documento
        
        Args:
            text: Texto del documento
            entities: Entidades extraídas
            transparency_score: Score de transparencia
        
        Returns:
            Lista de red flags detectadas
        """
        return self._detect_red_flags(text, entities, transparency_score)
    
    def _calculate_transparency_score(self, text: str, 
                                     entities: Dict[str, Any]) -> float:
        """Calcula score de transparencia (0-100)"""
        score = 50.0  # Base
        
        # Puntos por tener montos identificados
        if entities.get('amounts'):
            score += 10
            if len(entities['amounts']) >= 5:
                score += 5
        
        # Puntos por identificar beneficiarios
        if entities.get('beneficiaries'):
            score += 15
            if len(entities['beneficiaries']) >= 3:
                score += 5
        
        # Puntos por identificar organismos
        if entities.get('organisms'):
            score += 10
        
        # Penalización por texto muy corto
        if len(text) < 1000:
            score -= 15
        
        # Penalización por falta de estructura
        if '\n' not in text or len(text.split('\n')) < 10:
            score -= 10
        
        # Bonus por fechas claras
        if entities.get('dates') and len(entities['dates']) >= 2:
            score += 5
        
        # Asegurar rango 0-100
        return max(0.0, min(100.0, score))
    
    def _calculate_anomaly_score(self, entities: Dict[str, Any], 
                                 text: str) -> float:
        """Calcula score de anomalía (0-100)"""
        anomaly = 0.0
        
        # Montos sospechosos
        amounts = entities.get('amounts', [])
        for amount in amounts:
            value = amount['numeric_value']
            
            # Patrones sospechosos
            if '999' in str(int(value)):
                anomaly += 15
            
            # Montos muy altos
            threshold = self.config.amount_thresholds.get('very_high', 50000000)
            if value > threshold:
                anomaly += 10
        
        # Falta de beneficiarios con montos altos
        if amounts and not entities.get('beneficiaries'):
            anomaly += 20
        
        # Texto muy repetitivo
        words = text.lower().split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:
                anomaly += 15
        
        return min(100.0, anomaly)
    
    def _determine_risk_level(self, transparency_score: float, 
                             anomaly_score: float) -> str:
        """Determina nivel de riesgo"""
        thresholds = self.config.transparency_thresholds
        
        # Basado en transparency score
        if transparency_score < thresholds.get('high_risk', 30):
            return 'high'
        elif transparency_score < thresholds.get('medium_risk', 50):
            return 'medium'
        elif anomaly_score > 60:
            return 'medium'
        else:
            return 'low'
    
    def _detect_red_flags(self, text: str, entities: Dict[str, Any],
                         transparency_score: float) -> List[Dict[str, Any]]:
        """Detecta red flags basadas en reglas"""
        red_flags = []
        
        # RED FLAG: HIGH_AMOUNT
        rule = self.config.red_flag_rules.get('HIGH_AMOUNT', {})
        if rule.get('enabled', True):
            threshold = rule.get('threshold', 50000000)
            for amount in entities.get('amounts', []):
                if amount['numeric_value'] > threshold:
                    red_flags.append({
                        "type": "HIGH_AMOUNT",
                        "severity": "high",
                        "category": "amounts",
                        "title": f"Monto muy alto detectado: ${amount['numeric_value']:,.0f}",
                        "description": f"Se detectó un monto de ${amount['numeric_value']:,.0f} que supera el threshold de ${threshold:,.0f}",
                        "evidence": {
                            "amount": amount['numeric_value'],
                            "raw_text": amount['raw_text'],
                            "threshold": threshold
                        },
                        "confidence_score": 0.9,
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        # RED FLAG: MISSING_BENEFICIARY
        rule = self.config.red_flag_rules.get('MISSING_BENEFICIARY', {})
        if rule.get('enabled', True):
            if entities.get('amounts') and not entities.get('beneficiaries'):
                red_flags.append({
                    "type": "MISSING_BENEFICIARY",
                    "severity": "medium",
                    "category": "transparency",
                    "title": "Falta identificación de beneficiario",
                    "description": "Se detectaron montos pero no se pudo identificar beneficiarios",
                    "evidence": {
                        "amounts_count": len(entities.get('amounts', [])),
                        "beneficiaries_found": 0
                    },
                    "confidence_score": 0.7,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # RED FLAG: SUSPICIOUS_AMOUNT_PATTERN
        rule = self.config.red_flag_rules.get('SUSPICIOUS_AMOUNT_PATTERN', {})
        if rule.get('enabled', True):
            patterns = rule.get('patterns', ['999999', '9999'])
            for amount in entities.get('amounts', []):
                amount_str = str(int(amount['numeric_value']))
                for pattern in patterns:
                    if pattern in amount_str:
                        red_flags.append({
                            "type": "SUSPICIOUS_AMOUNT_PATTERN",
                            "severity": "medium",
                            "category": "patterns",
                            "title": f"Patrón sospechoso en monto: {pattern}",
                            "description": f"El monto ${amount['numeric_value']:,.0f} contiene el patrón sospechoso '{pattern}'",
                            "evidence": {
                                "amount": amount['numeric_value'],
                                "pattern": pattern,
                                "raw_text": amount['raw_text']
                            },
                            "confidence_score": 0.8,
                            "timestamp": datetime.utcnow().isoformat()
                        })
        
        # RED FLAG: LOW_TRANSPARENCY_SCORE
        rule = self.config.red_flag_rules.get('LOW_TRANSPARENCY_SCORE', {})
        if rule.get('enabled', True):
            threshold = rule.get('threshold', 30)
            if transparency_score < threshold:
                red_flags.append({
                    "type": "LOW_TRANSPARENCY_SCORE",
                    "severity": "high",
                    "category": "transparency",
                    "title": f"Score de transparencia muy bajo: {transparency_score:.1f}",
                    "description": f"El documento tiene un score de transparencia de {transparency_score:.1f}, por debajo del threshold de {threshold}",
                    "evidence": {
                        "transparency_score": transparency_score,
                        "threshold": threshold,
                        "missing_elements": self._identify_missing_elements(entities)
                    },
                    "confidence_score": 0.95,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return red_flags
    
    def _identify_missing_elements(self, entities: Dict[str, Any]) -> List[str]:
        """Identifica elementos faltantes para transparencia"""
        missing = []
        
        if not entities.get('amounts'):
            missing.append("montos")
        if not entities.get('beneficiaries'):
            missing.append("beneficiarios")
        if not entities.get('organisms'):
            missing.append("organismos")
        if not entities.get('dates'):
            missing.append("fechas")
        
        return missing
    
    def _run_ml_predictions(self, entities: Dict[str, Any],
                           transparency_score: float) -> Dict[str, Any]:
        """Ejecutar predicciones ML (placeholder)"""
        return {
            "random_forest": {
                "risk_probability": 0.3 if transparency_score > 50 else 0.7,
                "confidence": 0.75
            },
            "isolation_forest": {
                "is_anomaly": transparency_score < 40,
                "anomaly_score": -0.5
            },
            "kmeans": {
                "cluster": 1 if transparency_score > 50 else 2,
                "distance_to_centroid": 1.5
            }
        }
    
    async def analyze_high_risk_documents(self, threshold: int = 50, 
                                         limit: int = 20) -> Dict[str, Any]:
        """
        Analiza documentos con alto riesgo (bajo score de transparencia)
        
        Args:
            threshold: Score máximo de transparencia para considerar alto riesgo
            limit: Número máximo de documentos a analizar
        
        Returns:
            Análisis de documentos de alto riesgo
        """
        try:
            from agents.tools.database_tools import DatabaseTools
            from agents.tools.analysis_tools import AnalysisTools
            
            db = DatabaseTools.get_db()
            try:
                # Obtener documentos de alto riesgo
                high_risk_docs = AnalysisTools.get_top_risk_documents(db, limit=limit)
                
                # Filtrar por threshold
                filtered_docs = [
                    doc for doc in high_risk_docs 
                    if doc.get('transparency_score', 100) < threshold
                ]
                
                # Estadísticas
                stats = {
                    "total_analyzed": len(filtered_docs),
                    "threshold_used": threshold,
                    "average_score": sum(d.get('transparency_score', 0) for d in filtered_docs) / len(filtered_docs) if filtered_docs else 0,
                    "total_red_flags": sum(d.get('red_flags_count', 0) for d in filtered_docs)
                }
                
                logger.info(f"Análisis de alto riesgo completado: {len(filtered_docs)} documentos")
                
                return {
                    "success": True,
                    "task_type": "analyze_high_risk",
                    "statistics": stats,
                    "high_risk_documents": filtered_docs[:10],  # Top 10
                    "recommendations": [
                        f"Se encontraron {len(filtered_docs)} documentos con score < {threshold}",
                        "Revisar documentos priorizados por severidad de red flags",
                        "Considerar auditoría manual de casos críticos"
                    ],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error en análisis de alto riesgo: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }




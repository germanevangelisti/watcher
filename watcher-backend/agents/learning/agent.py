"""
Learning & Feedback Agent

Aprende del feedback humano y mejora el sistema continuamente
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

from agents.orchestrator.state import AgentType

logger = logging.getLogger(__name__)


class FeedbackRecord:
    """Registro de feedback humano"""
    
    def __init__(self, 
                 feedback_type: str,
                 entity_type: str,
                 entity_id: str,
                 feedback_value: Any,
                 user_notes: Optional[str] = None,
                 metadata: Optional[Dict] = None):
        self.feedback_type = feedback_type  # 'validation', 'correction', 'rating'
        self.entity_type = entity_type  # 'red_flag', 'classification', 'entity'
        self.entity_id = entity_id
        self.feedback_value = feedback_value
        self.user_notes = user_notes
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()


class LearningAgent:
    """
    Agente de aprendizaje continuo
    
    Capacidades:
    - Registrar feedback humano
    - Ajustar thresholds automáticamente
    - Detectar concept drift
    - Sugerir mejoras al sistema
    """
    
    def __init__(self):
        self.agent_type = AgentType.LEARNING_FEEDBACK
        
        # Almacenamiento de feedback
        self.feedback_history: List[FeedbackRecord] = []
        
        # Métricas de performance
        self.performance_metrics = {
            'red_flags': {
                'true_positives': 0,
                'false_positives': 0,
                'false_negatives': 0,
                'precision': 0.0,
                'recall': 0.0
            },
            'classifications': {
                'correct': 0,
                'incorrect': 0,
                'accuracy': 0.0
            }
        }
        
        # Ajustes sugeridos
        self.suggested_adjustments: List[Dict] = []
        
        logger.info("LearningAgent inicializado")
    
    def record_feedback(self, 
                       feedback_type: str,
                       entity_type: str,
                       entity_id: str,
                       feedback_value: Any,
                       user_notes: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Registra feedback del usuario
        
        Args:
            feedback_type: Tipo de feedback
            entity_type: Tipo de entidad
            entity_id: ID de la entidad
            feedback_value: Valor del feedback
            user_notes: Notas adicionales del usuario
            metadata: Metadata adicional
        
        Returns:
            Resultado del registro
        """
        record = FeedbackRecord(
            feedback_type=feedback_type,
            entity_type=entity_type,
            entity_id=entity_id,
            feedback_value=feedback_value,
            user_notes=user_notes,
            metadata=metadata
        )
        
        self.feedback_history.append(record)
        
        # Actualizar métricas
        self._update_metrics(record)
        
        # Analizar si hay ajustes necesarios
        self._analyze_for_adjustments()
        
        logger.info(f"Feedback registrado: {feedback_type} para {entity_type} {entity_id}")
        
        return {
            "success": True,
            "feedback_id": id(record),
            "timestamp": record.timestamp.isoformat(),
            "current_metrics": self.get_performance_metrics()
        }
    
    def validate_red_flag(self, 
                         red_flag_id: str,
                         is_valid: bool,
                         user_notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Valida una red flag
        
        Args:
            red_flag_id: ID de la red flag
            is_valid: Si la red flag es un verdadero positivo
            user_notes: Notas del usuario
        
        Returns:
            Resultado de la validación
        """
        return self.record_feedback(
            feedback_type='validation',
            entity_type='red_flag',
            entity_id=red_flag_id,
            feedback_value={'is_valid': is_valid},
            user_notes=user_notes
        )
    
    def rate_classification(self,
                           document_id: str,
                           predicted_class: str,
                           actual_class: str,
                           user_notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Registra corrección de clasificación
        
        Args:
            document_id: ID del documento
            predicted_class: Clase predicha
            actual_class: Clase correcta
            user_notes: Notas del usuario
        
        Returns:
            Resultado del registro
        """
        return self.record_feedback(
            feedback_type='correction',
            entity_type='classification',
            entity_id=document_id,
            feedback_value={
                'predicted': predicted_class,
                'actual': actual_class
            },
            user_notes=user_notes
        )
    
    def _update_metrics(self, record: FeedbackRecord) -> None:
        """Actualiza métricas de performance"""
        if record.entity_type == 'red_flag' and record.feedback_type == 'validation':
            is_valid = record.feedback_value.get('is_valid', False)
            
            if is_valid:
                self.performance_metrics['red_flags']['true_positives'] += 1
            else:
                self.performance_metrics['red_flags']['false_positives'] += 1
            
            # Recalcular precision
            tp = self.performance_metrics['red_flags']['true_positives']
            fp = self.performance_metrics['red_flags']['false_positives']
            
            if tp + fp > 0:
                precision = tp / (tp + fp)
                self.performance_metrics['red_flags']['precision'] = precision
        
        elif record.entity_type == 'classification' and record.feedback_type == 'correction':
            predicted = record.feedback_value.get('predicted')
            actual = record.feedback_value.get('actual')
            
            if predicted == actual:
                self.performance_metrics['classifications']['correct'] += 1
            else:
                self.performance_metrics['classifications']['incorrect'] += 1
            
            # Recalcular accuracy
            correct = self.performance_metrics['classifications']['correct']
            incorrect = self.performance_metrics['classifications']['incorrect']
            
            if correct + incorrect > 0:
                accuracy = correct / (correct + incorrect)
                self.performance_metrics['classifications']['accuracy'] = accuracy
    
    def _analyze_for_adjustments(self) -> None:
        """Analiza feedback para sugerir ajustes"""
        # Verificar si hay suficiente feedback
        if len(self.feedback_history) < 10:
            return
        
        # Analizar últimos 20 feedbacks de red flags
        recent_red_flag_feedback = [
            f for f in self.feedback_history[-20:]
            if f.entity_type == 'red_flag'
        ]
        
        if len(recent_red_flag_feedback) >= 5:
            valid_count = sum(
                1 for f in recent_red_flag_feedback
                if f.feedback_value.get('is_valid', False)
            )
            
            validation_rate = valid_count / len(recent_red_flag_feedback)
            
            # Si la tasa de validación es muy baja, sugerir ajuste
            if validation_rate < 0.5:
                self.suggested_adjustments.append({
                    "type": "threshold_adjustment",
                    "target": "red_flag_detection",
                    "reason": f"Alta tasa de falsos positivos: {(1-validation_rate)*100:.1f}%",
                    "suggestion": "Incrementar thresholds para reducir falsos positivos",
                    "priority": "high",
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de performance actuales"""
        return {
            "total_feedback_count": len(self.feedback_history),
            "metrics": self.performance_metrics,
            "suggested_adjustments_count": len(self.suggested_adjustments)
        }
    
    def get_suggested_adjustments(self) -> List[Dict]:
        """Obtiene ajustes sugeridos"""
        return self.suggested_adjustments
    
    def apply_adjustment(self, adjustment_id: int) -> Dict[str, Any]:
        """
        Marca un ajuste como aplicado
        
        Args:
            adjustment_id: Índice del ajuste en la lista
        
        Returns:
            Resultado de la aplicación
        """
        if 0 <= adjustment_id < len(self.suggested_adjustments):
            adjustment = self.suggested_adjustments[adjustment_id]
            adjustment['applied'] = True
            adjustment['applied_at'] = datetime.utcnow().isoformat()
            
            return {
                "success": True,
                "adjustment": adjustment
            }
        
        return {
            "success": False,
            "error": "Adjustment not found"
        }
    
    def get_feedback_history(self, 
                            entity_type: Optional[str] = None,
                            limit: int = 100) -> List[Dict]:
        """
        Obtiene historial de feedback
        
        Args:
            entity_type: Filtrar por tipo de entidad
            limit: Límite de registros
        
        Returns:
            Lista de feedbacks
        """
        history = self.feedback_history
        
        if entity_type:
            history = [f for f in history if f.entity_type == entity_type]
        
        # Tomar los más recientes
        recent = history[-limit:] if len(history) > limit else history
        
        return [
            {
                "feedback_type": f.feedback_type,
                "entity_type": f.entity_type,
                "entity_id": f.entity_id,
                "feedback_value": f.feedback_value,
                "user_notes": f.user_notes,
                "timestamp": f.timestamp.isoformat()
            }
            for f in recent
        ]
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """
        Genera insights sobre el aprendizaje del sistema
        
        Returns:
            Insights y estadísticas
        """
        insights = {
            "total_feedback_received": len(self.feedback_history),
            "feedback_by_type": defaultdict(int),
            "feedback_by_entity": defaultdict(int),
            "recent_trends": {},
            "improvement_suggestions": []
        }
        
        # Contar por tipo
        for record in self.feedback_history:
            insights["feedback_by_type"][record.feedback_type] += 1
            insights["feedback_by_entity"][record.entity_type] += 1
        
        # Tendencias recientes (últimos 20)
        if len(self.feedback_history) >= 20:
            recent = self.feedback_history[-20:]
            recent_valid_rf = sum(
                1 for f in recent
                if f.entity_type == 'red_flag' and f.feedback_value.get('is_valid', False)
            )
            recent_total_rf = sum(1 for f in recent if f.entity_type == 'red_flag')
            
            if recent_total_rf > 0:
                insights["recent_trends"]["red_flag_validation_rate"] = recent_valid_rf / recent_total_rf
        
        # Sugerencias de mejora
        if self.performance_metrics['red_flags']['precision'] < 0.7:
            insights["improvement_suggestions"].append(
                "Consider adjusting red flag thresholds to improve precision"
            )
        
        if self.performance_metrics['classifications']['accuracy'] < 0.8:
            insights["improvement_suggestions"].append(
                "Classification accuracy could be improved with model retraining"
            )
        
        return dict(insights)






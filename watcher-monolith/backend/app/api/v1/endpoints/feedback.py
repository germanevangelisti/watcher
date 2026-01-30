"""
API endpoints para sistema de feedback y learning
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from pydantic import BaseModel

from agents.learning import LearningAgent

router = APIRouter()

# Instancia global del learning agent
learning_agent = LearningAgent()


# Schemas
class ValidateRedFlagRequest(BaseModel):
    red_flag_id: str
    is_valid: bool
    user_notes: Optional[str] = None


class RateClassificationRequest(BaseModel):
    document_id: str
    predicted_class: str
    actual_class: str
    user_notes: Optional[str] = None


class GenericFeedbackRequest(BaseModel):
    feedback_type: str
    entity_type: str
    entity_id: str
    feedback_value: Dict[str, Any]
    user_notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Endpoints
@router.post("/red-flag/validate")
async def validate_red_flag(request: ValidateRedFlagRequest):
    """
    Valida una red flag como verdadero o falso positivo
    """
    try:
        result = learning_agent.validate_red_flag(
            red_flag_id=request.red_flag_id,
            is_valid=request.is_valid,
            user_notes=request.user_notes
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classification/rate")
async def rate_classification(request: RateClassificationRequest):
    """
    Registra corrección de clasificación
    """
    try:
        result = learning_agent.rate_classification(
            document_id=request.document_id,
            predicted_class=request.predicted_class,
            actual_class=request.actual_class,
            user_notes=request.user_notes
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def submit_feedback(request: GenericFeedbackRequest):
    """
    Envía feedback genérico
    """
    try:
        result = learning_agent.record_feedback(
            feedback_type=request.feedback_type,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            feedback_value=request.feedback_value,
            user_notes=request.user_notes,
            metadata=request.metadata
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_performance_metrics():
    """
    Obtiene métricas de performance del sistema
    """
    return learning_agent.get_performance_metrics()


@router.get("/adjustments")
async def get_suggested_adjustments():
    """
    Obtiene ajustes sugeridos basados en feedback
    """
    return {
        "adjustments": learning_agent.get_suggested_adjustments()
    }


@router.post("/adjustments/{adjustment_id}/apply")
async def apply_adjustment(adjustment_id: int):
    """
    Marca un ajuste como aplicado
    """
    result = learning_agent.apply_adjustment(adjustment_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Unknown error"))
    
    return result


@router.get("/history")
async def get_feedback_history(entity_type: Optional[str] = None, limit: int = 100):
    """
    Obtiene historial de feedback
    """
    return {
        "history": learning_agent.get_feedback_history(entity_type=entity_type, limit=limit)
    }


@router.get("/insights")
async def get_learning_insights():
    """
    Obtiene insights sobre el aprendizaje del sistema
    """
    return learning_agent.get_learning_insights()


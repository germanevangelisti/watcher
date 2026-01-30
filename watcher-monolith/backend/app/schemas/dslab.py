"""
Schemas Pydantic para el DS Lab - Análisis Persistente
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# =============================================================================
# DOCUMENTOS
# =============================================================================

class BoletinDocumentCreate(BaseModel):
    """Schema para crear un documento de boletín"""
    filename: str = Field(..., max_length=255)
    year: int
    month: int
    day: int
    section: int
    file_path: str
    file_size_bytes: Optional[int] = None
    num_pages: Optional[int] = None


class BoletinDocumentUpdate(BaseModel):
    """Schema para actualizar un documento"""
    analysis_status: Optional[str] = None
    last_analyzed: Optional[datetime] = None
    num_pages: Optional[int] = None


class BoletinDocumentResponse(BaseModel):
    """Schema de respuesta para documento"""
    id: int
    filename: str
    year: int
    month: int
    day: int
    section: int
    file_path: str
    file_size_bytes: Optional[int]
    download_date: datetime
    last_analyzed: Optional[datetime]
    analysis_status: str
    num_pages: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentStats(BaseModel):
    """Estadísticas de documentos"""
    total_documents: int
    by_status: Dict[str, int]
    by_month: Dict[str, int]
    total_size_mb: float
    avg_pages: Optional[float]


# =============================================================================
# CONFIGURACIONES
# =============================================================================

class AnalysisConfigCreate(BaseModel):
    """Schema para crear configuración"""
    config_name: str = Field(..., max_length=100)
    version: str = Field(..., max_length=50)
    description: Optional[str] = None
    parameters: Dict[str, Any]
    model_version: Optional[str] = None
    model_weights_path: Optional[str] = None
    created_by: Optional[str] = None


class AnalysisConfigUpdate(BaseModel):
    """Schema para actualizar configuración"""
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class AnalysisConfigResponse(BaseModel):
    """Schema de respuesta para configuración"""
    id: int
    config_name: str
    version: str
    description: Optional[str]
    parameters: Dict[str, Any]
    model_version: Optional[str]
    model_weights_path: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


# =============================================================================
# EJECUCIONES
# =============================================================================

class AnalysisExecutionCreate(BaseModel):
    """Schema para iniciar ejecución"""
    execution_name: Optional[str] = None
    config_id: int
    start_date: date
    end_date: date
    sections: Optional[List[int]] = [1, 2, 3, 4, 5]


class AnalysisExecutionUpdate(BaseModel):
    """Schema para actualizar ejecución"""
    status: Optional[str] = None
    processed_documents: Optional[int] = None
    failed_documents: Optional[int] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class AnalysisExecutionResponse(BaseModel):
    """Schema de respuesta para ejecución"""
    id: int
    execution_name: Optional[str]
    config_id: int
    status: str
    start_date: Optional[date]
    end_date: Optional[date]
    total_documents: int
    processed_documents: int
    failed_documents: int
    started_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    execution_metadata: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class ExecutionProgress(BaseModel):
    """Progreso de ejecución en tiempo real"""
    execution_id: int
    status: str
    total_documents: int
    processed_documents: int
    failed_documents: int
    progress_percentage: float
    estimated_time_remaining_seconds: Optional[int]
    current_document: Optional[str]


class ExecutionSummary(BaseModel):
    """Resumen de resultados de una ejecución"""
    execution_id: int
    execution_name: Optional[str]
    config_name: str
    config_version: str
    status: str
    total_documents: int
    processed_documents: int
    failed_documents: int
    
    # Métricas agregadas
    avg_transparency_score: Optional[float]
    risk_distribution: Dict[str, int]  # {high: 10, medium: 20, low: 30}
    total_red_flags: int
    red_flags_by_severity: Dict[str, int]
    
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]


# =============================================================================
# RESULTADOS
# =============================================================================

class AnalysisResultCreate(BaseModel):
    """Schema para crear resultado"""
    document_id: int
    execution_id: int
    config_id: int
    transparency_score: Optional[float] = None
    risk_level: Optional[str] = None
    anomaly_score: Optional[float] = None
    extracted_entities: Optional[Dict[str, Any]] = None
    red_flags: Optional[List[Dict[str, Any]]] = None
    num_red_flags: int = 0
    ml_predictions: Optional[Dict[str, Any]] = None
    extracted_text_sample: Optional[str] = None
    processing_time_seconds: Optional[float] = None


class AnalysisResultResponse(BaseModel):
    """Schema de respuesta para resultado"""
    id: int
    document_id: int
    execution_id: int
    config_id: int
    transparency_score: Optional[float]
    risk_level: Optional[str]
    anomaly_score: Optional[float]
    extracted_entities: Optional[Dict[str, Any]]
    red_flags: Optional[List[Dict[str, Any]]]
    num_red_flags: int
    ml_predictions: Optional[Dict[str, Any]]
    extracted_text_sample: Optional[str]
    processing_time_seconds: Optional[float]
    analyzed_at: datetime
    
    class Config:
        from_attributes = True


class ResultWithDocument(BaseModel):
    """Resultado con información del documento"""
    result: AnalysisResultResponse
    document: BoletinDocumentResponse


# =============================================================================
# RED FLAGS
# =============================================================================

class RedFlagCreate(BaseModel):
    """Schema para crear red flag"""
    result_id: Optional[int] = None
    document_id: int
    flag_type: str = Field(..., max_length=100)
    severity: str = Field(..., max_length=20)
    category: Optional[str] = None
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    page_number: Optional[int] = None


class RedFlagResponse(BaseModel):
    """Schema de respuesta para red flag"""
    id: int
    result_id: Optional[int]
    document_id: int
    flag_type: str
    severity: str
    category: Optional[str]
    title: str
    description: Optional[str]
    evidence: Optional[Dict[str, Any]]
    confidence_score: Optional[float]
    page_number: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class RedFlagStats(BaseModel):
    """Estadísticas de red flags"""
    total_flags: int
    by_severity: Dict[str, int]
    by_type: Dict[str, int]
    by_category: Dict[str, int]
    top_documents: List[Dict[str, Any]]  # Documentos con más flags


# =============================================================================
# COMPARACIONES
# =============================================================================

class AnalysisComparisonCreate(BaseModel):
    """Schema para crear comparación"""
    name: str = Field(..., max_length=200)
    execution_a_id: int
    execution_b_id: int
    notes: Optional[str] = None


class AnalysisComparisonResponse(BaseModel):
    """Schema de respuesta para comparación"""
    id: int
    name: str
    execution_a_id: int
    execution_b_id: int
    comparison_metrics: Optional[Dict[str, Any]]
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ComparisonDetail(BaseModel):
    """Detalle completo de comparación"""
    comparison: AnalysisComparisonResponse
    execution_a: AnalysisExecutionResponse
    execution_b: AnalysisExecutionResponse
    
    # Métricas calculadas
    score_diff_avg: float
    score_diff_median: float
    new_red_flags: int
    resolved_flags: int
    documents_changed_risk: int
    documents_improved: int  # Score mejoró
    documents_worsened: int  # Score empeoró
    
    # Distribuciones
    risk_changes: Dict[str, Dict[str, int]]  # {high: {to_medium: 5, to_low: 2}, ...}


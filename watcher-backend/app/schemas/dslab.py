"""
Schemas Pydantic para el DS Lab - Análisis Persistente
"""
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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
    file_size_bytes: int | None = None
    num_pages: int | None = None


class BoletinDocumentUpdate(BaseModel):
    """Schema para actualizar un documento"""
    analysis_status: str | None = None
    last_analyzed: datetime | None = None
    num_pages: int | None = None


class BoletinDocumentResponse(BaseModel):
    """Schema de respuesta para documento"""
    id: int
    filename: str
    year: int
    month: int
    day: int
    section: int
    file_path: str
    file_size_bytes: int | None
    download_date: datetime
    last_analyzed: datetime | None
    analysis_status: str
    num_pages: int | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentStats(BaseModel):
    """Estadísticas de documentos"""
    total_documents: int
    by_status: dict[str, int]
    by_month: dict[str, int]
    total_size_mb: float
    avg_pages: float | None


# =============================================================================
# CONFIGURACIONES
# =============================================================================

class AnalysisConfigCreate(BaseModel):
    """Schema para crear configuración"""
    model_config = ConfigDict(protected_namespaces=())

    config_name: str = Field(..., max_length=100)
    version: str = Field(..., max_length=50)
    description: str | None = None
    parameters: dict[str, Any]
    model_version: str | None = None
    model_weights_path: str | None = None
    created_by: str | None = None


class AnalysisConfigUpdate(BaseModel):
    """Schema para actualizar configuración"""
    description: str | None = None
    parameters: dict[str, Any] | None = None
    is_active: bool | None = None


class AnalysisConfigResponse(BaseModel):
    """Schema de respuesta para configuración"""
    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    id: int
    config_name: str
    version: str
    description: str | None
    parameters: dict[str, Any]
    model_version: str | None
    model_weights_path: str | None
    created_by: str | None
    created_at: datetime
    is_active: bool


# =============================================================================
# EJECUCIONES
# =============================================================================

class AnalysisExecutionCreate(BaseModel):
    """Schema para iniciar ejecución"""
    execution_name: str | None = None
    config_id: int
    start_date: date
    end_date: date
    sections: list[int] | None = [1, 2, 3, 4, 5]


class AnalysisExecutionUpdate(BaseModel):
    """Schema para actualizar ejecución"""
    status: str | None = None
    processed_documents: int | None = None
    failed_documents: int | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class AnalysisExecutionResponse(BaseModel):
    """Schema de respuesta para ejecución"""
    id: int
    execution_name: str | None
    config_id: int
    status: str
    start_date: date | None
    end_date: date | None
    total_documents: int
    processed_documents: int
    failed_documents: int
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    execution_metadata: dict[str, Any] | None

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
    estimated_time_remaining_seconds: int | None
    current_document: str | None


class ExecutionSummary(BaseModel):
    """Resumen de resultados de una ejecución"""
    execution_id: int
    execution_name: str | None
    config_name: str
    config_version: str
    status: str
    total_documents: int
    processed_documents: int
    failed_documents: int

    # Métricas agregadas
    avg_transparency_score: float | None
    risk_distribution: dict[str, int]  # {high: 10, medium: 20, low: 30}
    total_red_flags: int
    red_flags_by_severity: dict[str, int]

    started_at: datetime
    completed_at: datetime | None
    duration_seconds: float | None


# =============================================================================
# RESULTADOS
# =============================================================================

class AnalysisResultCreate(BaseModel):
    """Schema para crear resultado"""
    document_id: int
    execution_id: int
    config_id: int
    transparency_score: float | None = None
    risk_level: str | None = None
    anomaly_score: float | None = None
    extracted_entities: dict[str, Any] | None = None
    red_flags: list[dict[str, Any]] | None = None
    num_red_flags: int = 0
    ml_predictions: dict[str, Any] | None = None
    extracted_text_sample: str | None = None
    processing_time_seconds: float | None = None


class AnalysisResultResponse(BaseModel):
    """Schema de respuesta para resultado"""
    id: int
    document_id: int
    execution_id: int
    config_id: int
    transparency_score: float | None
    risk_level: str | None
    anomaly_score: float | None
    extracted_entities: dict[str, Any] | None
    red_flags: list[dict[str, Any]] | None
    num_red_flags: int
    ml_predictions: dict[str, Any] | None
    extracted_text_sample: str | None
    processing_time_seconds: float | None
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
    result_id: int | None = None
    document_id: int
    flag_type: str = Field(..., max_length=100)
    severity: str = Field(..., max_length=20)
    category: str | None = None
    title: str = Field(..., max_length=255)
    description: str | None = None
    evidence: dict[str, Any] | None = None
    confidence_score: float | None = None
    page_number: int | None = None


class RedFlagResponse(BaseModel):
    """Schema de respuesta para red flag"""
    id: int
    result_id: int | None
    document_id: int
    flag_type: str
    severity: str
    category: str | None
    title: str
    description: str | None
    evidence: dict[str, Any] | None
    confidence_score: float | None
    page_number: int | None
    created_at: datetime

    class Config:
        from_attributes = True


class RedFlagStats(BaseModel):
    """Estadísticas de red flags"""
    total_flags: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
    by_category: dict[str, int]
    top_documents: list[dict[str, Any]]  # Documentos con más flags


# =============================================================================
# COMPARACIONES
# =============================================================================

class AnalysisComparisonCreate(BaseModel):
    """Schema para crear comparación"""
    name: str = Field(..., max_length=200)
    execution_a_id: int
    execution_b_id: int
    notes: str | None = None


class AnalysisComparisonResponse(BaseModel):
    """Schema de respuesta para comparación"""
    id: int
    name: str
    execution_a_id: int
    execution_b_id: int
    comparison_metrics: dict[str, Any] | None
    notes: str | None
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
    risk_changes: dict[str, dict[str, int]]  # {high: {to_medium: 5, to_low: 2}, ...}


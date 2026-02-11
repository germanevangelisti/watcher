"""
Schemas para sistema de Compliance
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# COMPLIANCE CHECK SCHEMAS
# ============================================================================

class ComplianceCheckBase(BaseModel):
    """Schema base para Compliance Check"""
    check_code: str
    check_name: str
    description: str
    legal_basis: str
    obligation_summary: str
    priority: str
    category: Optional[str] = None
    weight: float = 1.0
    frequency: Optional[str] = None


class ComplianceCheckCreate(ComplianceCheckBase):
    """Schema para crear un Compliance Check"""
    legal_text: Optional[str] = None
    legal_url: Optional[str] = None
    rezago_permitido: Optional[int] = None
    validation_rules: Optional[Dict[str, Any]] = None
    expected_sources: Optional[List[str]] = None
    citizen_explanation: Optional[str] = None
    auditor_notes: Optional[str] = None


class ComplianceCheckResponse(ComplianceCheckBase):
    """Schema de respuesta para Compliance Check"""
    id: int
    legal_text: Optional[str] = None
    legal_url: Optional[str] = None
    rezago_permitido: Optional[int] = None
    validation_rules: Optional[Dict[str, Any]] = None
    expected_sources: Optional[List[str]] = None
    citizen_explanation: Optional[str] = None
    auditor_notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# CHECK RESULT SCHEMAS
# ============================================================================

class CheckResultBase(BaseModel):
    """Schema base para Check Result"""
    status: str
    summary: str


class CheckResultCreate(CheckResultBase):
    """Schema para crear un Check Result"""
    check_id: int
    jurisdiccion_id: Optional[int] = None
    score: Optional[float] = None
    evaluation_date: date
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    reason: Optional[str] = None
    remediation: Optional[str] = None
    evaluation_metadata: Optional[Dict[str, Any]] = None


class CheckResultResponse(CheckResultBase):
    """Schema de respuesta para Check Result"""
    id: int
    check_id: int
    jurisdiccion_id: Optional[int] = None
    score: Optional[float] = None
    evaluation_date: date
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    reason: Optional[str] = None
    remediation: Optional[str] = None
    evaluation_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CheckResultWithDetails(CheckResultResponse):
    """Schema de Check Result con detalles del check"""
    check: ComplianceCheckResponse
    evidences: List["EvidenceResponse"] = []

    class Config:
        from_attributes = True


# ============================================================================
# EVIDENCE SCHEMAS
# ============================================================================

class EvidenceBase(BaseModel):
    """Schema base para Evidence"""
    source_url: str
    source_type: str


class EvidenceCreate(EvidenceBase):
    """Schema para crear Evidence"""
    check_result_id: int
    snapshot_hash: Optional[str] = None
    snapshot_path: Optional[str] = None
    relevant_fragment: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    artifact_metadata: Optional[Dict[str, Any]] = None
    is_valid: bool = True
    validation_notes: Optional[str] = None


class EvidenceResponse(EvidenceBase):
    """Schema de respuesta para Evidence"""
    id: int
    check_result_id: int
    snapshot_hash: Optional[str] = None
    snapshot_path: Optional[str] = None
    captured_at: datetime
    relevant_fragment: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    artifact_metadata: Optional[Dict[str, Any]] = None
    is_valid: bool
    validation_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# SCORECARD SCHEMAS
# ============================================================================

class ScoreBreakdown(BaseModel):
    """Desglose de scores por estado"""
    pass_count: int = Field(..., alias="pass")
    warn_count: int = Field(..., alias="warn")
    fail_count: int = Field(..., alias="fail")
    unknown_count: int = Field(..., alias="unknown")

    class Config:
        populate_by_name = True


class CheckDetail(BaseModel):
    """Detalle de un check en el scorecard"""
    check_code: str
    check_name: str
    priority: str
    category: Optional[str] = None
    legal_basis: str
    status: str
    score: Optional[float] = None
    last_evaluation: Optional[str] = None
    summary: str
    citizen_explanation: Optional[str] = None


class ScorecardOverview(BaseModel):
    """Overview del scorecard"""
    overall_score: Optional[float] = None
    total_checks: int
    status_breakdown: Dict[str, int]
    evaluation_date: str
    jurisdiccion_id: Optional[int] = None


class ComplianceScorecardResponse(BaseModel):
    """Respuesta completa del scorecard de compliance"""
    scorecard: ScorecardOverview
    checks: List[CheckDetail]
    red_flags: List[CheckDetail]
    compliance_level: str


# ============================================================================
# SYNC SCHEMAS
# ============================================================================

class ChecksSyncResponse(BaseModel):
    """Respuesta de sincronización de checks"""
    success: bool
    synced_count: int
    message: str
    checks_summary: Optional[Dict[str, int]] = None


# ============================================================================
# REQUIRED DOCUMENT SCHEMAS
# ============================================================================

class RequiredDocumentBase(BaseModel):
    """Schema base para Required Document"""
    document_type: str
    document_name: str
    period: Optional[str] = None
    expected_format: str


class RequiredDocumentResponse(RequiredDocumentBase):
    """Schema de respuesta para Required Document"""
    id: int
    check_id: Optional[int] = None
    jurisdiccion_id: Optional[int] = None
    expected_url: Optional[str] = None
    status: str
    local_path: Optional[str] = None
    file_hash: Optional[str] = None
    file_size_bytes: Optional[int] = None
    downloaded_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    last_checked: Optional[datetime] = None
    indexed_in_rag: bool
    embedding_model: Optional[str] = None
    num_chunks: Optional[int] = None
    metadata_json: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JurisdictionDocumentsSummary(BaseModel):
    """Resumen de documentos de una jurisdicción"""
    jurisdiction_code: str
    jurisdiction_id: Optional[int] = None
    jurisdiction_name: str
    applicable_laws: List[str]
    total_documents: int
    missing: int
    downloaded: int
    processed: int
    coverage_percentage: float
    by_type: Dict[str, Dict[str, int]]


class DocumentsOverviewResponse(BaseModel):
    """Overview completo de documentos por jurisdicción"""
    jurisdictions: List[JurisdictionDocumentsSummary]
    total_documents: int
    total_missing: int
    total_processed: int
    overall_coverage: float


class DocumentUpdateRequest(BaseModel):
    """Request para actualizar estado de documento"""
    local_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    indexed_in_rag: Optional[bool] = None
    embedding_model: Optional[str] = None
    num_chunks: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


# Update forward refs
CheckResultWithDetails.model_rebuild()

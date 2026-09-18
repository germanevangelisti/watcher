"""
Schemas para sistema de Compliance
"""

from datetime import date, datetime
from typing import Any

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
    category: str | None = None
    weight: float = 1.0
    frequency: str | None = None


class ComplianceCheckCreate(ComplianceCheckBase):
    """Schema para crear un Compliance Check"""
    legal_text: str | None = None
    legal_url: str | None = None
    rezago_permitido: int | None = None
    validation_rules: dict[str, Any] | None = None
    expected_sources: list[str] | None = None
    citizen_explanation: str | None = None
    auditor_notes: str | None = None


class ComplianceCheckResponse(ComplianceCheckBase):
    """Schema de respuesta para Compliance Check"""
    id: int
    legal_text: str | None = None
    legal_url: str | None = None
    rezago_permitido: int | None = None
    validation_rules: dict[str, Any] | None = None
    expected_sources: list[str] | None = None
    citizen_explanation: str | None = None
    auditor_notes: str | None = None
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
    jurisdiccion_id: int | None = None
    score: float | None = None
    evaluation_date: date
    period_start: date | None = None
    period_end: date | None = None
    reason: str | None = None
    remediation: str | None = None
    evaluation_metadata: dict[str, Any] | None = None


class CheckResultResponse(CheckResultBase):
    """Schema de respuesta para Check Result"""
    id: int
    check_id: int
    jurisdiccion_id: int | None = None
    score: float | None = None
    evaluation_date: date
    period_start: date | None = None
    period_end: date | None = None
    reason: str | None = None
    remediation: str | None = None
    evaluation_metadata: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class CheckResultWithDetails(CheckResultResponse):
    """Schema de Check Result con detalles del check"""
    check: ComplianceCheckResponse
    evidences: list["EvidenceResponse"] = []

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
    snapshot_hash: str | None = None
    snapshot_path: str | None = None
    relevant_fragment: str | None = None
    extracted_data: dict[str, Any] | None = None
    artifact_metadata: dict[str, Any] | None = None
    is_valid: bool = True
    validation_notes: str | None = None


class EvidenceResponse(EvidenceBase):
    """Schema de respuesta para Evidence"""
    id: int
    check_result_id: int
    snapshot_hash: str | None = None
    snapshot_path: str | None = None
    captured_at: datetime
    relevant_fragment: str | None = None
    extracted_data: dict[str, Any] | None = None
    artifact_metadata: dict[str, Any] | None = None
    is_valid: bool
    validation_notes: str | None = None
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
    category: str | None = None
    legal_basis: str
    status: str
    score: float | None = None
    last_evaluation: str | None = None
    summary: str
    citizen_explanation: str | None = None


class ScorecardOverview(BaseModel):
    """Overview del scorecard"""
    overall_score: float | None = None
    total_checks: int
    status_breakdown: dict[str, int]
    evaluation_date: str
    jurisdiccion_id: int | None = None


class ComplianceScorecardResponse(BaseModel):
    """Respuesta completa del scorecard de compliance"""
    scorecard: ScorecardOverview
    checks: list[CheckDetail]
    red_flags: list[CheckDetail]
    compliance_level: str


# ============================================================================
# SYNC SCHEMAS
# ============================================================================

class ChecksSyncResponse(BaseModel):
    """Respuesta de sincronización de checks"""
    success: bool
    synced_count: int
    message: str
    checks_summary: dict[str, int] | None = None


# ============================================================================
# REQUIRED DOCUMENT SCHEMAS
# ============================================================================

class RequiredDocumentBase(BaseModel):
    """Schema base para Required Document"""
    document_type: str
    document_name: str
    period: str | None = None
    expected_format: str


class RequiredDocumentResponse(RequiredDocumentBase):
    """Schema de respuesta para Required Document"""
    id: int
    check_id: int | None = None
    jurisdiccion_id: int | None = None
    expected_url: str | None = None
    status: str
    local_path: str | None = None
    file_hash: str | None = None
    file_size_bytes: int | None = None
    downloaded_at: datetime | None = None
    processed_at: datetime | None = None
    last_checked: datetime | None = None
    indexed_in_rag: bool
    embedding_model: str | None = None
    num_chunks: int | None = None
    metadata_json: dict[str, Any] | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JurisdictionDocumentsSummary(BaseModel):
    """Resumen de documentos de una jurisdicción"""
    jurisdiction_code: str
    jurisdiction_id: int | None = None
    jurisdiction_name: str
    applicable_laws: list[str]
    total_documents: int
    missing: int
    downloaded: int
    processed: int
    coverage_percentage: float
    by_type: dict[str, dict[str, int]]


class DocumentsOverviewResponse(BaseModel):
    """Overview completo de documentos por jurisdicción"""
    jurisdictions: list[JurisdictionDocumentsSummary]
    total_documents: int
    total_missing: int
    total_processed: int
    overall_coverage: float


class DocumentUpdateRequest(BaseModel):
    """Request para actualizar estado de documento"""
    local_path: str | None = None
    file_size_bytes: int | None = None
    indexed_in_rag: bool | None = None
    embedding_model: str | None = None
    num_chunks: int | None = None
    metadata: dict[str, Any] | None = None


# Update forward refs
CheckResultWithDetails.model_rebuild()

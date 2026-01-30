"""
Configuración centralizada para agentes
"""
from typing import Dict, Any
from pydantic import BaseModel, Field


class DocumentIntelligenceConfig(BaseModel):
    """Configuración para Document Intelligence Agent"""
    extract_tables: bool = True
    extract_images: bool = False
    use_ocr: bool = False
    min_entity_confidence: float = 0.7
    extract_amounts: bool = True
    extract_beneficiaries: bool = True
    extract_organisms: bool = True
    extract_dates: bool = True
    amount_regex_patterns: list = Field(default_factory=lambda: [
        r'\$\s*[\d\.,]+',
        r'(?:pesos|ARS|PESOS)\s*[\d\.,]+',
        r'[\d\.,]+\s*(?:millones?|mil)'
    ])
    beneficiary_keywords: list = Field(default_factory=lambda: [
        'adjudicatario', 'beneficiario', 'contratista', 'proveedor', 'empresa'
    ])


class AnomalyDetectionConfig(BaseModel):
    """Configuración para Anomaly Detection Agent"""
    transparency_thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "high_risk": 30.0,
        "medium_risk": 50.0,
        "low_risk": 70.0
    })
    amount_thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "suspicious_amount": 10000000.0,
        "very_high": 50000000.0
    })
    red_flag_rules: Dict[str, Any] = Field(default_factory=lambda: {
        "HIGH_AMOUNT": {
            "enabled": True,
            "threshold": 50000000
        },
        "MISSING_BENEFICIARY": {
            "enabled": True
        },
        "SUSPICIOUS_AMOUNT_PATTERN": {
            "enabled": True,
            "patterns": ["999999", "9999"]
        },
        "LOW_TRANSPARENCY_SCORE": {
            "enabled": True,
            "threshold": 30
        }
    })
    ml_models: Dict[str, Any] = Field(default_factory=lambda: {
        "isolation_forest": {
            "contamination": 0.1,
            "n_estimators": 100
        },
        "random_forest": {
            "n_estimators": 100,
            "max_depth": 10
        }
    })


class InsightReportingConfig(BaseModel):
    """Configuración para Insight & Reporting Agent"""
    enable_chat: bool = True
    enable_report_generation: bool = True
    max_conversation_history: int = 10
    use_vector_db: bool = False
    temperature: float = 0.7
    max_tokens: int = 2000


class OrchestratorConfig(BaseModel):
    """Configuración para Agent Orchestrator"""
    max_concurrent_tasks: int = 5
    task_timeout_seconds: int = 300
    enable_auto_approval: bool = False
    auto_approval_risk_threshold: str = "low"


class AgentSystemConfig(BaseModel):
    """Configuración completa del sistema de agentes"""
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    document_intelligence: DocumentIntelligenceConfig = Field(
        default_factory=DocumentIntelligenceConfig
    )
    anomaly_detection: AnomalyDetectionConfig = Field(
        default_factory=AnomalyDetectionConfig
    )
    insight_reporting: InsightReportingConfig = Field(
        default_factory=InsightReportingConfig
    )
    
    # API Keys y recursos
    openai_api_key: str = "REDACTED_OPENAI_KEY"
    enable_observability: bool = True
    log_level: str = "INFO"


# Configuración por defecto
DEFAULT_AGENT_CONFIG = AgentSystemConfig()






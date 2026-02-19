"""
Modelos de base de datos - Versión completa con historial acumulativo
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Float, Date, Boolean, Index
from sqlalchemy.orm import relationship
from .database import Base

# ENUMS

class JurisdiccionTipo(str, Enum):
    """Tipos de jurisdicciones en Córdoba"""
    PROVINCIA = "provincia"
    CAPITAL = "capital"
    MUNICIPALIDAD = "municipalidad"
    COMUNA = "comuna"
    DESCONOCIDO = "desconocido"

class FuenteBoletin(str, Enum):
    """Fuentes de boletines oficiales"""
    PROVINCIAL = "provincial"  # Boletín Oficial de la Provincia
    MUNICIPAL_CAPITAL = "municipal_capital"  # Boletín de Ciudad de Córdoba
    MUNICIPAL_OTROS = "municipal_otros"  # Otros boletines municipales

# MODELOS PRINCIPALES

class Boletin(Base):
    """Modelo para almacenar información de boletines."""
    __tablename__ = "boletines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, unique=True, index=True)
    date = Column(String)  # YYYYMMDD format
    section = Column(String)
    status = Column(String)  # pending, processing, completed, error
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message = Column(Text, nullable=True)
    
    # Deduplication fields (Epic 1.1)
    file_hash = Column(String(64), nullable=True, index=True)  # SHA256 hash for deduplication
    file_size_bytes = Column(Integer, nullable=True)
    
    # Campos jurisdiccionales (NUEVO)
    fuente = Column(String(50), default="provincial", nullable=False)  # Valores: provincial, municipal_capital, municipal_otros
    jurisdiccion_id = Column(Integer, ForeignKey("jurisdicciones.id"), nullable=True)
    seccion_nombre = Column(String(100), nullable=True)  # Nombre legible de la sección
    
    # Origen del documento (v1.1 Phase 2)
    origin = Column(String(20), default="downloaded", nullable=False)  # downloaded, uploaded, synced

    # Relaciones
    analisis = relationship("Analisis", back_populates="boletin", cascade="all, delete-orphan")
    ejecuciones = relationship("EjecucionPresupuestaria", back_populates="boletin", cascade="all, delete-orphan")
    jurisdiccion = relationship("Jurisdiccion", back_populates="boletines", lazy="joined")
    menciones_jurisdiccionales = relationship("MencionJurisdiccional", back_populates="boletin", cascade="all, delete-orphan", lazy="select")

class Analisis(Base):
    """Modelo para almacenar análisis de actos administrativos individuales."""
    __tablename__ = "analisis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    boletin_id = Column(Integer, ForeignKey("boletines.id"))
    fragmento = Column(Text)
    categoria = Column(String)  # Legacy: kept for backward compat
    entidad_beneficiaria = Column(String)
    monto_estimado = Column(String, nullable=True)
    monto_numerico = Column(Float, nullable=True)
    riesgo = Column(String)  # alto, medio, bajo, informativo (was: ALTO, MEDIO, BAJO)
    tipo_curro = Column(String, nullable=True)  # Legacy: kept for backward compat
    accion_sugerida = Column(Text, nullable=True)
    datos_extra = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # v2 fields: structured multi-acto analysis
    tipo_acto = Column(String(50), nullable=True)  # decreto, resolucion, licitacion, designacion, subsidio, transferencia, otro
    numero_acto = Column(String(100), nullable=True)  # "Resolución N° 1813"
    organismo = Column(String(200), nullable=True)  # Organismo emisor
    beneficiarios_json = Column(JSON, nullable=True)  # ["persona1", "empresa2"]
    montos_json = Column(JSON, nullable=True)  # ["$1.000.000", "$500.000"]
    descripcion = Column(Text, nullable=True)  # Resumen del acto
    motivo_riesgo = Column(Text, nullable=True)  # Justificación del riesgo asignado

    # Relación con boletín
    boletin = relationship("Boletin", back_populates="analisis")

class ActoAdministrativo(Base):
    """Modelo para actos administrativos extraídos de boletines"""
    __tablename__ = "actos_administrativos"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    boletin_id = Column(Integer, ForeignKey("boletines.id"), nullable=True)
    
    # Identificación del acto
    tipo_acto = Column(String, index=True)  # DECRETO, RESOLUCIÓN, LICITACIÓN, etc.
    numero = Column(String, nullable=True)
    fecha = Column(Date, nullable=True)
    
    # Partes involucradas
    organismo = Column(String, index=True)
    beneficiario = Column(String, nullable=True)
    
    # Datos fiscales
    monto = Column(Float, nullable=True, index=True)
    partida = Column(String, nullable=True, index=True)
    
    # Contenido
    descripcion = Column(Text)
    keywords = Column(String, nullable=True)  # CSV de keywords
    fragmento_original = Column(Text)
    pagina = Column(Integer, nullable=True)
    
    # Análisis
    nivel_riesgo = Column(String, index=True)  # ALTO, MEDIO, BAJO
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índices para consultas eficientes
    __table_args__ = (
        Index('idx_acto_tipo_riesgo', 'tipo_acto', 'nivel_riesgo'),
        Index('idx_acto_organismo_fecha', 'organismo', 'fecha'),
        Index('idx_acto_monto', 'monto'),
    )

class VinculoActoPresupuesto(Base):
    """Vínculos entre actos administrativos y programas presupuestarios"""
    __tablename__ = "vinculos_acto_presupuesto"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    acto_id = Column(Integer, ForeignKey("actos_administrativos.id"), index=True)
    programa_id = Column(Integer, ForeignKey("presupuesto_base.id"), index=True)
    
    # Score y método de matching
    score_confianza = Column(Float, index=True)  # 0.0 - 1.0
    metodo_matching = Column(String)  # partida, organismo, keywords, semantico
    
    # Detalles del match
    detalles_json = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Índices
    __table_args__ = (
        Index('idx_vinculo_score', 'score_confianza'),
        Index('idx_vinculo_acto_score', 'acto_id', 'score_confianza'),
    )

# MODELOS EXTENDIDOS PARA HISTORIAL ACUMULATIVO

class PresupuestoBase(Base):
    """Presupuesto oficial inicial y metas de gestión."""
    __tablename__ = "presupuesto_base"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ejercicio = Column(Integer, index=True)  # 2025
    organismo = Column(String, index=True)
    programa = Column(String)
    subprograma = Column(String, nullable=True)
    partida_presupuestaria = Column(String)
    descripcion = Column(Text)
    monto_inicial = Column(Float)
    monto_vigente = Column(Float)  # Después de modificaciones
    fecha_aprobacion = Column(Date)
    meta_fisica = Column(String, nullable=True)  # Descripción de la meta
    meta_numerica = Column(Float, nullable=True)  # Valor numérico de la meta
    unidad_medida = Column(String, nullable=True)  # m2, personas, etc.
    cronograma_json = Column(JSON, nullable=True)  # Metas por trimestre/mes
    fuente_financiamiento = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    ejecuciones = relationship("EjecucionPresupuestaria", back_populates="presupuesto_base")
    
    # Índices para consultas eficientes
    __table_args__ = (
        Index('idx_presupuesto_ejercicio_organismo', 'ejercicio', 'organismo'),
        Index('idx_presupuesto_partida', 'partida_presupuestaria'),
    )

class EjecucionPresupuestaria(Base):
    """Ejecución acumulativa del presupuesto extraída de boletines."""
    __tablename__ = "ejecucion_presupuestaria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    boletin_id = Column(Integer, ForeignKey("boletines.id"))
    presupuesto_base_id = Column(Integer, ForeignKey("presupuesto_base.id"), nullable=True)
    
    # Datos de la ejecución
    fecha_boletin = Column(Date, index=True)
    organismo = Column(String, index=True)
    beneficiario = Column(String)
    concepto = Column(Text)
    monto = Column(Float)
    tipo_operacion = Column(String)  # gasto, transferencia, subsidio, obra, etc.
    
    # Clasificación presupuestaria
    partida_presupuestaria = Column(String, nullable=True)
    programa = Column(String, nullable=True)
    subprograma = Column(String, nullable=True)
    
    # Metadatos del análisis
    categoria_watcher = Column(String)  # Del análisis de Watcher
    riesgo_watcher = Column(String)
    
    # Acumuladores
    monto_acumulado_mes = Column(Float, nullable=True)
    monto_acumulado_trimestre = Column(Float, nullable=True)
    monto_acumulado_anual = Column(Float, nullable=True)
    
    # Control
    es_modificacion_presupuestaria = Column(Boolean, default=False)
    requiere_revision = Column(Boolean, default=False)
    observaciones = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    boletin = relationship("Boletin", back_populates="ejecuciones")
    presupuesto_base = relationship("PresupuestoBase", back_populates="ejecuciones")
    
    # Índices para consultas eficientes
    __table_args__ = (
        Index('idx_ejecucion_fecha_organismo', 'fecha_boletin', 'organismo'),
        Index('idx_ejecucion_monto', 'monto'),
        Index('idx_ejecucion_tipo', 'tipo_operacion'),
    )

class MetricasGestion(Base):
    """Métricas calculadas de gestión y comparación."""
    __tablename__ = "metricas_gestion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Período de cálculo
    ejercicio = Column(Integer, index=True)
    periodo = Column(String, index=True)  # 'mensual', 'trimestral', 'anual'
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)
    
    # Organismo/Programa
    organismo = Column(String, index=True)
    programa = Column(String, nullable=True)
    
    # Métricas presupuestarias
    presupuesto_inicial = Column(Float)
    presupuesto_vigente = Column(Float)
    ejecutado_acumulado = Column(Float)
    porcentaje_ejecucion = Column(Float)
    desvio_presupuestario = Column(Float)  # % de desvío
    
    # Métricas de metas físicas
    meta_fisica_planificada = Column(Float, nullable=True)
    meta_fisica_ejecutada = Column(Float, nullable=True)
    porcentaje_avance_fisico = Column(Float, nullable=True)
    
    # Métricas de riesgo (del análisis Watcher)
    total_operaciones = Column(Integer)
    operaciones_alto_riesgo = Column(Integer)
    operaciones_medio_riesgo = Column(Integer)
    monto_alto_riesgo = Column(Float)
    porcentaje_riesgo = Column(Float)
    
    # Métricas de concentración
    beneficiarios_unicos = Column(Integer)
    concentracion_beneficiarios = Column(Float)  # % del top 10%
    
    # Alertas automáticas
    tiene_alertas = Column(Boolean, default=False)
    alertas_json = Column(JSON, nullable=True)
    
    # Comparación temporal
    variacion_mes_anterior = Column(Float, nullable=True)
    variacion_mismo_periodo_anio_anterior = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Índices
    __table_args__ = (
        Index('idx_metricas_ejercicio_periodo', 'ejercicio', 'periodo'),
        Index('idx_metricas_organismo_fecha', 'organismo', 'fecha_fin'),
    )

class AlertasGestion(Base):
    """Sistema de alertas automáticas."""
    __tablename__ = "alertas_gestion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clasificación de la alerta
    tipo_alerta = Column(String, index=True)  # 'presupuestaria', 'riesgo', 'concentracion', 'meta'
    nivel_severidad = Column(String, index=True)  # 'critica', 'alta', 'media', 'baja'
    
    # Contexto
    organismo = Column(String, index=True)
    programa = Column(String, nullable=True)
    fecha_deteccion = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Descripción
    titulo = Column(String)
    descripcion = Column(Text)
    valor_detectado = Column(Float, nullable=True)
    valor_esperado = Column(Float, nullable=True)
    porcentaje_desvio = Column(Float, nullable=True)
    
    # Referencias
    boletin_id = Column(Integer, ForeignKey("boletines.id"), nullable=True)
    ejecucion_id = Column(Integer, ForeignKey("ejecucion_presupuestaria.id"), nullable=True)
    
    # Estado de la alerta
    estado = Column(String, default='activa')  # 'activa', 'revisada', 'resuelta', 'falsa'
    fecha_revision = Column(DateTime, nullable=True)
    observaciones_revision = Column(Text, nullable=True)
    
    # Acciones sugeridas
    acciones_sugeridas = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Índices
    __table_args__ = (
        Index('idx_alertas_tipo_nivel', 'tipo_alerta', 'nivel_severidad'),
        Index('idx_alertas_estado_fecha', 'estado', 'fecha_deteccion'),
    )

class ProcesamientoBatch(Base):
    """Control de procesamiento batch."""
    __tablename__ = "procesamiento_batch"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identificación del batch
    batch_id = Column(String, unique=True, index=True)
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_fin = Column(DateTime, nullable=True)
    
    # Configuración
    directorio_origen = Column(String)
    filtros_aplicados = Column(JSON, nullable=True)
    
    # Estadísticas
    total_archivos = Column(Integer)
    archivos_procesados = Column(Integer, default=0)
    archivos_fallidos = Column(Integer, default=0)
    
    # Resultados
    total_ejecuciones_detectadas = Column(Integer, default=0)
    monto_total_procesado = Column(Float, default=0.0)
    alertas_generadas = Column(Integer, default=0)
    
    # Estado
    estado = Column(String, default='iniciado')  # 'iniciado', 'procesando', 'completado', 'error'
    error_message = Column(Text, nullable=True)
    
    # Métricas de rendimiento
    tiempo_procesamiento_segundos = Column(Float, nullable=True)
    archivos_por_segundo = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =============================================================================
# MODELOS DS LAB - ANÁLISIS PERSISTENTE
# =============================================================================

class BoletinDocument(Base):
    """Metadata extendida de boletines para análisis DS Lab"""
    __tablename__ = "boletin_documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), unique=True, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    day = Column(Integer, nullable=False, index=True)
    section = Column(Integer, nullable=False, index=True)
    
    file_path = Column(Text, nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    download_date = Column(DateTime, default=datetime.utcnow)
    
    last_analyzed = Column(DateTime, nullable=True)
    analysis_status = Column(String(50), default='pending', index=True)  # pending, analyzing, completed, failed
    num_pages = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    analysis_results = relationship("AnalysisResult", back_populates="document", cascade="all, delete-orphan")
    red_flags = relationship("RedFlag", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_boletin_doc_date', 'year', 'month', 'day'),
        Index('idx_boletin_doc_status', 'analysis_status'),
    )


class AnalysisConfig(Base):
    """Configuraciones y versiones de modelos de análisis"""
    __tablename__ = "analysis_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    
    parameters = Column(JSON, nullable=False)  # Parámetros del análisis
    model_version = Column(String(50), nullable=True)
    model_weights_path = Column(Text, nullable=True)
    
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)
    
    # Relaciones
    executions = relationship("AnalysisExecution", back_populates="config")
    results = relationship("AnalysisResult", back_populates="config")
    
    __table_args__ = (
        Index('idx_config_name_version', 'config_name', 'version', unique=True),
    )


class AnalysisExecution(Base):
    """Ejecuciones de análisis"""
    __tablename__ = "analysis_executions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_name = Column(String(200), nullable=True)
    config_id = Column(Integer, ForeignKey("analysis_configs.id"), nullable=False, index=True)
    
    status = Column(String(50), default='pending', index=True)  # pending, running, completed, failed, cancelled
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    
    total_documents = Column(Integer, default=0)
    processed_documents = Column(Integer, default=0)
    failed_documents = Column(Integer, default=0)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    error_message = Column(Text, nullable=True)
    execution_metadata = Column(JSON, nullable=True)  # Logs, warnings, etc.
    
    # Relaciones
    config = relationship("AnalysisConfig", back_populates="executions")
    results = relationship("AnalysisResult", back_populates="execution", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_execution_status', 'status'),
        Index('idx_execution_dates', 'started_at', 'completed_at'),
    )


class AnalysisResult(Base):
    """Resultados detallados de análisis por documento"""
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("boletin_documents.id"), nullable=False, index=True)
    execution_id = Column(Integer, ForeignKey("analysis_executions.id"), nullable=False, index=True)
    config_id = Column(Integer, ForeignKey("analysis_configs.id"), nullable=False, index=True)
    
    # Scores y métricas
    transparency_score = Column(Float, nullable=True, index=True)
    risk_level = Column(String(20), nullable=True, index=True)  # high, medium, low
    anomaly_score = Column(Float, nullable=True)
    
    # Entidades extraídas
    extracted_entities = Column(JSON, nullable=True)  # {amounts: [], beneficiaries: [], contracts: []}
    
    # Red Flags detectadas
    red_flags = Column(JSON, nullable=True)  # [{type: 'high_amount', severity: 'high', description: '...'}]
    num_red_flags = Column(Integer, default=0, index=True)
    
    # Clasificaciones ML
    ml_predictions = Column(JSON, nullable=True)  # {random_forest: 0.85, isolation_forest: 'anomaly'}
    
    # Texto y contexto
    extracted_text_sample = Column(Text, nullable=True)  # Primeros 5000 chars
    processing_time_seconds = Column(Float, nullable=True)
    
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    document = relationship("BoletinDocument", back_populates="analysis_results")
    execution = relationship("AnalysisExecution", back_populates="results")
    config = relationship("AnalysisConfig", back_populates="results")
    red_flag_details = relationship("RedFlag", back_populates="result", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_result_document_execution', 'document_id', 'execution_id', unique=True),
        Index('idx_result_risk', 'risk_level'),
        Index('idx_result_score', 'transparency_score'),
    )


class RedFlag(Base):
    """Red flags individuales (para análisis detallado)"""
    __tablename__ = "red_flags"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("boletin_documents.id"), nullable=False, index=True)
    
    flag_type = Column(String(100), nullable=False, index=True)  # HIGH_AMOUNT, MISSING_INFO, etc.
    severity = Column(String(20), nullable=False, index=True)  # critical, high, medium, low
    category = Column(String(100), nullable=True)  # transparency, amounts, patterns, entities
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    evidence = Column(JSON, nullable=True)  # Datos específicos que triggerearon la flag
    
    confidence_score = Column(Float, nullable=True)
    page_number = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    result = relationship("AnalysisResult", back_populates="red_flag_details")
    document = relationship("BoletinDocument", back_populates="red_flags")
    
    __table_args__ = (
        Index('idx_red_flag_type', 'flag_type'),
        Index('idx_red_flag_severity', 'severity'),
        Index('idx_red_flag_document', 'document_id'),
    )


class AnalysisComparison(Base):
    """Comparaciones entre ejecuciones"""
    __tablename__ = "analysis_comparisons"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    execution_a_id = Column(Integer, ForeignKey("analysis_executions.id"), nullable=False, index=True)
    execution_b_id = Column(Integer, ForeignKey("analysis_executions.id"), nullable=False, index=True)
    
    # Métricas de comparación
    comparison_metrics = Column(JSON, nullable=True)
    # {
    #   "score_diff_avg": 5.2,
    #   "new_red_flags": 15,
    #   "resolved_flags": 8,
    #   "documents_changed_risk": 12
    # }
    
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_comparison_executions', 'execution_a_id', 'execution_b_id'),
    )


# =============================================================================
# MODELOS PARA SISTEMA DE AGENTES INTELIGENTES
# =============================================================================

class AgentWorkflow(Base):
    """Workflow de agentes - Flujo completo de análisis"""
    
    __tablename__ = "agent_workflows"
    
    id = Column(String(36), primary_key=True, index=True)
    workflow_name = Column(String(255), nullable=False)
    workflow_type = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)  # pending, in_progress, completed, failed, cancelled
    
    # Configuración y parámetros
    parameters = Column(JSON, nullable=True)
    config = Column(JSON, nullable=True)
    
    # Resultados
    results = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Métricas
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    progress_percentage = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Usuario (para futura implementación)
    created_by = Column(String(100), nullable=True)
    
    # Relaciones
    tasks = relationship("AgentTask", back_populates="workflow", cascade="all, delete-orphan")
    logs = relationship("WorkflowLog", back_populates="workflow", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_workflow_status_created', 'status', 'created_at'),
        Index('idx_workflow_type_status', 'workflow_type', 'status'),
    )
    
    def __repr__(self):
        return f"<AgentWorkflow(id={self.id}, name={self.workflow_name}, status={self.status})>"


class AgentTask(Base):
    """Tarea individual dentro de un workflow"""
    
    __tablename__ = "agent_tasks"
    
    id = Column(String(50), primary_key=True, index=True)
    workflow_id = Column(String(36), ForeignKey("agent_workflows.id"), nullable=False, index=True)
    
    # Definición de la tarea
    task_type = Column(String(100), nullable=False)
    agent_type = Column(String(50), nullable=False)
    priority = Column(Integer, default=0)
    requires_approval = Column(Boolean, default=False)
    
    # Estado
    status = Column(String(50), nullable=False, default="pending")  # pending, in_progress, completed, failed, awaiting_approval, cancelled
    
    # Datos
    parameters = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Aprobación
    approval_status = Column(String(50), nullable=True)  # approved, rejected, pending
    approval_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relaciones
    workflow = relationship("AgentWorkflow", back_populates="tasks")
    
    __table_args__ = (
        Index('idx_task_workflow_status', 'workflow_id', 'status'),
    )
    
    def __repr__(self):
        return f"<AgentTask(id={self.id}, type={self.task_type}, status={self.status})>"


class WorkflowLog(Base):
    """Logs de ejecución de workflows"""
    
    __tablename__ = "workflow_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String(36), ForeignKey("agent_workflows.id"), nullable=False, index=True)
    
    # Log data
    level = Column(String(20), nullable=False)  # info, warning, error, debug
    message = Column(Text, nullable=False)
    source = Column(String(100), nullable=True)  # Qué agente o componente generó el log
    
    # Metadata adicional
    extra_data = Column(JSON, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relaciones
    workflow = relationship("AgentWorkflow", back_populates="logs")
    
    __table_args__ = (
        Index('idx_log_workflow_created', 'workflow_id', 'created_at'),
        Index('idx_log_level', 'level'),
    )
    
    def __repr__(self):
        return f"<WorkflowLog(id={self.id}, level={self.level}, message={self.message[:50]})>"


class Jurisdiccion(Base):
    """Jurisdicciones de la Provincia de Córdoba"""
    
    __tablename__ = "jurisdicciones"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Información básica
    nombre = Column(String(200), nullable=False, unique=True, index=True)
    tipo = Column(String(50), nullable=False, index=True)  # Valores: provincia, capital, municipalidad, comuna
    
    # Ubicación geográfica
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    codigo_postal = Column(String(10), nullable=True)
    departamento = Column(String(100), nullable=True)  # Departamento/región
    
    # Datos demográficos
    poblacion = Column(Integer, nullable=True)
    superficie_km2 = Column(Float, nullable=True)
    
    # Metadata adicional
    extra_data = Column(JSON, nullable=True)  # Para info extra: URLs, contactos, etc
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relaciones
    boletines = relationship("Boletin", back_populates="jurisdiccion")
    menciones = relationship("MencionJurisdiccional", back_populates="jurisdiccion")
    
    def __repr__(self):
        return f"<Jurisdiccion(nombre={self.nombre}, tipo={self.tipo})>"


class JurisdiccionSyncConfig(Base):
    """
    Configuración de sincronización de boletines por jurisdicción (v1.1 Phase 2).
    Define cómo y de dónde descargar documentos para cada jurisdicción.
    """
    __tablename__ = "jurisdiccion_sync_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    jurisdiccion_id = Column(Integer, ForeignKey("jurisdicciones.id"), nullable=False, unique=True, index=True)
    
    # Configuración de fuente
    source_url_template = Column(String(500), nullable=True)  # URL template con {year}, {month}, {day}, {section}
    scraper_type = Column(String(50), default="generic", nullable=False)  # provincial, municipal, national, generic
    sync_enabled = Column(Boolean, default=False, nullable=False)
    
    # Estado de sincronización
    last_sync_date = Column(Date, nullable=True)
    last_sync_timestamp = Column(DateTime, nullable=True)
    last_sync_status = Column(String(20), default="idle")  # idle, syncing, completed, failed
    last_sync_error = Column(Text, nullable=True)
    
    # Configuración adicional
    sync_frequency = Column(String(20), default="manual")  # manual, daily, weekly
    sections_to_sync = Column(JSON, nullable=True)  # e.g. ["1_Secc", "2_Secc"]
    extra_config = Column(JSON, nullable=True)  # Additional scraper-specific configuration
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relaciones
    jurisdiccion = relationship("Jurisdiccion", backref="sync_config", uselist=False)
    
    def __repr__(self):
        return f"<JurisdiccionSyncConfig(jurisdiccion_id={self.jurisdiccion_id}, enabled={self.sync_enabled})>"


class MencionJurisdiccional(Base):
    """
    Tracking de menciones de jurisdicciones dentro de boletines.
    
    Ejemplo: Boletín provincial sección 5 menciona "Municipalidad de Alta Gracia"
    """
    
    __tablename__ = "menciones_jurisdiccionales"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Referencias
    boletin_id = Column(Integer, ForeignKey("boletines.id"), nullable=False, index=True)
    jurisdiccion_id = Column(Integer, ForeignKey("jurisdicciones.id"), nullable=False, index=True)
    
    # Detalles de la mención
    tipo_mencion = Column(String(50), nullable=True)  # decreto, resolucion, licitacion, ordenanza
    seccion = Column(Integer, nullable=True)  # Sección del boletín donde aparece
    confianza = Column(Float, default=1.0)  # Confianza del NER (0.0 a 1.0)
    extracto = Column(Text, nullable=True)  # Fragmento de texto relevante
    
    # Metadata
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relaciones
    boletin = relationship("Boletin", back_populates="menciones_jurisdiccionales")
    jurisdiccion = relationship("Jurisdiccion", back_populates="menciones")
    
    # Índices para búsqueda rápida
    __table_args__ = (
        Index('idx_mencion_boletin_jurisdiccion', 'boletin_id', 'jurisdiccion_id'),
        Index('idx_mencion_tipo', 'tipo_mencion'),
    )
    
    def __repr__(self):
        return f"<MencionJurisdiccional(boletin_id={self.boletin_id}, jurisdiccion={self.jurisdiccion_id})>"


class SyncState(Base):
    """Estado de sincronización de boletines"""
    
    __tablename__ = "sync_state"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Estado de sincronización
    last_synced_date = Column(Date, nullable=True)  # Última fecha sincronizada con éxito
    last_sync_timestamp = Column(DateTime, nullable=True)  # Cuándo se ejecutó la última sincronización
    next_scheduled_sync = Column(DateTime, nullable=True)  # Próxima ejecución programada
    
    # Estado actual
    status = Column(String(20), default="idle")  # idle, syncing, processing, completed, error
    
    # Estadísticas de la última sincronización
    boletines_pending = Column(Integer, default=0)  # Pendientes de descargar
    boletines_downloaded = Column(Integer, default=0)  # Descargados en última sync
    boletines_processed = Column(Integer, default=0)  # Procesados en última sync
    boletines_failed = Column(Integer, default=0)  # Fallidos en última sync
    
    # Configuración de scheduler
    auto_sync_enabled = Column(Boolean, default=False)  # Si está habilitado el sync automático
    sync_frequency = Column(String(20), default="daily")  # daily, weekly, manual
    sync_hour = Column(Integer, default=6)  # Hora del día para ejecutar (0-23)
    
    # Errores y logs
    error_message = Column(Text, nullable=True)
    current_operation = Column(String(100), nullable=True)  # Operación actual en progreso
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<SyncState(status={self.status}, last_synced={self.last_synced_date})>"


# =============================================================================
# KNOWLEDGE GRAPH - ENTIDADES Y RELACIONES
# =============================================================================

class EntidadExtraida(Base):
    """
    Entidades extraídas de boletines (personas, organismos, empresas, contratos, montos).
    Permite tracking histórico y detección de patrones.
    """
    __tablename__ = "entidades_extraidas"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo = Column(String(50), index=True, nullable=False)  # persona, organismo, empresa, contrato, monto
    nombre_normalizado = Column(String(255), unique=True, index=True, nullable=False)
    nombre_display = Column(String(255), nullable=False)
    variantes = Column(JSON, nullable=True)  # ["Juan Perez", "PEREZ, Juan", "J. Pérez"]
    
    # Estadísticas de apariciones
    primera_aparicion = Column(Date, nullable=True)
    ultima_aparicion = Column(Date, nullable=True)
    total_menciones = Column(Integer, default=0)
    
    # Metadata adicional
    metadata_extra = Column(JSON, nullable=True)  # Para info específica por tipo
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relaciones
    menciones = relationship("MencionEntidad", back_populates="entidad", cascade="all, delete-orphan")
    relaciones_origen = relationship("RelacionEntidad",
        foreign_keys="RelacionEntidad.entidad_origen_id", 
        back_populates="origen",
        cascade="all, delete-orphan")
    relaciones_destino = relationship("RelacionEntidad",
        foreign_keys="RelacionEntidad.entidad_destino_id",
        back_populates="destino",
        cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_entidad_tipo_nombre', 'tipo', 'nombre_normalizado'),
    )
    
    def __repr__(self):
        return f"<EntidadExtraida(tipo={self.tipo}, nombre={self.nombre_normalizado})>"


class MencionEntidad(Base):
    """
    Cada aparición de una entidad en un boletín específico.
    Permite construir timeline de actividad.
    """
    __tablename__ = "menciones_entidades"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entidad_id = Column(Integer, ForeignKey("entidades_extraidas.id"), index=True, nullable=False)
    boletin_id = Column(Integer, ForeignKey("boletines.id"), index=True, nullable=False)
    
    # Contexto de la mención
    fragmento = Column(Text, nullable=False)  # Contexto donde aparece (max 500 chars)
    pagina = Column(Integer, nullable=True)
    confianza = Column(Float, default=1.0)  # Score de confianza en la extracción (0-1)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relaciones
    entidad = relationship("EntidadExtraida", back_populates="menciones")
    boletin = relationship("Boletin")
    
    # Índices
    __table_args__ = (
        Index('idx_mencion_entidad_boletin', 'entidad_id', 'boletin_id'),
        Index('idx_mencion_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<MencionEntidad(entidad_id={self.entidad_id}, boletin_id={self.boletin_id})>"


class RelacionEntidad(Base):
    """
    Relación detectada entre dos entidades (ej: Organismo contrata Empresa).
    Permite análisis de redes y detección de patrones sospechosos.
    """
    __tablename__ = "relaciones_entidades"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entidad_origen_id = Column(Integer, ForeignKey("entidades_extraidas.id"), index=True, nullable=False)
    entidad_destino_id = Column(Integer, ForeignKey("entidades_extraidas.id"), index=True, nullable=False)
    
    # Tipo de relación
    tipo_relacion = Column(String(100), index=True, nullable=False)  
    # Tipos: contrata, designa, recibe_subsidio, firma, adjudica, transfiere
    
    # Contexto de la relación
    boletin_id = Column(Integer, ForeignKey("boletines.id"), nullable=False)
    fecha_relacion = Column(Date, nullable=False, index=True)
    contexto = Column(Text, nullable=True)  # Fragmento donde se detectó la relación
    confianza = Column(Float, default=1.0)  # Score de confianza (0-1)
    
    # Metadata adicional
    metadata_extra = Column(JSON, nullable=True)  # ej: {"monto": 150000, "tipo_contrato": "licitacion"}
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relaciones
    origen = relationship("EntidadExtraida", foreign_keys=[entidad_origen_id], back_populates="relaciones_origen")
    destino = relationship("EntidadExtraida", foreign_keys=[entidad_destino_id], back_populates="relaciones_destino")
    boletin = relationship("Boletin")
    
    # Índices
    __table_args__ = (
        Index('idx_relacion_origen_destino', 'entidad_origen_id', 'entidad_destino_id'),
        Index('idx_relacion_tipo_fecha', 'tipo_relacion', 'fecha_relacion'),
        Index('idx_relacion_boletin', 'boletin_id'),
    )
    
    def __repr__(self):
        return f"<RelacionEntidad(origen={self.entidad_origen_id}, tipo={self.tipo_relacion}, destino={self.entidad_destino_id})>"


# =============================================================================
# COMPLIANCE SYSTEM - CHECKS LEGALES
# =============================================================================

class ComplianceCheckStatus(str, Enum):
    """Estados posibles de un check de compliance"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    UNKNOWN = "unknown"

class ComplianceCheckPriority(str, Enum):
    """Prioridad de checks de compliance"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComplianceCheck(Base):
    """
    Definición de checks de compliance basados en obligaciones legales.
    Cada check representa una obligación de transparencia/publicación.
    """
    __tablename__ = "compliance_checks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identificación
    check_code = Column(String(100), unique=True, index=True, nullable=False)  # RF_25917_PRESUPUESTO_ANUAL
    check_name = Column(String(255), nullable=False)  # "Presupuesto Anual Publicado"
    description = Column(Text, nullable=False)  # Descripción legible del check
    
    # Base legal
    legal_basis = Column(String(255), nullable=False)  # "Ley 25.917 Art. 7 + Ley 10.471"
    legal_text = Column(Text, nullable=True)  # Texto completo del artículo
    legal_url = Column(String(500), nullable=True)  # URL al texto legal
    
    # Obligación
    obligation_summary = Column(Text, nullable=False)  # Resumen de qué debe publicarse
    frequency = Column(String(50), nullable=True)  # anual, trimestral, semestral
    rezago_permitido = Column(Integer, nullable=True)  # Rezago en días/trimestres permitido
    
    # Configuración del check
    priority = Column(String(20), nullable=False, index=True)  # critical, high, medium, low
    weight = Column(Float, default=1.0)  # Peso para scoring ponderado
    category = Column(String(100), nullable=True, index=True)  # presupuesto, deuda, empleo, etc.
    
    # Validación
    validation_rules = Column(JSON, nullable=True)  # Reglas de validación específicas
    expected_sources = Column(JSON, nullable=True)  # URLs esperadas donde buscar evidencia
    
    # Estado
    is_active = Column(Boolean, default=True, index=True)
    
    # Metadata
    citizen_explanation = Column(Text, nullable=True)  # Explicación en lenguaje simple
    auditor_notes = Column(Text, nullable=True)  # Notas técnicas para auditores
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relaciones
    check_results = relationship("CheckResult", back_populates="check", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_check_priority_active', 'priority', 'is_active'),
        Index('idx_check_category', 'category'),
    )
    
    def __repr__(self):
        return f"<ComplianceCheck(code={self.check_code}, priority={self.priority})>"


class CheckResult(Base):
    """
    Resultado de ejecutar un compliance check en un período específico.
    """
    __tablename__ = "check_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    check_id = Column(Integer, ForeignKey("compliance_checks.id"), index=True, nullable=False)
    jurisdiccion_id = Column(Integer, ForeignKey("jurisdicciones.id"), index=True, nullable=True)
    
    # Resultado
    status = Column(String(20), nullable=False, index=True)  # pass, warn, fail, unknown
    score = Column(Float, nullable=True)  # 0.0 a 1.0 (PASS=1, WARN=0.5, FAIL=0)
    
    # Período evaluado
    evaluation_date = Column(Date, nullable=False, index=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    
    # Detalles del resultado
    summary = Column(Text, nullable=False)  # Resumen del resultado
    reason = Column(Text, nullable=True)  # Razón del PASS/WARN/FAIL
    remediation = Column(Text, nullable=True)  # Qué se debe hacer para cumplir
    
    # Metadata
    evaluation_metadata = Column(JSON, nullable=True)  # Datos adicionales de la evaluación
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relaciones
    check = relationship("ComplianceCheck", back_populates="check_results")
    jurisdiccion = relationship("Jurisdiccion")
    evidences = relationship("Evidence", back_populates="check_result", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_result_check_date', 'check_id', 'evaluation_date'),
        Index('idx_result_status_date', 'status', 'evaluation_date'),
        Index('idx_result_jurisdiccion', 'jurisdiccion_id'),
    )
    
    def __repr__(self):
        return f"<CheckResult(check_id={self.check_id}, status={self.status}, date={self.evaluation_date})>"


class Evidence(Base):
    """
    Evidencia que respalda el resultado de un check de compliance.
    Permite trazabilidad y reproducibilidad de las evaluaciones.
    """
    __tablename__ = "evidences"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    check_result_id = Column(Integer, ForeignKey("check_results.id"), index=True, nullable=False)
    
    # Fuente de la evidencia
    source_url = Column(String(1000), nullable=False)  # URL del documento/página
    source_type = Column(String(50), nullable=False)  # pdf, html_table, api_response, download
    
    # Snapshot para reproducibilidad
    snapshot_hash = Column(String(64), nullable=True)  # SHA256 del contenido
    snapshot_path = Column(String(500), nullable=True)  # Path al archivo guardado
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Contenido relevante
    relevant_fragment = Column(Text, nullable=True)  # Fragmento relevante del documento
    extracted_data = Column(JSON, nullable=True)  # Datos extraídos estructurados
    
    # Metadata
    artifact_metadata = Column(JSON, nullable=True)  # file_size, num_pages, etc.
    
    # Validation status
    is_valid = Column(Boolean, default=True)  # Si la evidencia es válida
    validation_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relaciones
    check_result = relationship("CheckResult", back_populates="evidences")
    
    # Índices
    __table_args__ = (
        Index('idx_evidence_result', 'check_result_id'),
        Index('idx_evidence_captured', 'captured_at'),
        Index('idx_evidence_hash', 'snapshot_hash'),
    )
    
    def __repr__(self):
        return f"<Evidence(result_id={self.check_result_id}, source={self.source_url[:50]})>"


class RequiredDocument(Base):
    """
    Documentos requeridos por ley para cada jurisdicción.
    Permite tracking de qué documentos deben existir vs cuáles tenemos.
    """
    __tablename__ = "required_documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    check_id = Column(Integer, ForeignKey("compliance_checks.id"), index=True, nullable=True)
    jurisdiccion_id = Column(Integer, ForeignKey("jurisdicciones.id"), index=True, nullable=True)
    
    # Identificación del documento
    document_type = Column(String(100), nullable=False, index=True)  # presupuesto_anual, ejecucion_Q1, etc.
    document_name = Column(String(255), nullable=False)  # "Presupuesto 2025"
    period = Column(String(50), nullable=True)  # 2025, 2025-Q1, 2025-06, etc.
    
    # Fuente esperada
    expected_url = Column(String(1000), nullable=True)  # URL donde debería estar
    expected_format = Column(String(50), nullable=False)  # pdf, csv, txt, xlsx, html
    
    # Estado del documento
    status = Column(String(50), nullable=False, default='missing', index=True)  
    # missing: no encontrado/no descargado
    # downloaded: descargado pero no procesado
    # processed: descargado y procesado con RAG
    # failed: intento de descarga/procesamiento falló
    
    # Tracking de archivo local
    local_path = Column(String(500), nullable=True)  # Path al archivo descargado
    file_hash = Column(String(64), nullable=True)  # SHA256 del archivo
    file_size_bytes = Column(Integer, nullable=True)
    
    # Metadata de procesamiento
    downloaded_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    last_checked = Column(DateTime, nullable=True)
    
    # RAG/Embedding status
    indexed_in_rag = Column(Boolean, default=False)
    embedding_model = Column(String(100), nullable=True)
    num_chunks = Column(Integer, nullable=True)
    
    # Metadata adicional
    metadata_json = Column(JSON, nullable=True)  # Metadata extraída del documento
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relaciones
    check = relationship("ComplianceCheck")
    jurisdiccion = relationship("Jurisdiccion")
    
    # Índices
    __table_args__ = (
        Index('idx_required_doc_check_jurisdiccion', 'check_id', 'jurisdiccion_id'),
        Index('idx_required_doc_status', 'status'),
        Index('idx_required_doc_period', 'period'),
    )
    
    def __repr__(self):
        return f"<RequiredDocument(name={self.document_name}, status={self.status})>"


# =============================================================================
# CHUNK RECORDS - EPIC 3: FEATURE ENGINEERING
# =============================================================================

class ChunkRecord(Base):
    """
    Registro persistente de chunks de texto con metadata enriquecida.
    
    Cada chunk es una porción de un documento (boletin) que ha sido:
    - Limpiado y normalizado
    - Dividido con estrategia recursiva
    - Enriquecido con metadata (section_type, entities, etc.)
    - Indexado con embeddings
    
    Epic 3 (Feature Engineering): Provee metadata rica para búsqueda filtrada.
    Epic 4 (Indexación): Registra información de embedding.
    Epic 5 (Retrieval): Permite búsqueda por metadata.
    """
    __tablename__ = "chunk_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Referencias al documento
    document_id = Column(String(255), index=True, nullable=False)  # ID único del documento
    boletin_id = Column(Integer, ForeignKey("boletines.id"), nullable=True, index=True)
    
    # Identidad del chunk
    chunk_index = Column(Integer, nullable=False)  # Índice dentro del documento (0-based)
    chunk_hash = Column(String(64), index=True, nullable=True)  # SHA256 del texto del chunk
    
    # Contenido
    text = Column(Text, nullable=False)  # Texto del chunk
    num_chars = Column(Integer, nullable=False)  # Número de caracteres
    start_char = Column(Integer, nullable=True)  # Posición inicial en el documento original
    end_char = Column(Integer, nullable=True)  # Posición final en el documento original
    
    # Metadata enriquecida (Epic 3: Feature Engineering)
    section_type = Column(String(50), nullable=True, index=True)  
    # Valores: licitacion, decreto, resolucion, subsidio, presupuesto, nombramiento, general, unknown
    
    topic = Column(String(100), nullable=True)  # Tema principal del chunk
    language = Column(String(10), default="es")  # Idioma (default: español)
    has_tables = Column(Boolean, default=False)  # Contiene tablas
    has_amounts = Column(Boolean, default=False, index=True)  # Contiene montos
    entities_json = Column(JSON, nullable=True)  # Entidades detectadas en el chunk
    # Formato: {"personas": [...], "organismos": [...], "empresas": [...], "montos": [...]}
    
    # Embedding tracking (Epic 4: Indexación + Epic 7.3: Deuda Técnica)
    embedding_model = Column(String(100), nullable=True)  # ej: "gemini-embedding-001"
    embedding_dimensions = Column(Integer, nullable=True)  # ej: 3072
    indexed_at = Column(DateTime, nullable=True, index=True)  # Cuándo se indexó
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    boletin = relationship("Boletin", lazy="select")
    
    # Índices para búsqueda eficiente
    __table_args__ = (
        Index('idx_chunk_document_index', 'document_id', 'chunk_index', unique=True),
        Index('idx_chunk_section', 'section_type'),
        Index('idx_chunk_hash', 'chunk_hash'),
        Index('idx_chunk_boletin', 'boletin_id'),
        Index('idx_chunk_has_amounts', 'has_amounts'),
        Index('idx_chunk_indexed', 'indexed_at'),
    )
    
    def __repr__(self):
        return f"<ChunkRecord(document_id={self.document_id}, chunk_index={self.chunk_index}, section_type={self.section_type})>"
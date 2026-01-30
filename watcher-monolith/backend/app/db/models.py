"""
Modelos de base de datos - Versión completa con historial acumulativo
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Float, Date, Boolean, Index
from sqlalchemy.orm import relationship
from .database import Base

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

    # Relaciones
    analisis = relationship("Analisis", back_populates="boletin", cascade="all, delete-orphan")
    ejecuciones = relationship("EjecucionPresupuestaria", back_populates="boletin", cascade="all, delete-orphan")

class Analisis(Base):
    """Modelo para almacenar análisis de fragmentos."""
    __tablename__ = "analisis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    boletin_id = Column(Integer, ForeignKey("boletines.id"))
    fragmento = Column(Text)
    categoria = Column(String)
    entidad_beneficiaria = Column(String)
    monto_estimado = Column(String, nullable=True)
    monto_numerico = Column(Float, nullable=True)  # Monto parseado numéricamente
    riesgo = Column(String)  # ALTO, MEDIO, BAJO
    tipo_curro = Column(String)
    accion_sugerida = Column(Text)
    datos_extra = Column(JSON, nullable=True)  # Para datos adicionales
    created_at = Column(DateTime, default=datetime.utcnow)

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
"""
🧪 DS Lab - Endpoints para ejecuciones de análisis
"""
import asyncio
from datetime import date, datetime
from typing import Any

from app.db.models import (
    AnalysisConfig,
    AnalysisExecution,
    AnalysisResult,
    BoletinDocument,
    RedFlag,
)
from app.db.sync_session import get_sync_db
from app.schemas.dslab import (
    AnalysisExecutionCreate,
    AnalysisExecutionResponse,
    ExecutionProgress,
    ExecutionSummary,
)
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

router = APIRouter()

# Estado global para tracking (en producción usar Redis)
execution_progress: dict[int, dict[str, Any]] = {}


def get_documents_for_execution(
    db: Session,
    start_date: date,
    end_date: date,
    sections: list[int]
) -> list[BoletinDocument]:
    """Obtener documentos para analizar en un rango de fechas"""
    query = db.query(BoletinDocument).filter(
        and_(
            BoletinDocument.year >= start_date.year,
            BoletinDocument.year <= end_date.year
        )
    )

    documents = []
    for doc in query.all():
        doc_date = date(doc.year, doc.month, doc.day)
        if start_date <= doc_date <= end_date and doc.section in sections:
            documents.append(doc)

    return documents


async def run_analysis_task(
    execution_id: int,
    config_id: int,
    documents: list[int],  # IDs de documentos
    db_path: str
):
    """
    Tarea de análisis en background con análisis real
    Nota: En producción esto debería usar Celery o similar
    """
    from app.services.dslab_analyzer import DSLabAnalyzer
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Crear nueva sesión para el background task
    engine = create_engine(f"sqlite:///{db_path}")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        execution = db.query(AnalysisExecution).filter(
            AnalysisExecution.id == execution_id
        ).first()

        if not execution:
            return

        # Obtener configuración
        config = db.query(AnalysisConfig).filter(
            AnalysisConfig.id == config_id
        ).first()

        if not config:
            execution.status = 'failed'
            execution.error_message = "Configuración no encontrada"
            db.commit()
            return

        # Inicializar analizador
        analyzer = DSLabAnalyzer(config.parameters)

        execution.status = 'running'
        db.commit()

        # Inicializar progreso
        execution_progress[execution_id] = {
            "status": "running",
            "processed": 0,
            "failed": 0,
            "total": len(documents),
            "current_document": None
        }

        # Procesar cada documento
        for i, doc_id in enumerate(documents):
            try:
                document = db.query(BoletinDocument).filter(
                    BoletinDocument.id == doc_id
                ).first()

                if not document:
                    execution.failed_documents += 1
                    db.commit()
                    continue

                # Actualizar progreso
                execution_progress[execution_id]["current_document"] = document.filename
                execution_progress[execution_id]["processed"] = i + 1

                # Marcar documento como analizando
                document.analysis_status = 'analyzing'
                db.commit()

                # ANÁLISIS REAL
                analysis_result = analyzer.analyze_document(document.file_path)

                # Crear resultado en BD
                result = AnalysisResult(
                    document_id=doc_id,
                    execution_id=execution_id,
                    config_id=config_id,
                    transparency_score=analysis_result.get('transparency_score'),
                    risk_level=analysis_result.get('risk_level'),
                    anomaly_score=analysis_result.get('anomaly_score'),
                    extracted_entities=analysis_result.get('extracted_entities'),
                    red_flags=analysis_result.get('red_flags'),
                    num_red_flags=analysis_result.get('num_red_flags', 0),
                    ml_predictions=analysis_result.get('ml_predictions'),
                    extracted_text_sample=analysis_result.get('extracted_text_sample'),
                    processing_time_seconds=analysis_result.get('processing_time_seconds')
                )

                db.add(result)
                db.flush()  # Para obtener el ID del resultado

                # Crear red flags individuales
                for flag_data in analysis_result.get('red_flags', []):
                    red_flag = RedFlag(
                        result_id=result.id,
                        document_id=doc_id,
                        flag_type=flag_data.get('type'),
                        severity=flag_data.get('severity'),
                        category=flag_data.get('category'),
                        title=flag_data.get('title'),
                        description=flag_data.get('description'),
                        evidence=flag_data.get('evidence'),
                        confidence_score=flag_data.get('confidence_score')
                    )
                    db.add(red_flag)

                # Actualizar documento
                document.analysis_status = 'completed'
                document.last_analyzed = datetime.utcnow()
                document.num_pages = analysis_result.get('metadata', {}).get('num_pages')

                execution.processed_documents += 1
                db.commit()

                print(f"✓ Analizado: {document.filename} - Score: {analysis_result.get('transparency_score'):.1f}, Flags: {analysis_result.get('num_red_flags')}")

                # Pequeña pausa para no sobrecargar
                await asyncio.sleep(0.05)

            except Exception as e:
                print(f"Error procesando documento {doc_id}: {e}")
                import traceback
                traceback.print_exc()

                document.analysis_status = 'failed'
                execution.failed_documents += 1
                db.commit()
                continue

        # Finalizar ejecución
        execution.status = 'completed'
        execution.completed_at = datetime.utcnow()
        execution_progress[execution_id]["status"] = "completed"
        db.commit()

        print(f"✅ Ejecución {execution_id} completada: {execution.processed_documents}/{execution.total_documents} exitosos")

    except Exception as e:
        print(f"Error crítico en ejecución {execution_id}: {e}")
        import traceback
        traceback.print_exc()

        execution.status = 'failed'
        execution.error_message = str(e)
        execution_progress[execution_id]["status"] = "failed"
        db.commit()

    finally:
        db.close()


@router.post("/analysis/executions", response_model=AnalysisExecutionResponse, status_code=201)
async def create_execution(
    execution_data: AnalysisExecutionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_sync_db)
):
    """
    Crear y iniciar una nueva ejecución de análisis
    """
    # Verificar que la config existe
    config = db.query(AnalysisConfig).filter(
        AnalysisConfig.id == execution_data.config_id
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")

    # Obtener documentos a analizar
    documents = get_documents_for_execution(
        db,
        execution_data.start_date,
        execution_data.end_date,
        execution_data.sections or [1, 2, 3, 4, 5]
    )

    if not documents:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron documentos para el rango especificado"
        )

    # Crear ejecución
    execution = AnalysisExecution(
        execution_name=execution_data.execution_name or f"Análisis {execution_data.start_date} - {execution_data.end_date}",
        config_id=execution_data.config_id,
        status='pending',
        start_date=execution_data.start_date,
        end_date=execution_data.end_date,
        total_documents=len(documents),
        processed_documents=0,
        failed_documents=0
    )

    db.add(execution)
    db.commit()
    db.refresh(execution)

    # Iniciar análisis en background
    # Nota: Pasar IDs en lugar de objetos ORM
    document_ids = [d.id for d in documents]

    # Obtener path de la DB para el background task
    from app.core.config import settings
    db_path = f"{settings.BASE_DIR}/sqlite.db"

    # TODO: Esto debería ser async pero FastAPI BackgroundTasks no soporta async directamente
    # En producción usar Celery
    background_tasks.add_task(
        run_analysis_task,
        execution.id,
        config.id,
        document_ids,
        db_path
    )

    return execution


@router.get("/analysis/executions", response_model=list[AnalysisExecutionResponse])
async def list_executions(
    status: str | None = None,
    config_id: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_sync_db)
):
    """
    Listar ejecuciones
    """
    query = db.query(AnalysisExecution)

    if status:
        query = query.filter(AnalysisExecution.status == status)

    if config_id:
        query = query.filter(AnalysisExecution.config_id == config_id)

    executions = query.order_by(
        desc(AnalysisExecution.started_at)
    ).offset(skip).limit(limit).all()

    return executions


@router.get("/analysis/executions/{execution_id}", response_model=AnalysisExecutionResponse)
async def get_execution(
    execution_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Obtener detalle de una ejecución
    """
    execution = db.query(AnalysisExecution).filter(
        AnalysisExecution.id == execution_id
    ).first()

    if not execution:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")

    return execution


@router.get("/analysis/executions/{execution_id}/progress", response_model=ExecutionProgress)
async def get_execution_progress(
    execution_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Obtener progreso en tiempo real de una ejecución
    """
    execution = db.query(AnalysisExecution).filter(
        AnalysisExecution.id == execution_id
    ).first()

    if not execution:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")

    # Obtener progreso del estado global
    progress_data = execution_progress.get(execution_id, {})

    # Calcular progreso
    progress_percentage = 0.0
    if execution.total_documents > 0:
        progress_percentage = (execution.processed_documents / execution.total_documents) * 100

    # Estimar tiempo restante
    estimated_time = None
    if execution.status == 'running' and execution.processed_documents > 0:
        elapsed = (datetime.utcnow() - execution.started_at).total_seconds()
        rate = execution.processed_documents / elapsed
        remaining = execution.total_documents - execution.processed_documents
        if rate > 0:
            estimated_time = int(remaining / rate)

    return ExecutionProgress(
        execution_id=execution_id,
        status=execution.status,
        total_documents=execution.total_documents,
        processed_documents=execution.processed_documents,
        failed_documents=execution.failed_documents,
        progress_percentage=round(progress_percentage, 2),
        estimated_time_remaining_seconds=estimated_time,
        current_document=progress_data.get("current_document")
    )


@router.get("/analysis/executions/{execution_id}/summary", response_model=ExecutionSummary)
async def get_execution_summary(
    execution_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Obtener resumen de resultados de una ejecución
    """
    execution = db.query(AnalysisExecution).filter(
        AnalysisExecution.id == execution_id
    ).first()

    if not execution:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")

    config = db.query(AnalysisConfig).filter(
        AnalysisConfig.id == execution.config_id
    ).first()

    # Calcular métricas agregadas
    results = db.query(AnalysisResult).filter(
        AnalysisResult.execution_id == execution_id
    ).all()

    # Score promedio
    avg_score = None
    if results:
        scores = [r.transparency_score for r in results if r.transparency_score is not None]
        if scores:
            avg_score = sum(scores) / len(scores)

    # Distribución de riesgo
    risk_dist = db.query(
        AnalysisResult.risk_level,
        func.count(AnalysisResult.id)
    ).filter(
        AnalysisResult.execution_id == execution_id
    ).group_by(AnalysisResult.risk_level).all()

    risk_distribution = {level: count for level, count in risk_dist if level}

    # Total red flags
    total_flags = db.query(
        func.sum(AnalysisResult.num_red_flags)
    ).filter(
        AnalysisResult.execution_id == execution_id
    ).scalar() or 0

    # Red flags por severidad
    severity_dist = db.query(
        RedFlag.severity,
        func.count(RedFlag.id)
    ).join(
        AnalysisResult,
        RedFlag.result_id == AnalysisResult.id
    ).filter(
        AnalysisResult.execution_id == execution_id
    ).group_by(RedFlag.severity).all()

    red_flags_by_severity = {sev: count for sev, count in severity_dist}

    # Duración
    duration = None
    if execution.completed_at:
        duration = (execution.completed_at - execution.started_at).total_seconds()

    return ExecutionSummary(
        execution_id=execution_id,
        execution_name=execution.execution_name,
        config_name=config.config_name,
        config_version=config.version,
        status=execution.status,
        total_documents=execution.total_documents,
        processed_documents=execution.processed_documents,
        failed_documents=execution.failed_documents,
        avg_transparency_score=round(avg_score, 2) if avg_score else None,
        risk_distribution=risk_distribution,
        total_red_flags=int(total_flags),
        red_flags_by_severity=red_flags_by_severity,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        duration_seconds=round(duration, 2) if duration else None
    )


@router.post("/analysis/executions/{execution_id}/cancel")
async def cancel_execution(
    execution_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Cancelar una ejecución en progreso
    """
    execution = db.query(AnalysisExecution).filter(
        AnalysisExecution.id == execution_id
    ).first()

    if not execution:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")

    if execution.status not in ['pending', 'running']:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cancelar una ejecución en estado '{execution.status}'"
        )

    execution.status = 'cancelled'
    execution.completed_at = datetime.utcnow()

    # Actualizar progreso global
    if execution_id in execution_progress:
        execution_progress[execution_id]["status"] = "cancelled"

    db.commit()

    return {
        "message": "Ejecución cancelada",
        "execution_id": execution_id,
        "processed_documents": execution.processed_documents,
        "remaining_documents": execution.total_documents - execution.processed_documents
    }


@router.get("/analysis/executions/{execution_id}/results")
async def get_execution_results(
    execution_id: int,
    risk_level: str | None = None,
    min_red_flags: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_sync_db)
):
    """
    Obtener resultados de una ejecución con filtros
    """
    execution = db.query(AnalysisExecution).filter(
        AnalysisExecution.id == execution_id
    ).first()

    if not execution:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")

    query = db.query(AnalysisResult).filter(
        AnalysisResult.execution_id == execution_id
    )

    if risk_level:
        query = query.filter(AnalysisResult.risk_level == risk_level)

    if min_red_flags is not None:
        query = query.filter(AnalysisResult.num_red_flags >= min_red_flags)

    results = query.order_by(
        desc(AnalysisResult.num_red_flags),
        desc(AnalysisResult.transparency_score)
    ).offset(skip).limit(limit).all()

    return {
        "execution_id": execution_id,
        "total_results": query.count(),
        "results": results
    }


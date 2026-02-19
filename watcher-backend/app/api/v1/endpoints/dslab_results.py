"""
🧪 DS Lab - Endpoints para resultados y comparaciones
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional, Dict, Any

from app.db.sync_session import get_sync_db
from app.db.models import (
    AnalysisResult, AnalysisExecution, AnalysisConfig,
    BoletinDocument, RedFlag, AnalysisComparison
)
from app.schemas.dslab import (
    AnalysisResultResponse,
    RedFlagResponse,
    RedFlagStats,
    AnalysisComparisonCreate,
    AnalysisComparisonResponse
)

router = APIRouter()


@router.get("/analysis/results")
async def list_results(
    execution_id: Optional[int] = None,
    document_id: Optional[int] = None,
    risk_level: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    min_red_flags: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_sync_db)
):
    """
    Listar resultados con filtros avanzados
    """
    query = db.query(AnalysisResult)
    
    if execution_id:
        query = query.filter(AnalysisResult.execution_id == execution_id)
    
    if document_id:
        query = query.filter(AnalysisResult.document_id == document_id)
    
    if risk_level:
        query = query.filter(AnalysisResult.risk_level == risk_level)
    
    if min_score is not None:
        query = query.filter(AnalysisResult.transparency_score >= min_score)
    
    if max_score is not None:
        query = query.filter(AnalysisResult.transparency_score <= max_score)
    
    if min_red_flags is not None:
        query = query.filter(AnalysisResult.num_red_flags >= min_red_flags)
    
    total = query.count()
    
    results = query.order_by(
        desc(AnalysisResult.num_red_flags),
        AnalysisResult.transparency_score
    ).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "results": results
    }


@router.get("/analysis/results/{result_id}", response_model=AnalysisResultResponse)
async def get_result(
    result_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Obtener un resultado específico
    """
    result = db.query(AnalysisResult).filter(
        AnalysisResult.id == result_id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")
    
    return result


@router.get("/analysis/results/{result_id}/full")
async def get_result_with_context(
    result_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Obtener resultado con documento, config y ejecución
    """
    result = db.query(AnalysisResult).filter(
        AnalysisResult.id == result_id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")
    
    document = db.query(BoletinDocument).filter(
        BoletinDocument.id == result.document_id
    ).first()
    
    execution = db.query(AnalysisExecution).filter(
        AnalysisExecution.id == result.execution_id
    ).first()
    
    config = db.query(AnalysisConfig).filter(
        AnalysisConfig.id == result.config_id
    ).first()
    
    # Red flags del resultado
    red_flags = db.query(RedFlag).filter(
        RedFlag.result_id == result_id
    ).order_by(desc(RedFlag.severity)).all()
    
    return {
        "result": result,
        "document": document,
        "execution": {
            "id": execution.id,
            "name": execution.execution_name,
            "status": execution.status
        } if execution else None,
        "config": {
            "id": config.id,
            "name": config.config_name,
            "version": config.version
        } if config else None,
        "red_flags": red_flags
    }


@router.get("/red-flags", response_model=List[RedFlagResponse])
async def list_red_flags(
    document_id: Optional[int] = None,
    execution_id: Optional[int] = None,
    severity: Optional[str] = None,
    flag_type: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_sync_db)
):
    """
    Listar red flags con filtros
    """
    query = db.query(RedFlag)
    
    if document_id:
        query = query.filter(RedFlag.document_id == document_id)
    
    if execution_id:
        query = query.join(
            AnalysisResult,
            RedFlag.result_id == AnalysisResult.id
        ).filter(
            AnalysisResult.execution_id == execution_id
        )
    
    if severity:
        query = query.filter(RedFlag.severity == severity)
    
    if flag_type:
        query = query.filter(RedFlag.flag_type == flag_type)
    
    if category:
        query = query.filter(RedFlag.category == category)
    
    flags = query.order_by(
        desc(RedFlag.severity),
        desc(RedFlag.created_at)
    ).offset(skip).limit(limit).all()
    
    return flags


@router.get("/red-flags/stats", response_model=RedFlagStats)
async def get_red_flags_stats(
    execution_id: Optional[int] = None,
    db: Session = Depends(get_sync_db)
):
    """
    Estadísticas de red flags
    """
    query = db.query(RedFlag)
    
    if execution_id:
        query = query.join(
            AnalysisResult,
            RedFlag.result_id == AnalysisResult.id
        ).filter(
            AnalysisResult.execution_id == execution_id
        )
    
    total_flags = query.count()
    
    # Por severidad
    severity_stats = query.with_entities(
        RedFlag.severity,
        func.count(RedFlag.id)
    ).group_by(RedFlag.severity).all()
    
    by_severity = {sev: count for sev, count in severity_stats if sev}
    
    # Por tipo
    type_stats = query.with_entities(
        RedFlag.flag_type,
        func.count(RedFlag.id)
    ).group_by(RedFlag.flag_type).all()
    
    by_type = {ftype: count for ftype, count in type_stats if ftype}
    
    # Por categoría
    category_stats = query.with_entities(
        RedFlag.category,
        func.count(RedFlag.id)
    ).group_by(RedFlag.category).all()
    
    by_category = {cat: count for cat, count in category_stats if cat}
    
    # Top documentos con más flags
    top_docs_query = db.query(
        RedFlag.document_id,
        func.count(RedFlag.id).label('flag_count')
    )
    
    if execution_id:
        top_docs_query = top_docs_query.join(
            AnalysisResult,
            RedFlag.result_id == AnalysisResult.id
        ).filter(
            AnalysisResult.execution_id == execution_id
        )
    
    top_docs = top_docs_query.group_by(
        RedFlag.document_id
    ).order_by(
        desc('flag_count')
    ).limit(10).all()
    
    top_documents = []
    for doc_id, count in top_docs:
        doc = db.query(BoletinDocument).filter(
            BoletinDocument.id == doc_id
        ).first()
        if doc:
            top_documents.append({
                "document_id": doc_id,
                "filename": doc.filename,
                "flag_count": count
            })
    
    return RedFlagStats(
        total_flags=total_flags,
        by_severity=by_severity,
        by_type=by_type,
        by_category=by_category,
        top_documents=top_documents
    )


@router.post("/analysis/comparisons", response_model=AnalysisComparisonResponse, status_code=201)
async def create_comparison(
    comparison: AnalysisComparisonCreate,
    db: Session = Depends(get_sync_db)
):
    """
    Crear una comparación entre dos ejecuciones
    """
    # Verificar que ambas ejecuciones existen
    exec_a = db.query(AnalysisExecution).filter(
        AnalysisExecution.id == comparison.execution_a_id
    ).first()
    
    exec_b = db.query(AnalysisExecution).filter(
        AnalysisExecution.id == comparison.execution_b_id
    ).first()
    
    if not exec_a or not exec_b:
        raise HTTPException(status_code=404, detail="Una o ambas ejecuciones no encontradas")
    
    if exec_a.status != 'completed' or exec_b.status != 'completed':
        raise HTTPException(status_code=400, detail="Ambas ejecuciones deben estar completadas")
    
    # Calcular métricas de comparación
    metrics = calculate_comparison_metrics(db, comparison.execution_a_id, comparison.execution_b_id)
    
    # Crear comparación
    db_comparison = AnalysisComparison(
        name=comparison.name,
        execution_a_id=comparison.execution_a_id,
        execution_b_id=comparison.execution_b_id,
        comparison_metrics=metrics,
        notes=comparison.notes
    )
    
    db.add(db_comparison)
    db.commit()
    db.refresh(db_comparison)
    
    return db_comparison


@router.get("/analysis/comparisons", response_model=List[AnalysisComparisonResponse])
async def list_comparisons(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_sync_db)
):
    """
    Listar comparaciones
    """
    comparisons = db.query(AnalysisComparison).order_by(
        desc(AnalysisComparison.created_at)
    ).offset(skip).limit(limit).all()
    
    return comparisons


@router.get("/analysis/comparisons/{comparison_id}")
async def get_comparison_detail(
    comparison_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Obtener detalle completo de una comparación
    """
    comparison = db.query(AnalysisComparison).filter(
        AnalysisComparison.id == comparison_id
    ).first()
    
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparación no encontrada")
    
    exec_a = db.query(AnalysisExecution).filter(
        AnalysisExecution.id == comparison.execution_a_id
    ).first()
    
    exec_b = db.query(AnalysisExecution).filter(
        AnalysisExecution.id == comparison.execution_b_id
    ).first()
    
    # Obtener métricas detalladas
    detailed_metrics = get_detailed_comparison(db, comparison.execution_a_id, comparison.execution_b_id)
    
    return {
        "comparison": comparison,
        "execution_a": exec_a,
        "execution_b": exec_b,
        "detailed_metrics": detailed_metrics
    }


@router.delete("/analysis/comparisons/{comparison_id}")
async def delete_comparison(
    comparison_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Eliminar una comparación
    """
    comparison = db.query(AnalysisComparison).filter(
        AnalysisComparison.id == comparison_id
    ).first()
    
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparación no encontrada")
    
    db.delete(comparison)
    db.commit()
    
    return {"message": "Comparación eliminada", "comparison_id": comparison_id}


def calculate_comparison_metrics(db: Session, exec_a_id: int, exec_b_id: int) -> Dict[str, Any]:
    """
    Calcular métricas de comparación entre dos ejecuciones
    """
    # Obtener resultados de ambas ejecuciones para documentos comunes
    results_a = db.query(AnalysisResult).filter(
        AnalysisResult.execution_id == exec_a_id
    ).all()
    
    results_b = db.query(AnalysisResult).filter(
        AnalysisResult.execution_id == exec_b_id
    ).all()
    
    # Crear mapas doc_id -> resultado
    map_a = {r.document_id: r for r in results_a}
    map_b = {r.document_id: r for r in results_b}
    
    # Documentos comunes
    common_docs = set(map_a.keys()) & set(map_b.keys())
    
    if not common_docs:
        return {
            "common_documents": 0,
            "score_diff_avg": 0,
            "new_red_flags": 0,
            "resolved_flags": 0,
            "documents_changed_risk": 0
        }
    
    # Diferencias de score
    score_diffs = []
    risk_changes = 0
    
    for doc_id in common_docs:
        ra = map_a[doc_id]
        rb = map_b[doc_id]
        
        if ra.transparency_score and rb.transparency_score:
            score_diffs.append(rb.transparency_score - ra.transparency_score)
        
        if ra.risk_level != rb.risk_level:
            risk_changes += 1
    
    avg_score_diff = sum(score_diffs) / len(score_diffs) if score_diffs else 0
    
    # Red flags nuevas vs resueltas
    flags_a = db.query(func.sum(AnalysisResult.num_red_flags)).filter(
        AnalysisResult.execution_id == exec_a_id
    ).scalar() or 0
    
    flags_b = db.query(func.sum(AnalysisResult.num_red_flags)).filter(
        AnalysisResult.execution_id == exec_b_id
    ).scalar() or 0
    
    flag_diff = int(flags_b - flags_a)
    
    return {
        "common_documents": len(common_docs),
        "score_diff_avg": round(avg_score_diff, 2),
        "new_red_flags": max(0, flag_diff),
        "resolved_flags": max(0, -flag_diff),
        "documents_changed_risk": risk_changes
    }


def get_detailed_comparison(db: Session, exec_a_id: int, exec_b_id: int) -> Dict[str, Any]:
    """
    Obtener comparación detallada con distribuciones
    """
    # Obtener resultados
    results_a = db.query(AnalysisResult).filter(
        AnalysisResult.execution_id == exec_a_id
    ).all()
    
    results_b = db.query(AnalysisResult).filter(
        AnalysisResult.execution_id == exec_b_id
    ).all()
    
    map_a = {r.document_id: r for r in results_a}
    map_b = {r.document_id: r for r in results_b}
    
    common_docs = set(map_a.keys()) & set(map_b.keys())
    
    # Cambios de riesgo detallados
    risk_changes = {}
    documents_improved = 0
    documents_worsened = 0
    
    for doc_id in common_docs:
        ra = map_a[doc_id]
        rb = map_b[doc_id]
        
        # Comparar scores
        if ra.transparency_score and rb.transparency_score:
            if rb.transparency_score > ra.transparency_score:
                documents_improved += 1
            elif rb.transparency_score < ra.transparency_score:
                documents_worsened += 1
        
        # Rastrear cambios de riesgo
        if ra.risk_level and rb.risk_level and ra.risk_level != rb.risk_level:
            if ra.risk_level not in risk_changes:
                risk_changes[ra.risk_level] = {}
            
            target_risk = rb.risk_level
            if target_risk not in risk_changes[ra.risk_level]:
                risk_changes[ra.risk_level][target_risk] = 0
            
            risk_changes[ra.risk_level][target_risk] += 1
    
    return {
        "documents_improved": documents_improved,
        "documents_worsened": documents_worsened,
        "documents_unchanged": len(common_docs) - documents_improved - documents_worsened,
        "risk_changes": risk_changes
    }


"""
Dashboard endpoint with real DS Lab data
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, List, Any

from app.db.sync_session import get_sync_db
from app.db.models import (
    BoletinDocument,
    AnalysisExecution,
    AnalysisResult,
    RedFlag,
    AnalysisConfig
)

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_sync_db)
) -> Dict[str, Any]:
    """
    Get comprehensive dashboard statistics from DS Lab data
    """
    try:
        # Documentos totales
        total_documents = db.query(func.count(BoletinDocument.id)).scalar() or 0
        
        # Documentos analizados
        analyzed_documents = db.query(func.count(BoletinDocument.id)).filter(
            BoletinDocument.analysis_status == 'completed'
        ).scalar() or 0
        
        # Documentos pendientes
        pending_documents = db.query(func.count(BoletinDocument.id)).filter(
            BoletinDocument.analysis_status == 'pending'
        ).scalar() or 0
        
        # Total de ejecuciones
        total_executions = db.query(func.count(AnalysisExecution.id)).scalar() or 0
        
        # Ejecuciones completadas
        completed_executions = db.query(func.count(AnalysisExecution.id)).filter(
            AnalysisExecution.status == 'completed'
        ).scalar() or 0
        
        # Total red flags
        total_red_flags = db.query(func.count(RedFlag.id)).scalar() or 0
        
        # Red flags por severidad
        severity_stats = db.query(
            RedFlag.severity,
            func.count(RedFlag.id)
        ).group_by(RedFlag.severity).all()
        
        red_flags_by_severity = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }
        for severity, count in severity_stats:
            if severity in red_flags_by_severity:
                red_flags_by_severity[severity] = count
        
        # Score promedio de transparencia
        avg_transparency = db.query(
            func.avg(AnalysisResult.transparency_score)
        ).scalar()
        
        # Distribución de riesgo
        risk_distribution = db.query(
            AnalysisResult.risk_level,
            func.count(AnalysisResult.id)
        ).group_by(AnalysisResult.risk_level).all()
        
        risk_stats = {
            'high': 0,
            'medium': 0,
            'low': 0
        }
        for risk, count in risk_distribution:
            if risk in risk_stats:
                risk_stats[risk] = count
        
        # Documentos por mes
        documents_by_month = db.query(
            BoletinDocument.year,
            BoletinDocument.month,
            func.count(BoletinDocument.id)
        ).group_by(
            BoletinDocument.year,
            BoletinDocument.month
        ).order_by(
            BoletinDocument.year,
            BoletinDocument.month
        ).all()
        
        monthly_data = []
        for year, month, count in documents_by_month:
            monthly_data.append({
                'period': f"{year}-{month:02d}",
                'count': count,
                'year': year,
                'month': month
            })
        
        # Últimas ejecuciones
        recent_executions = db.query(AnalysisExecution).filter(
            AnalysisExecution.status == 'completed'
        ).order_by(desc(AnalysisExecution.completed_at)).limit(5).all()
        
        executions_list = []
        for ex in recent_executions:
            executions_list.append({
                'id': ex.id,
                'name': ex.execution_name,
                'status': ex.status,
                'total_documents': ex.total_documents,
                'processed_documents': ex.processed_documents,
                'started_at': ex.started_at.isoformat() if ex.started_at else None,
                'completed_at': ex.completed_at.isoformat() if ex.completed_at else None
            })
        
        # Top red flags (más comunes)
        top_flags = db.query(
            RedFlag.flag_type,
            func.count(RedFlag.id).label('count')
        ).group_by(RedFlag.flag_type).order_by(desc('count')).limit(10).all()
        
        top_red_flags = [
            {'type': flag_type, 'count': count}
            for flag_type, count in top_flags
        ]
        
        # Montos totales extraídos (sumando las evidencias que contienen amounts)
        total_amount_detected = 0
        high_amount_flags = db.query(RedFlag).filter(
            RedFlag.flag_type == 'HIGH_AMOUNT'
        ).all()
        
        for flag in high_amount_flags:
            if flag.evidence and isinstance(flag.evidence, dict):
                amount = flag.evidence.get('amount', 0)
                if amount:
                    total_amount_detected += amount
        
        # Configuraciones activas
        active_configs = db.query(func.count(AnalysisConfig.id)).filter(
            AnalysisConfig.is_active == True
        ).scalar() or 0
        
        return {
            'summary': {
                'total_documents': total_documents,
                'analyzed_documents': analyzed_documents,
                'pending_documents': pending_documents,
                'total_executions': total_executions,
                'completed_executions': completed_executions,
                'total_red_flags': total_red_flags,
                'avg_transparency_score': round(avg_transparency, 2) if avg_transparency else 0,
                'total_amount_detected': round(total_amount_detected, 2),
                'active_configs': active_configs
            },
            'red_flags': {
                'by_severity': red_flags_by_severity,
                'top_types': top_red_flags
            },
            'risk_distribution': risk_stats,
            'documents_by_month': monthly_data,
            'recent_executions': executions_list
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'summary': {
                'total_documents': 0,
                'analyzed_documents': 0,
                'pending_documents': 0,
                'total_executions': 0,
                'completed_executions': 0,
                'total_red_flags': 0,
                'avg_transparency_score': 0,
                'total_amount_detected': 0,
                'active_configs': 0
            },
            'red_flags': {
                'by_severity': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0},
                'top_types': []
            },
            'risk_distribution': {'high': 0, 'medium': 0, 'low': 0},
            'documents_by_month': [],
            'recent_executions': []
        }


@router.get("/red-flags/recent")
async def get_recent_red_flags(
    limit: int = 20,
    severity: str = None,
    db: Session = Depends(get_sync_db)
) -> Dict[str, Any]:
    """
    Get recent red flags with optional severity filter
    """
    try:
        query = db.query(RedFlag).order_by(desc(RedFlag.created_at))
        
        if severity:
            query = query.filter(RedFlag.severity == severity)
        
        flags = query.limit(limit).all()
        
        result = []
        for flag in flags:
            # Get document info
            document = db.query(BoletinDocument).filter(
                BoletinDocument.id == flag.document_id
            ).first()
            
            result.append({
                'id': flag.id,
                'type': flag.flag_type,
                'severity': flag.severity,
                'category': flag.category,
                'title': flag.title,
                'description': flag.description,
                'evidence': flag.evidence,
                'confidence_score': flag.confidence_score,
                'created_at': flag.created_at.isoformat() if flag.created_at else None,
                'document': {
                    'id': document.id if document else None,
                    'filename': document.filename if document else None,
                    'year': document.year if document else None,
                    'month': document.month if document else None,
                    'day': document.day if document else None
                } if document else None
            })
        
        return {
            'total': len(result),
            'flags': result
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'total': 0,
            'flags': []
        }


@router.get("/timeline")
async def get_analysis_timeline(
    db: Session = Depends(get_sync_db)
) -> Dict[str, Any]:
    """
    Get timeline of analysis activity
    """
    try:
        # Get all completed executions with their dates
        executions = db.query(AnalysisExecution).filter(
            AnalysisExecution.status == 'completed'
        ).order_by(AnalysisExecution.started_at).all()
        
        timeline = []
        for ex in executions:
            timeline.append({
                'id': ex.id,
                'name': ex.execution_name,
                'started_at': ex.started_at.isoformat() if ex.started_at else None,
                'completed_at': ex.completed_at.isoformat() if ex.completed_at else None,
                'total_documents': ex.total_documents,
                'processed_documents': ex.processed_documents,
                'duration_seconds': (
                    (ex.completed_at - ex.started_at).total_seconds()
                    if ex.completed_at and ex.started_at else 0
                )
            })
        
        return {
            'total_executions': len(timeline),
            'timeline': timeline
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'total_executions': 0,
            'timeline': []
        }


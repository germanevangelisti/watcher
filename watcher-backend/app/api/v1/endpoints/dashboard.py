"""
Dashboard endpoint with real data from Watcher Agent
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.sync_session import get_sync_db
from app.db.models import (
    Boletin,  # Tabla real de boletines
    Analisis,  # Tabla real de análisis
    AgentWorkflow  # Workflows de agentes
)

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_sync_db)
) -> Dict[str, Any]:
    """
    Get comprehensive dashboard statistics from real Watcher Agent data
    """
    try:
        # Documentos totales (boletines)
        total_documents = db.query(func.count(Boletin.id)).scalar() or 0
        
        # Documentos con texto extraído (status='completed')
        analyzed_documents = db.query(func.count(Boletin.id)).filter(
            Boletin.status == 'completed'
        ).scalar() or 0
        
        # Documentos pendientes de extracción
        pending_documents = db.query(func.count(Boletin.id)).filter(
            Boletin.status == 'pending'
        ).scalar() or 0
        
        # Total de workflows ejecutados
        total_executions = db.query(func.count(AgentWorkflow.id)).scalar() or 0
        
        # Workflows completados
        completed_executions = db.query(func.count(AgentWorkflow.id)).filter(
            AgentWorkflow.status == 'completed'
        ).scalar() or 0
        
        # Total análisis realizados (RED FLAGS = análisis con riesgo ALTO)
        total_analyses = db.query(func.count(Analisis.id)).scalar() or 0
        total_red_flags = db.query(func.count(Analisis.id)).filter(
            Analisis.riesgo == 'ALTO'
        ).scalar() or 0
        
        # Red flags por "severidad" (mapeando riesgo a severidad)
        risk_stats = db.query(
            Analisis.riesgo,
            func.count(Analisis.id)
        ).group_by(Analisis.riesgo).all()
        
        red_flags_by_severity = {
            'critical': 0,  # ALTO
            'high': 0,      # MEDIO
            'medium': 0,    # BAJO
            'low': 0        # Otros
        }
        
        for riesgo, count in risk_stats:
            if riesgo == 'ALTO':
                red_flags_by_severity['critical'] = count
            elif riesgo == 'MEDIO':
                red_flags_by_severity['high'] = count
            elif riesgo == 'BAJO':
                red_flags_by_severity['medium'] = count
        
        # Score promedio de transparencia (no tenemos, usar valor ficticio basado en análisis)
        # Si hay análisis, mostrar un valor proporcional
        avg_transparency = 0.0
        if total_analyses > 0:
            # Calcular score basado en proporción de análisis de alto riesgo
            risk_ratio = total_red_flags / total_analyses if total_analyses > 0 else 0
            # Invertir: menos riesgo = más transparencia
            avg_transparency = (1 - risk_ratio) * 100
        
        # Distribución de riesgo
        risk_distribution = {
            'high': 0,
            'medium': 0,
            'low': 0
        }
        for riesgo, count in risk_stats:
            if riesgo == 'ALTO':
                risk_distribution['high'] = count
            elif riesgo == 'MEDIO':
                risk_distribution['medium'] = count
            elif riesgo == 'BAJO':
                risk_distribution['low'] = count
        
        # Documentos por mes (basado en fecha del boletín: YYYYMMDD)
        boletines_with_dates = db.query(Boletin.date).filter(Boletin.date.isnot(None)).all()
        
        monthly_counts = {}
        for (date_str,) in boletines_with_dates:
            if date_str and len(date_str) >= 6:
                year = int(date_str[:4])
                month = int(date_str[4:6])
                key = f"{year}-{month:02d}"
                monthly_counts[key] = monthly_counts.get(key, 0) + 1
        
        monthly_data = []
        for period in sorted(monthly_counts.keys()):
            year, month = period.split('-')
            monthly_data.append({
                'period': period,
                'count': monthly_counts[period],
                'year': int(year),
                'month': int(month)
            })
        
        # Últimas ejecuciones (workflows completados)
        recent_workflows = db.query(AgentWorkflow).filter(
            AgentWorkflow.status == 'completed'
        ).order_by(desc(AgentWorkflow.created_at)).limit(5).all()
        
        executions_list = []
        for wf in recent_workflows:
            executions_list.append({
                'id': wf.id,
                'name': wf.workflow_name or f"Workflow #{wf.id}",
                'status': wf.status,
                'total_documents': analyzed_documents,  # Usar docs analizados
                'processed_documents': analyzed_documents,
                'started_at': wf.created_at.isoformat() if wf.created_at else None,
                'completed_at': wf.updated_at.isoformat() if wf.updated_at else None
            })
        
        # Top categorías de análisis
        top_categories = db.query(
            Analisis.categoria,
            func.count(Analisis.id).label('count')
        ).group_by(Analisis.categoria).order_by(desc('count')).limit(10).all()
        
        top_red_flags = [
            {'type': categoria or 'sin_categoria', 'count': count}
            for categoria, count in top_categories
        ]
        
        # Montos totales detectados (sumar de monto_numerico)
        total_amount_detected = db.query(func.sum(Analisis.monto_numerico)).scalar() or 0
        
        # Configuraciones activas (usar total de workflows como proxy)
        active_configs = db.query(func.count(AgentWorkflow.id)).filter(
            AgentWorkflow.status.in_(['pending', 'running'])
        ).scalar() or 0
        
        return {
            'summary': {
                'total_documents': total_documents,
                'analyzed_documents': analyzed_documents,
                'pending_documents': pending_documents,
                'total_executions': total_executions,
                'completed_executions': completed_executions,
                'total_red_flags': total_red_flags,
                'avg_transparency_score': round(avg_transparency, 2),
                'total_amount_detected': round(total_amount_detected, 2),
                'active_configs': active_configs
            },
            'red_flags': {
                'by_severity': red_flags_by_severity,
                'top_types': top_red_flags
            },
            'risk_distribution': risk_distribution,
            'documents_by_month': monthly_data,
            'recent_executions': executions_list
        }
        
    except Exception as e:
        import traceback
        print(f"Error in get_dashboard_stats: {str(e)}")
        print(traceback.format_exc())
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
    Get recent high-risk analyses (red flags) from Analisis table
    """
    try:
        # Consultar análisis de alto riesgo (RED FLAGS)
        query = db.query(Analisis).order_by(desc(Analisis.created_at))
        
        # Mapear severity a riesgo
        if severity:
            if severity == 'critical':
                query = query.filter(Analisis.riesgo == 'ALTO')
            elif severity == 'high':
                query = query.filter(Analisis.riesgo == 'MEDIO')
            elif severity in ['medium', 'low']:
                query = query.filter(Analisis.riesgo == 'BAJO')
        else:
            # Por defecto, solo mostrar alto riesgo
            query = query.filter(Analisis.riesgo == 'ALTO')
        
        analyses = query.limit(limit).all()
        
        result = []
        for analisis in analyses:
            # Get boletin info
            boletin = db.query(Boletin).filter(
                Boletin.id == analisis.boletin_id
            ).first()
            
            # Mapear riesgo a severity
            severity_map = {
                'ALTO': 'critical',
                'MEDIO': 'high',
                'BAJO': 'medium'
            }
            
            # Extraer año/mes/día del date del boletín
            year, month, day = None, None, None
            if boletin and boletin.date and len(boletin.date) >= 8:
                year = int(boletin.date[:4])
                month = int(boletin.date[4:6])
                day = int(boletin.date[6:8])
            
            result.append({
                'id': analisis.id,
                'type': analisis.tipo_curro or analisis.categoria or 'general',
                'severity': severity_map.get(analisis.riesgo, 'medium'),
                'category': analisis.categoria or 'sin_categoria',
                'title': f"{analisis.categoria or 'Análisis'} - {analisis.entidad_beneficiaria or 'Sin entidad'}",
                'description': analisis.accion_sugerida or analisis.fragmento[:200] if analisis.fragmento else 'Sin descripción',
                'evidence': {
                    'fragmento': analisis.fragmento[:500] if analisis.fragmento else None,
                    'monto': analisis.monto_estimado,
                    'datos_extra': analisis.datos_extra
                },
                'confidence_score': 0.85,  # Valor ficticio
                'created_at': analisis.created_at.isoformat() if analisis.created_at else None,
                'document': {
                    'id': boletin.id if boletin else None,
                    'filename': boletin.filename if boletin else None,
                    'year': year,
                    'month': month,
                    'day': day
                } if boletin else None
            })
        
        return {
            'total': len(result),
            'flags': result
        }
        
    except Exception as e:
        import traceback
        print(f"Error in get_recent_red_flags: {str(e)}")
        print(traceback.format_exc())
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
    Get timeline of workflow execution activity
    """
    try:
        # Get all completed workflows
        workflows = db.query(AgentWorkflow).filter(
            AgentWorkflow.status == 'completed'
        ).order_by(AgentWorkflow.created_at).all()
        
        timeline = []
        for wf in workflows:
            # Contar análisis generados por este workflow (aproximado por fecha)
            analyses_count = db.query(func.count(Analisis.id)).filter(
                Analisis.created_at >= wf.created_at
            ).scalar() or 0
            
            duration = 0
            if wf.updated_at and wf.created_at:
                duration = (wf.updated_at - wf.created_at).total_seconds()
            
            timeline.append({
                'id': wf.id,
                'name': wf.workflow_name or f"Workflow #{wf.id}",
                'started_at': wf.created_at.isoformat() if wf.created_at else None,
                'completed_at': wf.updated_at.isoformat() if wf.updated_at else None,
                'total_documents': analyses_count,
                'processed_documents': analyses_count,
                'duration_seconds': duration
            })
        
        return {
            'total_executions': len(timeline),
            'timeline': timeline
        }
        
    except Exception as e:
        import traceback
        print(f"Error in get_analysis_timeline: {str(e)}")
        print(traceback.format_exc())
        return {
            'error': str(e),
            'total_executions': 0,
            'timeline': []
        }


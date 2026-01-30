"""
Herramientas de análisis para los agentes
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, case
from collections import defaultdict

from app.db.models import AnalysisResult, RedFlag, BoletinDocument

logger = logging.getLogger(__name__)


class AnalysisTools:
    """
    Herramientas de análisis para insights y reportes
    """
    
    @staticmethod
    def get_transparency_trends(
        db: Session,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int
    ) -> List[Dict[str, Any]]:
        """
        Analiza tendencias de transparencia en un período
        
        Args:
            db: Sesión de base de datos
            start_year: Año inicial
            start_month: Mes inicial
            end_year: Año final
            end_month: Mes final
        
        Returns:
            Lista con promedios por mes
        """
        results = db.query(
            BoletinDocument.year,
            BoletinDocument.month,
            func.avg(AnalysisResult.transparency_score).label('avg_score'),
            func.count(AnalysisResult.id).label('total_docs'),
            func.sum(case((AnalysisResult.risk_level == 'high', 1), else_=0)).label('high_risk_count')
        ).join(
            AnalysisResult, BoletinDocument.id == AnalysisResult.document_id
        ).filter(
            and_(
                or_(
                    BoletinDocument.year > start_year,
                    and_(BoletinDocument.year == start_year, BoletinDocument.month >= start_month)
                ),
                or_(
                    BoletinDocument.year < end_year,
                    and_(BoletinDocument.year == end_year, BoletinDocument.month <= end_month)
                )
            )
        ).group_by(
            BoletinDocument.year,
            BoletinDocument.month
        ).order_by(
            BoletinDocument.year,
            BoletinDocument.month
        ).all()
        
        return [
            {
                "year": year,
                "month": month,
                "avg_transparency_score": float(avg_score) if avg_score else 0,
                "total_documents": total_docs or 0,
                "high_risk_count": high_risk_count or 0
            }
            for year, month, avg_score, total_docs, high_risk_count in results
        ]
    
    @staticmethod
    def get_red_flag_distribution(
        db: Session,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analiza la distribución de red flags
        
        Args:
            db: Sesión de base de datos
            year: Filtrar por año
            month: Filtrar por mes
        
        Returns:
            Distribución de red flags por tipo, severidad y categoría
        """
        query = db.query(RedFlag).join(BoletinDocument)
        
        if year:
            query = query.filter(BoletinDocument.year == year)
        if month:
            query = query.filter(BoletinDocument.month == month)
        
        red_flags = query.all()
        
        by_type = defaultdict(int)
        by_severity = defaultdict(int)
        by_category = defaultdict(int)
        
        for rf in red_flags:
            by_type[rf.flag_type] += 1
            by_severity[rf.severity] += 1
            by_category[rf.category] += 1
        
        return {
            "total": len(red_flags),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "by_category": dict(by_category)
        }
    
    @staticmethod
    def get_top_risk_documents(
        db: Session,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Obtiene los documentos con mayor riesgo
        
        Args:
            db: Sesión de base de datos
            limit: Límite de resultados
        
        Returns:
            Lista de documentos ordenados por riesgo
        """
        results = db.query(
            AnalysisResult,
            BoletinDocument
        ).join(
            BoletinDocument, AnalysisResult.document_id == BoletinDocument.id
        ).filter(
            AnalysisResult.risk_level == 'high'
        ).order_by(
            desc(AnalysisResult.num_red_flags),
            AnalysisResult.transparency_score
        ).limit(limit).all()
        
        return [
            {
                "document_id": doc.id,
                "filename": doc.filename,
                "year": doc.year,
                "month": doc.month,
                "day": doc.day,
                "transparency_score": result.transparency_score,
                "num_red_flags": result.num_red_flags,
                "anomaly_score": result.anomaly_score,
                "risk_level": result.risk_level
            }
            for result, doc in results
        ]
    
    @staticmethod
    def get_entity_analysis(
        db: Session,
        entity_type: str = "beneficiaries"
    ) -> List[Dict[str, Any]]:
        """
        Analiza las entidades extraídas más frecuentes
        
        Args:
            db: Sesión de base de datos
            entity_type: Tipo de entidad a analizar
        
        Returns:
            Lista de entidades con frecuencia y scores asociados
        """
        results = db.query(AnalysisResult).filter(
            AnalysisResult.extracted_entities.isnot(None)
        ).all()
        
        entity_stats = defaultdict(lambda: {
            'count': 0,
            'total_score': 0,
            'documents': set(),
            'high_risk_count': 0
        })
        
        for result in results:
            entities = result.extracted_entities or {}
            entity_list = entities.get(entity_type, [])
            
            for entity in entity_list:
                entity_str = str(entity)
                entity_stats[entity_str]['count'] += 1
                entity_stats[entity_str]['total_score'] += (result.transparency_score or 0)
                entity_stats[entity_str]['documents'].add(result.document_id)
                if result.risk_level == 'high':
                    entity_stats[entity_str]['high_risk_count'] += 1
        
        # Convertir a lista y ordenar por frecuencia
        entity_list = []
        for entity, stats in entity_stats.items():
            entity_list.append({
                'entity': entity,
                'frequency': stats['count'],
                'avg_transparency_score': stats['total_score'] / stats['count'] if stats['count'] > 0 else 0,
                'num_documents': len(stats['documents']),
                'high_risk_appearances': stats['high_risk_count']
            })
        
        entity_list.sort(key=lambda x: x['frequency'], reverse=True)
        
        return entity_list[:50]  # Top 50
    
    @staticmethod
    def compare_periods(
        db: Session,
        period1_year: int,
        period1_month: int,
        period2_year: int,
        period2_month: int
    ) -> Dict[str, Any]:
        """
        Compara métricas entre dos períodos
        
        Args:
            db: Sesión de base de datos
            period1_year: Año del primer período
            period1_month: Mes del primer período
            period2_year: Año del segundo período
            period2_month: Mes del segundo período
        
        Returns:
            Comparación de métricas
        """
        def get_period_stats(year, month):
            results = db.query(AnalysisResult).join(
                BoletinDocument
            ).filter(
                and_(
                    BoletinDocument.year == year,
                    BoletinDocument.month == month
                )
            ).all()
            
            if not results:
                return {
                    'total_docs': 0,
                    'avg_transparency': 0,
                    'high_risk_count': 0,
                    'total_red_flags': 0
                }
            
            return {
                'total_docs': len(results),
                'avg_transparency': sum(r.transparency_score or 0 for r in results) / len(results),
                'high_risk_count': sum(1 for r in results if r.risk_level == 'high'),
                'total_red_flags': sum(r.num_red_flags or 0 for r in results)
            }
        
        stats1 = get_period_stats(period1_year, period1_month)
        stats2 = get_period_stats(period2_year, period2_month)
        
        return {
            'period1': {
                'year': period1_year,
                'month': period1_month,
                **stats1
            },
            'period2': {
                'year': period2_year,
                'month': period2_month,
                **stats2
            },
            'comparison': {
                'transparency_change': stats2['avg_transparency'] - stats1['avg_transparency'],
                'high_risk_change': stats2['high_risk_count'] - stats1['high_risk_count'],
                'red_flags_change': stats2['total_red_flags'] - stats1['total_red_flags']
            }
        }
    
    @staticmethod
    def detect_anomalous_patterns(
        db: Session,
        threshold_score: float = 30.0,
        min_red_flags: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Detecta patrones anómalos en los análisis
        
        Args:
            db: Sesión de base de datos
            threshold_score: Score mínimo para considerar anómalo
            min_red_flags: Mínimo de red flags
        
        Returns:
            Lista de patrones anómalos detectados
        """
        # Documentos con bajo score y muchas red flags
        suspicious_results = db.query(
            AnalysisResult,
            BoletinDocument
        ).join(
            BoletinDocument
        ).filter(
            and_(
                AnalysisResult.transparency_score < threshold_score,
                AnalysisResult.num_red_flags >= min_red_flags
            )
        ).order_by(
            AnalysisResult.transparency_score
        ).limit(50).all()
        
        patterns = []
        for result, doc in suspicious_results:
            patterns.append({
                'document_id': doc.id,
                'filename': doc.filename,
                'date': f"{doc.year}-{doc.month:02d}-{doc.day:02d}",
                'transparency_score': result.transparency_score,
                'num_red_flags': result.num_red_flags,
                'anomaly_score': result.anomaly_score,
                'risk_level': result.risk_level,
                'red_flags_types': [rf['type'] for rf in (result.red_flags or [])],
                'pattern_description': f"Score bajo ({result.transparency_score:.1f}) con {result.num_red_flags} red flags"
            })
        
        return patterns
    
    @staticmethod
    def get_monthly_summary(
        db: Session,
        year: int,
        month: int
    ) -> Dict[str, Any]:
        """
        Genera un resumen mensual completo
        
        Args:
            db: Sesión de base de datos
            year: Año
            month: Mes
        
        Returns:
            Resumen completo del mes
        """
        # Documentos del mes
        documents = db.query(BoletinDocument).filter(
            and_(
                BoletinDocument.year == year,
                BoletinDocument.month == month
            )
        ).all()
        
        # Resultados del mes
        results = db.query(AnalysisResult).join(
            BoletinDocument
        ).filter(
            and_(
                BoletinDocument.year == year,
                BoletinDocument.month == month
            )
        ).all()
        
        # Red flags del mes
        red_flags = db.query(RedFlag).join(
            BoletinDocument
        ).filter(
            and_(
                BoletinDocument.year == year,
                BoletinDocument.month == month
            )
        ).all()
        
        if not results:
            return {
                'year': year,
                'month': month,
                'total_documents': len(documents),
                'message': 'No hay resultados de análisis para este mes'
            }
        
        return {
            'year': year,
            'month': month,
            'total_documents': len(documents),
            'total_analyzed': len(results),
            'avg_transparency_score': sum(r.transparency_score or 0 for r in results) / len(results),
            'risk_distribution': {
                'high': sum(1 for r in results if r.risk_level == 'high'),
                'medium': sum(1 for r in results if r.risk_level == 'medium'),
                'low': sum(1 for r in results if r.risk_level == 'low')
            },
            'total_red_flags': len(red_flags),
            'red_flags_by_severity': {
                'high': sum(1 for rf in red_flags if rf.severity == 'high'),
                'medium': sum(1 for rf in red_flags if rf.severity == 'medium'),
                'low': sum(1 for rf in red_flags if rf.severity == 'low')
            },
            'top_risk_documents': [
                {
                    'filename': r.document.filename,
                    'transparency_score': r.transparency_score,
                    'num_red_flags': r.num_red_flags
                }
                for r in sorted(results, key=lambda x: (x.num_red_flags or 0), reverse=True)[:5]
            ]
        }


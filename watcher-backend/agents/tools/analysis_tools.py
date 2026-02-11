"""
Herramientas de análisis para los agentes
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, and_, or_, case, select
from collections import defaultdict

from app.db.models import AnalysisResult, RedFlag, BoletinDocument

logger = logging.getLogger(__name__)


class AnalysisTools:
    """
    Herramientas de análisis para insights y reportes (async)
    """
    
    @staticmethod
    async def get_transparency_trends(
        db: AsyncSession,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int
    ) -> List[Dict[str, Any]]:
        """
        Analiza tendencias de transparencia en un período
        
        Args:
            db: Sesión de base de datos async
            start_year: Año inicial
            start_month: Mes inicial
            end_year: Año final
            end_month: Mes final
        
        Returns:
            Lista con promedios por mes
        """
        stmt = select(
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
        )
        
        result = await db.execute(stmt)
        results = result.all()
        
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
    async def get_red_flag_distribution(
        db: AsyncSession,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analiza la distribución de red flags
        
        Args:
            db: Sesión de base de datos async
            year: Filtrar por año
            month: Filtrar por mes
        
        Returns:
            Distribución de red flags por tipo, severidad y categoría
        """
        stmt = select(RedFlag).join(BoletinDocument)
        
        if year:
            stmt = stmt.filter(BoletinDocument.year == year)
        if month:
            stmt = stmt.filter(BoletinDocument.month == month)
        
        result = await db.execute(stmt)
        red_flags = result.scalars().all()
        
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
    async def get_top_risk_documents(
        db: AsyncSession,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Obtiene los documentos con mayor riesgo
        
        Args:
            db: Sesión de base de datos async
            limit: Límite de resultados
        
        Returns:
            Lista de documentos ordenados por riesgo
        """
        stmt = select(
            AnalysisResult,
            BoletinDocument
        ).join(
            BoletinDocument, AnalysisResult.document_id == BoletinDocument.id
        ).filter(
            AnalysisResult.risk_level == 'high'
        ).order_by(
            desc(AnalysisResult.num_red_flags),
            AnalysisResult.transparency_score
        ).limit(limit)
        
        result = await db.execute(stmt)
        results = result.all()
        
        return [
            {
                "document_id": doc.id,
                "filename": doc.filename,
                "year": doc.year,
                "month": doc.month,
                "day": doc.day,
                "transparency_score": analysis_result.transparency_score,
                "num_red_flags": analysis_result.num_red_flags,
                "anomaly_score": analysis_result.anomaly_score,
                "risk_level": analysis_result.risk_level
            }
            for analysis_result, doc in results
        ]
    
    @staticmethod
    async def get_entity_analysis(
        db: AsyncSession,
        entity_type: str = "beneficiaries"
    ) -> List[Dict[str, Any]]:
        """
        Analiza las entidades extraídas más frecuentes
        
        Args:
            db: Sesión de base de datos async
            entity_type: Tipo de entidad a analizar
        
        Returns:
            Lista de entidades con frecuencia y scores asociados
        """
        stmt = select(AnalysisResult).filter(
            AnalysisResult.extracted_entities.isnot(None)
        )
        
        result = await db.execute(stmt)
        results = result.scalars().all()
        
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
    async def compare_periods(
        db: AsyncSession,
        period1_year: int,
        period1_month: int,
        period2_year: int,
        period2_month: int
    ) -> Dict[str, Any]:
        """
        Compara métricas entre dos períodos
        
        Args:
            db: Sesión de base de datos async
            period1_year: Año del primer período
            period1_month: Mes del primer período
            period2_year: Año del segundo período
            period2_month: Mes del segundo período
        
        Returns:
            Comparación de métricas
        """
        async def get_period_stats(year, month):
            stmt = select(AnalysisResult).join(
                BoletinDocument
            ).filter(
                and_(
                    BoletinDocument.year == year,
                    BoletinDocument.month == month
                )
            )
            
            result = await db.execute(stmt)
            results = result.scalars().all()
            
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
        
        stats1 = await get_period_stats(period1_year, period1_month)
        stats2 = await get_period_stats(period2_year, period2_month)
        
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
    async def detect_anomalous_patterns(
        db: AsyncSession,
        threshold_score: float = 30.0,
        min_red_flags: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Detecta patrones anómalos en los análisis
        
        Args:
            db: Sesión de base de datos async
            threshold_score: Score mínimo para considerar anómalo
            min_red_flags: Mínimo de red flags
        
        Returns:
            Lista de patrones anómalos detectados
        """
        # Documentos con bajo score y muchas red flags
        stmt = select(
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
        ).limit(50)
        
        result = await db.execute(stmt)
        suspicious_results = result.all()
        
        patterns = []
        for analysis_result, doc in suspicious_results:
            patterns.append({
                'document_id': doc.id,
                'filename': doc.filename,
                'date': f"{doc.year}-{doc.month:02d}-{doc.day:02d}",
                'transparency_score': analysis_result.transparency_score,
                'num_red_flags': analysis_result.num_red_flags,
                'anomaly_score': analysis_result.anomaly_score,
                'risk_level': analysis_result.risk_level,
                'red_flags_types': [rf['type'] for rf in (analysis_result.red_flags or [])],
                'pattern_description': f"Score bajo ({analysis_result.transparency_score:.1f}) con {analysis_result.num_red_flags} red flags"
            })
        
        return patterns
    
    @staticmethod
    async def get_monthly_summary(
        db: AsyncSession,
        year: int,
        month: int
    ) -> Dict[str, Any]:
        """
        Genera un resumen mensual completo
        
        Args:
            db: Sesión de base de datos async
            year: Año
            month: Mes
        
        Returns:
            Resumen completo del mes
        """
        # Documentos del mes
        stmt = select(BoletinDocument).filter(
            and_(
                BoletinDocument.year == year,
                BoletinDocument.month == month
            )
        )
        result = await db.execute(stmt)
        documents = result.scalars().all()
        
        # Resultados del mes
        stmt = select(AnalysisResult).join(
            BoletinDocument
        ).filter(
            and_(
                BoletinDocument.year == year,
                BoletinDocument.month == month
            )
        )
        result = await db.execute(stmt)
        results = result.scalars().all()
        
        # Red flags del mes
        stmt = select(RedFlag).join(
            BoletinDocument
        ).filter(
            and_(
                BoletinDocument.year == year,
                BoletinDocument.month == month
            )
        )
        result = await db.execute(stmt)
        red_flags = result.scalars().all()
        
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


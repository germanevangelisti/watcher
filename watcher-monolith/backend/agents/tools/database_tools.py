"""
Herramientas de base de datos para los agentes
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.db.models import (
    BoletinDocument, AnalysisResult, RedFlag, 
    AnalysisConfig, AnalysisExecution
)
from app.db.sync_session import SyncSessionLocal

logger = logging.getLogger(__name__)


class DatabaseTools:
    """
    Herramientas para que los agentes accedan a la base de datos
    """
    
    @staticmethod
    def get_db() -> Session:
        """Obtiene una sesión de base de datos"""
        return SyncSessionLocal()
    
    @staticmethod
    def get_documents(
        db: Session,
        year: Optional[int] = None,
        month: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene documentos de la base de datos
        
        Args:
            db: Sesión de base de datos
            year: Filtrar por año
            month: Filtrar por mes
            status: Filtrar por estado
            limit: Límite de resultados
        
        Returns:
            Lista de documentos
        """
        query = db.query(BoletinDocument)
        
        if year:
            query = query.filter(BoletinDocument.year == year)
        if month:
            query = query.filter(BoletinDocument.month == month)
        if status:
            query = query.filter(BoletinDocument.analysis_status == status)
        
        documents = query.limit(limit).all()
        
        return [
            {
                "id": doc.id,
                "filename": doc.filename,
                "year": doc.year,
                "month": doc.month,
                "day": doc.day,
                "section": doc.section,
                "file_path": doc.file_path,
                "analysis_status": doc.analysis_status,
                "num_pages": doc.num_pages,
                "last_analyzed": doc.last_analyzed.isoformat() if doc.last_analyzed else None
            }
            for doc in documents
        ]
    
    @staticmethod
    def get_analysis_results(
        db: Session,
        document_id: Optional[int] = None,
        risk_level: Optional[str] = None,
        min_score: Optional[float] = None,
        min_red_flags: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene resultados de análisis
        
        Args:
            db: Sesión de base de datos
            document_id: Filtrar por documento
            risk_level: Filtrar por nivel de riesgo (high, medium, low)
            min_score: Score mínimo de transparencia
            min_red_flags: Mínimo de red flags
            limit: Límite de resultados
        
        Returns:
            Lista de resultados
        """
        query = db.query(AnalysisResult)
        
        if document_id:
            query = query.filter(AnalysisResult.document_id == document_id)
        if risk_level:
            query = query.filter(AnalysisResult.risk_level == risk_level)
        if min_score is not None:
            query = query.filter(AnalysisResult.transparency_score >= min_score)
        if min_red_flags is not None:
            query = query.filter(AnalysisResult.num_red_flags >= min_red_flags)
        
        results = query.order_by(desc(AnalysisResult.analyzed_at)).limit(limit).all()
        
        return [
            {
                "id": result.id,
                "document_id": result.document_id,
                "transparency_score": result.transparency_score,
                "risk_level": result.risk_level,
                "anomaly_score": result.anomaly_score,
                "num_red_flags": result.num_red_flags,
                "extracted_entities": result.extracted_entities,
                "red_flags": result.red_flags,
                "ml_predictions": result.ml_predictions,
                "analyzed_at": result.analyzed_at.isoformat() if result.analyzed_at else None
            }
            for result in results
        ]
    
    @staticmethod
    def get_red_flags(
        db: Session,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene red flags
        
        Args:
            db: Sesión de base de datos
            severity: Filtrar por severidad (high, medium, low)
            category: Filtrar por categoría
            limit: Límite de resultados
        
        Returns:
            Lista de red flags
        """
        query = db.query(RedFlag).join(AnalysisResult).join(BoletinDocument)
        
        if severity:
            query = query.filter(RedFlag.severity == severity)
        if category:
            query = query.filter(RedFlag.category == category)
        
        red_flags = query.order_by(desc(RedFlag.created_at)).limit(limit).all()
        
        return [
            {
                "id": rf.id,
                "result_id": rf.result_id,
                "document_id": rf.document_id,
                "flag_type": rf.flag_type,
                "severity": rf.severity,
                "category": rf.category,
                "title": rf.title,
                "description": rf.description,
                "evidence": rf.evidence,
                "confidence_score": rf.confidence_score,
                "page_number": rf.page_number,
                "created_at": rf.created_at.isoformat() if rf.created_at else None
            }
            for rf in red_flags
        ]
    
    @staticmethod
    def get_statistics(db: Session) -> Dict[str, Any]:
        """
        Obtiene estadísticas generales del sistema
        
        Args:
            db: Sesión de base de datos
        
        Returns:
            Diccionario con estadísticas
        """
        total_documents = db.query(func.count(BoletinDocument.id)).scalar()
        total_analyzed = db.query(func.count(BoletinDocument.id)).filter(
            BoletinDocument.analysis_status == 'completed'
        ).scalar()
        
        total_results = db.query(func.count(AnalysisResult.id)).scalar()
        
        high_risk = db.query(func.count(AnalysisResult.id)).filter(
            AnalysisResult.risk_level == 'high'
        ).scalar()
        
        total_red_flags = db.query(func.count(RedFlag.id)).scalar()
        high_severity_flags = db.query(func.count(RedFlag.id)).filter(
            RedFlag.severity == 'high'
        ).scalar()
        
        avg_transparency = db.query(func.avg(AnalysisResult.transparency_score)).scalar()
        
        # Distribución por año y mes
        docs_by_period = db.query(
            BoletinDocument.year,
            BoletinDocument.month,
            func.count(BoletinDocument.id).label('count')
        ).group_by(
            BoletinDocument.year,
            BoletinDocument.month
        ).order_by(
            BoletinDocument.year,
            BoletinDocument.month
        ).all()
        
        return {
            "total_documents": total_documents or 0,
            "total_analyzed": total_analyzed or 0,
            "total_results": total_results or 0,
            "high_risk_documents": high_risk or 0,
            "total_red_flags": total_red_flags or 0,
            "high_severity_flags": high_severity_flags or 0,
            "avg_transparency_score": float(avg_transparency) if avg_transparency else 0,
            "documents_by_period": [
                {
                    "year": year,
                    "month": month,
                    "count": count
                }
                for year, month, count in docs_by_period
            ]
        }
    
    @staticmethod
    def get_document_with_results(
        db: Session,
        document_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene un documento con todos sus resultados de análisis
        
        Args:
            db: Sesión de base de datos
            document_id: ID del documento
        
        Returns:
            Diccionario con documento y resultados
        """
        document = db.query(BoletinDocument).filter(
            BoletinDocument.id == document_id
        ).first()
        
        if not document:
            return None
        
        results = db.query(AnalysisResult).filter(
            AnalysisResult.document_id == document_id
        ).all()
        
        red_flags = db.query(RedFlag).filter(
            RedFlag.document_id == document_id
        ).all()
        
        return {
            "document": {
                "id": document.id,
                "filename": document.filename,
                "year": document.year,
                "month": document.month,
                "day": document.day,
                "section": document.section,
                "file_path": document.file_path,
                "analysis_status": document.analysis_status,
                "num_pages": document.num_pages
            },
            "results": [
                {
                    "id": result.id,
                    "transparency_score": result.transparency_score,
                    "risk_level": result.risk_level,
                    "anomaly_score": result.anomaly_score,
                    "num_red_flags": result.num_red_flags,
                    "extracted_entities": result.extracted_entities,
                    "red_flags": result.red_flags,
                    "ml_predictions": result.ml_predictions
                }
                for result in results
            ],
            "red_flags": [
                {
                    "id": rf.id,
                    "flag_type": rf.flag_type,
                    "severity": rf.severity,
                    "category": rf.category,
                    "description": rf.description,
                    "confidence_score": rf.confidence_score,
                    "page_number": rf.page_number
                }
                for rf in red_flags
            ]
        }
    
    @staticmethod
    def search_by_entity(
        db: Session,
        entity_type: str,
        entity_value: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Busca documentos que contengan una entidad específica
        
        Args:
            db: Sesión de base de datos
            entity_type: Tipo de entidad (beneficiaries, amounts, contracts, etc.)
            entity_value: Valor a buscar
            limit: Límite de resultados
        
        Returns:
            Lista de documentos con la entidad
        """
        # Buscar en extracted_entities JSON
        results = db.query(AnalysisResult).join(BoletinDocument).filter(
            AnalysisResult.extracted_entities.isnot(None)
        ).limit(limit * 2).all()  # Obtener más para filtrar
        
        matching_results = []
        for result in results:
            entities = result.extracted_entities or {}
            entity_list = entities.get(entity_type, [])
            
            # Buscar coincidencia (case-insensitive)
            if any(entity_value.lower() in str(e).lower() for e in entity_list):
                matching_results.append({
                    "document_id": result.document_id,
                    "document_filename": result.document.filename if result.document else None,
                    "transparency_score": result.transparency_score,
                    "risk_level": result.risk_level,
                    "entities_found": entity_list,
                    "analyzed_at": result.analyzed_at.isoformat() if result.analyzed_at else None
                })
                
                if len(matching_results) >= limit:
                    break
        
        return matching_results


"""
Herramientas de base de datos para los agentes
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, select

from app.db.models import (
    BoletinDocument, AnalysisResult, RedFlag
)
from app.db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class DatabaseTools:
    """
    Herramientas para que los agentes accedan a la base de datos (async)
    """
    
    @staticmethod
    async def get_db() -> AsyncSession:
        """Obtiene una sesión de base de datos async"""
        async with AsyncSessionLocal() as session:
            yield session
    
    @staticmethod
    async def get_documents(
        db: AsyncSession,
        year: Optional[int] = None,
        month: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene documentos de la base de datos
        
        Args:
            db: Sesión de base de datos async
            year: Filtrar por año
            month: Filtrar por mes
            status: Filtrar por estado
            limit: Límite de resultados
        
        Returns:
            Lista de documentos
        """
        stmt = select(BoletinDocument)
        
        if year:
            stmt = stmt.filter(BoletinDocument.year == year)
        if month:
            stmt = stmt.filter(BoletinDocument.month == month)
        if status:
            stmt = stmt.filter(BoletinDocument.analysis_status == status)
        
        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        documents = result.scalars().all()
        
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
    async def get_analysis_results(
        db: AsyncSession,
        document_id: Optional[int] = None,
        risk_level: Optional[str] = None,
        min_score: Optional[float] = None,
        min_red_flags: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene resultados de análisis
        
        Args:
            db: Sesión de base de datos async
            document_id: Filtrar por documento
            risk_level: Filtrar por nivel de riesgo (high, medium, low)
            min_score: Score mínimo de transparencia
            min_red_flags: Mínimo de red flags
            limit: Límite de resultados
        
        Returns:
            Lista de resultados
        """
        stmt = select(AnalysisResult)
        
        if document_id:
            stmt = stmt.filter(AnalysisResult.document_id == document_id)
        if risk_level:
            stmt = stmt.filter(AnalysisResult.risk_level == risk_level)
        if min_score is not None:
            stmt = stmt.filter(AnalysisResult.transparency_score >= min_score)
        if min_red_flags is not None:
            stmt = stmt.filter(AnalysisResult.num_red_flags >= min_red_flags)
        
        stmt = stmt.order_by(desc(AnalysisResult.analyzed_at)).limit(limit)
        result = await db.execute(stmt)
        results = result.scalars().all()
        
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
    async def get_red_flags(
        db: AsyncSession,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene red flags
        
        Args:
            db: Sesión de base de datos async
            severity: Filtrar por severidad (high, medium, low)
            category: Filtrar por categoría
            limit: Límite de resultados
        
        Returns:
            Lista de red flags
        """
        stmt = select(RedFlag).join(AnalysisResult).join(BoletinDocument)
        
        if severity:
            stmt = stmt.filter(RedFlag.severity == severity)
        if category:
            stmt = stmt.filter(RedFlag.category == category)
        
        stmt = stmt.order_by(desc(RedFlag.created_at)).limit(limit)
        result = await db.execute(stmt)
        red_flags = result.scalars().all()
        
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
    async def get_statistics(db: AsyncSession) -> Dict[str, Any]:
        """
        Obtiene estadísticas generales del sistema
        
        Args:
            db: Sesión de base de datos async
        
        Returns:
            Diccionario con estadísticas
        """
        # Total documents
        result = await db.execute(select(func.count(BoletinDocument.id)))
        total_documents = result.scalar()
        
        # Total analyzed
        result = await db.execute(
            select(func.count(BoletinDocument.id)).filter(
                BoletinDocument.analysis_status == 'completed'
            )
        )
        total_analyzed = result.scalar()
        
        # Total results
        result = await db.execute(select(func.count(AnalysisResult.id)))
        total_results = result.scalar()
        
        # High risk documents
        result = await db.execute(
            select(func.count(AnalysisResult.id)).filter(
                AnalysisResult.risk_level == 'high'
            )
        )
        high_risk = result.scalar()
        
        # Total red flags
        result = await db.execute(select(func.count(RedFlag.id)))
        total_red_flags = result.scalar()
        
        # High severity flags
        result = await db.execute(
            select(func.count(RedFlag.id)).filter(
                RedFlag.severity == 'high'
            )
        )
        high_severity_flags = result.scalar()
        
        # Average transparency score
        result = await db.execute(select(func.avg(AnalysisResult.transparency_score)))
        avg_transparency = result.scalar()
        
        # Distribución por año y mes
        stmt = select(
            BoletinDocument.year,
            BoletinDocument.month,
            func.count(BoletinDocument.id).label('count')
        ).group_by(
            BoletinDocument.year,
            BoletinDocument.month
        ).order_by(
            BoletinDocument.year,
            BoletinDocument.month
        )
        result = await db.execute(stmt)
        docs_by_period = result.all()
        
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
    async def get_document_with_results(
        db: AsyncSession,
        document_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene un documento con todos sus resultados de análisis
        
        Args:
            db: Sesión de base de datos async
            document_id: ID del documento
        
        Returns:
            Diccionario con documento y resultados
        """
        # Get document
        stmt = select(BoletinDocument).filter(BoletinDocument.id == document_id)
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()
        
        if not document:
            return None
        
        # Get analysis results
        stmt = select(AnalysisResult).filter(AnalysisResult.document_id == document_id)
        result = await db.execute(stmt)
        results = result.scalars().all()
        
        # Get red flags
        stmt = select(RedFlag).filter(RedFlag.document_id == document_id)
        result = await db.execute(stmt)
        red_flags = result.scalars().all()
        
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
    async def search_by_entity(
        db: AsyncSession,
        entity_type: str,
        entity_value: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Busca documentos que contengan una entidad específica
        
        Args:
            db: Sesión de base de datos async
            entity_type: Tipo de entidad (beneficiaries, amounts, contracts, etc.)
            entity_value: Valor a buscar
            limit: Límite de resultados
        
        Returns:
            Lista de documentos con la entidad
        """
        # Buscar en extracted_entities JSON
        stmt = select(AnalysisResult).join(BoletinDocument).filter(
            AnalysisResult.extracted_entities.isnot(None)
        ).limit(limit * 2)  # Obtener más para filtrar
        
        result = await db.execute(stmt)
        results = result.scalars().all()
        
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
    
    @staticmethod
    async def search_documents(
        query: str,
        technique: str = "hybrid",
        top_k: int = 10,
        rerank: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca documentos usando el RetrievalService (hybrid/semantic/keyword)
        
        Args:
            query: Consulta de búsqueda
            technique: Técnica de búsqueda (semantic, keyword, hybrid)
            top_k: Número de resultados a retornar
            rerank: Si se debe aplicar reranking
            filters: Filtros opcionales de metadata
        
        Returns:
            Lista de resultados de búsqueda
        """
        try:
            from app.services.retrieval_service import get_retrieval_service
            
            service = get_retrieval_service()
            
            if technique == 'hybrid':
                results = await service.hybrid_search(
                    query=query,
                    top_k=top_k,
                    rerank=rerank
                )
            elif technique == 'keyword':
                results = await service.keyword_search(
                    query=query,
                    top_k=top_k,
                    filters=filters
                )
            else:  # semantic
                results = await service.semantic_search(
                    query=query,
                    top_k=top_k,
                    filters=filters
                )
            
            # Convertir SearchResult objects a dicts
            return [
                {
                    'chunk_id': r.chunk_id,
                    'document_id': r.document_id,
                    'chunk_index': r.chunk_index,
                    'text': r.text,
                    'score': r.score,
                    'metadata': r.metadata or {}
                }
                for r in results
            ]
            
        except Exception as e:
            logger.error(f"Error in search_documents: {e}")
            return []


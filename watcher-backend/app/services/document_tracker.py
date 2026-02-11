"""
Document Tracker - Sistema de tracking de documentos requeridos por ley

Gestiona el inventario de documentos obligatorios por jurisdicción y su estado.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..db.models import RequiredDocument, ComplianceCheck, Jurisdiccion


class DocumentTracker:
    """Gestor de documentos requeridos"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.config_path = Path(__file__).parent.parent.parent / "config" / "required_documents.json"
        self._config = None
    
    def load_config(self) -> Dict[str, Any]:
        """Carga configuración de documentos requeridos"""
        if self._config is None:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        return self._config
    
    async def sync_required_documents(self) -> Dict[str, int]:
        """
        Sincroniza documentos requeridos desde config a la base de datos.
        Retorna conteo por jurisdicción.
        """
        config = self.load_config()
        synced_by_jurisdiction = {}
        
        for juris_code, juris_data in config.get("jurisdictions", {}).items():
            count = 0
            jurisdiction_id = juris_data.get("jurisdiction_id")
            
            for doc_def in juris_data.get("documents", []):
                # Buscar si ya existe (usando document_name como identificador único)
                stmt = select(RequiredDocument).filter(
                    and_(
                        RequiredDocument.document_name == doc_def["document_name"],
                        RequiredDocument.jurisdiccion_id == jurisdiction_id
                    )
                )
                result = await self.db.execute(stmt)
                existing = result.scalar_one_or_none()
                
                # Buscar el check asociado
                check = None
                if doc_def.get("check_code"):
                    stmt = select(ComplianceCheck).filter_by(check_code=doc_def["check_code"])
                    result = await self.db.execute(stmt)
                    check = result.scalar_one_or_none()
                
                if existing:
                    # Actualizar documento existente (solo metadata, no estado)
                    existing.document_name = doc_def["document_name"]
                    existing.expected_url = doc_def.get("expected_url")
                    existing.expected_format = doc_def["expected_format"]
                    existing.metadata_json = {
                        "description": doc_def.get("description"),
                        "notes": doc_def.get("notes"),
                        "frequency": doc_def.get("frequency"),
                        "applicable_laws": juris_data.get("applicable_laws", [])
                    }
                    existing.updated_at = datetime.utcnow()
                else:
                    # Crear nuevo documento requerido
                    new_doc = RequiredDocument(
                        check_id=check.id if check else None,
                        jurisdiccion_id=jurisdiction_id,
                        document_type=doc_def["document_type"],
                        document_name=doc_def["document_name"],
                        period=doc_def.get("period"),
                        expected_url=doc_def.get("expected_url"),
                        expected_format=doc_def["expected_format"],
                        status="missing",
                        metadata_json={
                            "description": doc_def.get("description"),
                            "notes": doc_def.get("notes"),
                            "frequency": doc_def.get("frequency"),
                            "applicable_laws": juris_data.get("applicable_laws", [])
                        }
                    )
                    self.db.add(new_doc)
                
                count += 1
            
            synced_by_jurisdiction[juris_code] = count
        
        await self.db.commit()
        return synced_by_jurisdiction
    
    async def get_documents_by_jurisdiction(
        self, 
        jurisdiccion_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[RequiredDocument]:
        """Obtiene documentos requeridos filtrados por jurisdicción y/o estado"""
        stmt = select(RequiredDocument)
        
        if jurisdiccion_id is not None:
            stmt = stmt.filter(RequiredDocument.jurisdiccion_id == jurisdiccion_id)
        
        if status:
            stmt = stmt.filter(RequiredDocument.status == status)
        
        stmt = stmt.order_by(
            RequiredDocument.jurisdiccion_id,
            RequiredDocument.document_type,
            RequiredDocument.period.desc()
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_jurisdiction_summary(self, jurisdiccion_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Obtiene resumen de documentos por jurisdicción.
        Retorna estadísticas de disponibilidad.
        """
        docs = await self.get_documents_by_jurisdiction(jurisdiccion_id)
        
        summary = {
            "total": len(docs),
            "missing": 0,
            "downloaded": 0,
            "processed": 0,
            "failed": 0,
            "by_type": {},
            "by_check": {},
            "coverage_percentage": 0.0
        }
        
        for doc in docs:
            summary[doc.status] = summary.get(doc.status, 0) + 1
            
            if doc.document_type not in summary["by_type"]:
                summary["by_type"][doc.document_type] = {
                    "total": 0,
                    "missing": 0,
                    "downloaded": 0,
                    "processed": 0
                }
            
            summary["by_type"][doc.document_type]["total"] += 1
            if doc.status == "missing":
                summary["by_type"][doc.document_type]["missing"] += 1
            elif doc.status == "downloaded":
                summary["by_type"][doc.document_type]["downloaded"] += 1
            elif doc.status == "processed":
                summary["by_type"][doc.document_type]["processed"] += 1
        
        # Calcular cobertura (procesados / total)
        if summary["total"] > 0:
            summary["coverage_percentage"] = (summary.get("processed", 0) / summary["total"]) * 100
        
        return summary
    
    async def mark_document_downloaded(
        self,
        document_id: int,
        local_path: str,
        file_size_bytes: int
    ) -> RequiredDocument:
        """Marca un documento como descargado"""
        stmt = select(RequiredDocument).filter(RequiredDocument.id == document_id)
        result = await self.db.execute(stmt)
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise ValueError(f"Document {document_id} not found")
        
        # Calcular hash del archivo
        file_hash = None
        if Path(local_path).exists():
            with open(local_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
        
        doc.status = "downloaded"
        doc.local_path = local_path
        doc.file_hash = file_hash
        doc.file_size_bytes = file_size_bytes
        doc.downloaded_at = datetime.utcnow()
        doc.last_checked = datetime.utcnow()
        doc.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(doc)
        
        return doc
    
    async def mark_document_processed(
        self,
        document_id: int,
        indexed_in_rag: bool = False,
        embedding_model: Optional[str] = None,
        num_chunks: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RequiredDocument:
        """Marca un documento como procesado con RAG"""
        stmt = select(RequiredDocument).filter(RequiredDocument.id == document_id)
        result = await self.db.execute(stmt)
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise ValueError(f"Document {document_id} not found")
        
        doc.status = "processed"
        doc.processed_at = datetime.utcnow()
        doc.indexed_in_rag = indexed_in_rag
        doc.embedding_model = embedding_model
        doc.num_chunks = num_chunks
        doc.last_checked = datetime.utcnow()
        
        if metadata:
            doc.metadata_json = {**(doc.metadata_json or {}), **metadata}
        
        doc.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(doc)
        
        return doc
    
    async def get_all_jurisdictions_overview(self) -> List[Dict[str, Any]]:
        """
        Obtiene overview de todas las jurisdicciones con sus documentos.
        Útil para el dashboard de compliance.
        """
        config = self.load_config()
        overview = []
        
        for juris_code, juris_data in config.get("jurisdictions", {}).items():
            jurisdiction_id = juris_data.get("jurisdiction_id")
            
            summary = await self.get_jurisdiction_summary(jurisdiction_id)
            
            overview.append({
                "jurisdiction_code": juris_code,
                "jurisdiction_id": jurisdiction_id,
                "jurisdiction_name": juris_data["jurisdiction_name"],
                "applicable_laws": juris_data.get("applicable_laws", []),
                "total_documents": summary["total"],
                "missing": summary.get("missing", 0),
                "downloaded": summary.get("downloaded", 0),
                "processed": summary.get("processed", 0),
                "failed": summary.get("failed", 0),
                "coverage_percentage": summary["coverage_percentage"],
                "by_type": summary["by_type"]
            })
        
        return overview

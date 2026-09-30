"""
Document Tracker - Sistema de tracking de documentos requeridos por ley

Gestiona el inventario de documentos obligatorios por jurisdicción y su estado.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ComplianceCheck, Jurisdiccion, RequiredDocument
from .file_type_taxonomy import UNKNOWN_FILE_TYPE, file_type_order

logger = logging.getLogger(__name__)

# jurisdiction_level (config) -> Jurisdiccion.tipo (DB)
LEVEL_TO_TIPO = {"nacion": "nacion", "provincia": "provincia", "municipio": "capital"}


class DocumentTracker:
    """Gestor de documentos requeridos"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.config_path = Path(__file__).parent.parent.parent / "config" / "required_documents.json"
        self._config = None

    def load_config(self) -> dict[str, Any]:
        """Carga configuración de documentos requeridos"""
        if self._config is None:
            with open(self.config_path, encoding='utf-8') as f:
                self._config = json.load(f)
        return self._config

    async def resolve_jurisdiction_id(self, juris_data: dict[str, Any]) -> int | None:
        """
        Resuelve el id real en `jurisdicciones` para una jurisdicción del config.

        Busca primero por el id del config (si el nombre coincide) y luego por nombre.
        Devuelve None si la fila no existe — nunca se usa None como "sin filtro".
        """
        config_id = juris_data.get("jurisdiction_id")
        name = juris_data["jurisdiction_name"]

        if config_id is not None:
            row = await self.db.get(Jurisdiccion, config_id)
            if row is not None and row.nombre == name:
                return row.id

        result = await self.db.execute(select(Jurisdiccion.id).filter(Jurisdiccion.nombre == name))
        found = result.scalar_one_or_none()
        if found is not None and config_id is not None and found != config_id:
            logger.warning(
                "Jurisdicción %r existe con id=%s pero el config dice %s; se usa el de la DB",
                name, found, config_id,
            )
        return found

    async def ensure_jurisdiction(self, juris_data: dict[str, Any]) -> int:
        """Get-or-create de la fila `Jurisdiccion` (seed idempotente, p. ej. Nación id=100)."""
        existing = await self.resolve_jurisdiction_id(juris_data)
        if existing is not None:
            return existing

        config_id = juris_data.get("jurisdiction_id")
        if config_id is not None and await self.db.get(Jurisdiccion, config_id) is not None:
            # El id del config está tomado por otra jurisdicción: crear con id autogenerado
            logger.warning("jurisdicciones.id=%s ocupado; %r se crea con id autogenerado",
                           config_id, juris_data["jurisdiction_name"])
            config_id = None

        row = Jurisdiccion(
            nombre=juris_data["jurisdiction_name"],
            tipo=LEVEL_TO_TIPO.get(juris_data.get("jurisdiction_level", ""), "provincia"),
            extra_data={"jurisdiction_code": juris_data.get("jurisdiction_code")},
        )
        if config_id is not None:
            row.id = config_id
        self.db.add(row)
        await self.db.flush()

        if config_id is not None and self.db.bind.dialect.name == "postgresql":
            # Un id explícito no avanza la secuencia SERIAL; alinearla para no colisionar
            await self.db.execute(text(
                "SELECT setval(pg_get_serial_sequence('jurisdicciones', 'id'), "
                "(SELECT MAX(id) FROM jurisdicciones))"
            ))
        return row.id

    async def sync_required_documents(self) -> dict[str, int]:
        """
        Sincroniza documentos requeridos desde config a la base de datos.
        Asegura que cada jurisdicción exista en `jurisdicciones` y adopta filas
        huérfanas (`jurisdiccion_id` NULL de syncs viejos) por nombre de documento.
        Retorna conteo por jurisdicción.
        """
        config = self.load_config()
        synced_by_jurisdiction = {}

        for juris_code, juris_data in config.get("jurisdictions", {}).items():
            count = 0
            jurisdiction_id = await self.ensure_jurisdiction(juris_data)

            doc_names = [d["document_name"] for d in juris_data.get("documents", [])]
            if doc_names:
                await self.db.execute(
                    update(RequiredDocument)
                    .where(RequiredDocument.jurisdiccion_id.is_(None))
                    .where(RequiredDocument.document_name.in_(doc_names))
                    .values(jurisdiccion_id=jurisdiction_id)
                )

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
        jurisdiccion_id: int | None = None,
        status: str | None = None
    ) -> list[RequiredDocument]:
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

    async def get_jurisdiction_summary(self, jurisdiccion_id: int | None = None) -> dict[str, Any]:
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
            "by_file_type": {},
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

            # Eje primario: tipo de ARCHIVO, con la categoría legal como mapping.
            # Cada documento cae en un solo bucket, así que los conteos cierran
            # contra `total` y contra la suma de `legal_categories`.
            file_type = doc.expected_format or UNKNOWN_FILE_TYPE
            bucket = summary["by_file_type"].setdefault(file_type, {
                "total": 0,
                "missing": 0,
                "downloaded": 0,
                "processed": 0,
                "legal_categories": {}
            })
            bucket["total"] += 1
            if doc.status == "missing":
                bucket["missing"] += 1
            elif doc.status == "downloaded":
                bucket["downloaded"] += 1
            elif doc.status == "processed":
                bucket["processed"] += 1
            bucket["legal_categories"][doc.document_type] = (
                bucket["legal_categories"].get(doc.document_type, 0) + 1
            )

        # Orden estable de presentación: la taxonomía primero.
        summary["by_file_type"] = {
            file_type: summary["by_file_type"][file_type]
            for file_type in sorted(summary["by_file_type"], key=file_type_order)
        }

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
        embedding_model: str | None = None,
        num_chunks: int | None = None,
        metadata: dict[str, Any] | None = None
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

    async def get_all_jurisdictions_overview(self) -> list[dict[str, Any]]:
        """
        Obtiene overview de todas las jurisdicciones con sus documentos.
        Útil para el dashboard de compliance.
        """
        config = self.load_config()
        overview = []

        for juris_key, juris_data in config.get("jurisdictions", {}).items():
            jurisdiction_id = await self.resolve_jurisdiction_id(juris_data)

            if jurisdiction_id is None:
                # Sin fila en DB (inventario sin sync): cero, no "todos los docs"
                summary = {"total": 0, "coverage_percentage": 0.0, "by_type": {}, "by_file_type": {}}
            else:
                summary = await self.get_jurisdiction_summary(jurisdiction_id)

            overview.append({
                "jurisdiction_key": juris_key,
                "jurisdiction_code": juris_data.get("jurisdiction_code", juris_key),
                "jurisdiction_level": juris_data.get("jurisdiction_level"),
                "jurisdiction_id": jurisdiction_id,
                "jurisdiction_name": juris_data["jurisdiction_name"],
                "applicable_laws": juris_data.get("applicable_laws", []),
                "total_documents": summary["total"],
                "missing": summary.get("missing", 0),
                "downloaded": summary.get("downloaded", 0),
                "processed": summary.get("processed", 0),
                "failed": summary.get("failed", 0),
                "coverage_percentage": summary["coverage_percentage"],
                "by_type": summary["by_type"],
                "by_file_type": summary.get("by_file_type", {})
            })

        return overview

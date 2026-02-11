"""
Endpoints para sistema de Compliance
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date, datetime
import os
from pathlib import Path

from ....db.database import get_db
from ....db.models import ComplianceCheck, CheckResult, Evidence, Jurisdiccion, RequiredDocument
from sqlalchemy import select, desc, func
from ....schemas.compliance import (
    ComplianceCheckResponse,
    CheckResultResponse,
    CheckResultWithDetails,
    EvidenceResponse,
    ComplianceScorecardResponse,
    ChecksSyncResponse,
    RequiredDocumentResponse,
    JurisdictionDocumentsSummary,
    DocumentsOverviewResponse,
    DocumentUpdateRequest
)
from ....services.compliance_engine import ComplianceEngine
from ....services.document_tracker import DocumentTracker
from app.services.extractors import ExtractorRegistry


router = APIRouter()


# ============================================================================
# COMPLIANCE CHECKS ENDPOINTS
# ============================================================================

@router.get("/checks", response_model=List[ComplianceCheckResponse])
@router.get("/checks/", response_model=List[ComplianceCheckResponse])
async def get_compliance_checks(
    active_only: bool = Query(True, description="Solo checks activos"),
    priority: Optional[str] = Query(None, description="Filtrar por prioridad"),
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene la lista de compliance checks.
    
    Parámetros:
    - active_only: Solo checks activos (default: True)
    - priority: Filtrar por prioridad (critical, high, medium, low)
    - category: Filtrar por categoría (presupuesto, deuda, empleo, etc.)
    """
    from sqlalchemy import select
    
    stmt = select(ComplianceCheck)
    
    if active_only:
        stmt = stmt.filter(ComplianceCheck.is_active == True)
    
    if priority:
        stmt = stmt.filter(ComplianceCheck.priority == priority)
    
    if category:
        stmt = stmt.filter(ComplianceCheck.category == category)
    
    stmt = stmt.order_by(ComplianceCheck.priority.desc(), ComplianceCheck.category)
    result = await db.execute(stmt)
    checks = result.scalars().all()
    
    return checks


@router.get("/checks/{check_id}", response_model=ComplianceCheckResponse)
async def get_compliance_check(
    check_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene un check específico por ID"""
    from sqlalchemy import select
    
    stmt = select(ComplianceCheck).filter(ComplianceCheck.id == check_id)
    result = await db.execute(stmt)
    check = result.scalar_one_or_none()
    
    if not check:
        raise HTTPException(status_code=404, detail="Check no encontrado")
    
    return check


@router.get("/checks/code/{check_code}", response_model=ComplianceCheckResponse)
async def get_compliance_check_by_code(
    check_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene un check específico por código"""
    from sqlalchemy import select
    
    stmt = select(ComplianceCheck).filter(ComplianceCheck.check_code == check_code)
    result = await db.execute(stmt)
    check = result.scalar_one_or_none()
    
    if not check:
        raise HTTPException(status_code=404, detail="Check no encontrado")
    
    return check


# ============================================================================
# CHECK RESULTS ENDPOINTS
# ============================================================================

@router.get("/results", response_model=List[CheckResultResponse])
@router.get("/results/", response_model=List[CheckResultResponse])
async def get_check_results(
    check_id: Optional[int] = Query(None, description="Filtrar por check"),
    jurisdiccion_id: Optional[int] = Query(None, description="Filtrar por jurisdicción"),
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene resultados de checks.
    
    Parámetros:
    - check_id: ID del check
    - jurisdiccion_id: ID de la jurisdicción
    - status: Estado (pass, warn, fail, unknown)
    - limit: Número máximo de resultados
    """
    from sqlalchemy import select
    
    stmt = select(CheckResult)
    
    if check_id:
        stmt = stmt.filter(CheckResult.check_id == check_id)
    
    if jurisdiccion_id:
        stmt = stmt.filter(CheckResult.jurisdiccion_id == jurisdiccion_id)
    
    if status:
        stmt = stmt.filter(CheckResult.status == status)
    
    stmt = stmt.order_by(CheckResult.evaluation_date.desc()).limit(limit)
    result = await db.execute(stmt)
    results = result.scalars().all()
    
    return results


@router.get("/results/{result_id}", response_model=CheckResultWithDetails)
async def get_check_result(
    result_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene un resultado específico con detalles y evidencias"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    stmt = select(CheckResult).options(
        selectinload(CheckResult.check),
        selectinload(CheckResult.evidences)
    ).filter(CheckResult.id == result_id)
    result = await db.execute(stmt)
    check_result = result.scalar_one_or_none()
    
    if not check_result:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")
    
    return check_result


# ============================================================================
# EVIDENCE ENDPOINTS
# ============================================================================

@router.get("/results/{result_id}/evidence", response_model=List[EvidenceResponse])
async def get_check_evidence(
    result_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene todas las evidencias de un resultado de check.
    
    Permite trazabilidad completa de cómo se llegó a un resultado.
    """
    from sqlalchemy import select
    
    # Verificar que el resultado existe
    stmt = select(CheckResult).filter(CheckResult.id == result_id)
    result = await db.execute(stmt)
    check_result = result.scalar_one_or_none()
    if not check_result:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")
    
    stmt = select(Evidence).filter(
        Evidence.check_result_id == result_id
    ).order_by(Evidence.captured_at.desc())
    result = await db.execute(stmt)
    evidences = result.scalars().all()
    
    return evidences


@router.get("/evidence/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence_detail(
    evidence_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene detalle de una evidencia específica"""
    from sqlalchemy import select
    
    stmt = select(Evidence).filter(Evidence.id == evidence_id)
    result = await db.execute(stmt)
    evidence = result.scalar_one_or_none()
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada")
    
    return evidence


# ============================================================================
# SCORECARD ENDPOINT
# ============================================================================

@router.get("/scorecard", response_model=ComplianceScorecardResponse)
@router.get("/scorecard/", response_model=ComplianceScorecardResponse)
async def get_compliance_scorecard(
    jurisdiccion_id: Optional[int] = Query(None, description="ID de jurisdicción"),
    db: AsyncSession = Depends(get_db)
):
    """
    Genera el scorecard de compliance completo.
    
    Incluye:
    - Score general ponderado
    - Desglose por checks
    - Red flags (checks en estado FAIL o WARN)
    - Nivel de compliance (excellent, good, acceptable, deficient)
    
    Parámetros:
    - jurisdiccion_id: Si se especifica, genera scorecard para esa jurisdicción
    """
    engine = ComplianceEngine(db)
    scorecard = await engine.get_scorecard(jurisdiccion_id=jurisdiccion_id)
    
    return scorecard


# ============================================================================
# EXECUTION ENDPOINTS
# ============================================================================

@router.post("/execute")
@router.post("/execute/")
async def execute_compliance_checks(
    check_codes: Optional[List[str]] = Query(None, description="Códigos de checks a ejecutar"),
    jurisdiccion_id: Optional[int] = Query(None, description="ID de jurisdicción"),
    db: AsyncSession = Depends(get_db)
):
    """
    Ejecuta checks de compliance.
    
    Parámetros:
    - check_codes: Lista de códigos de checks a ejecutar. Si no se especifica, ejecuta todos.
    - jurisdiccion_id: ID de la jurisdicción a evaluar
    
    Nota: Por ahora, los checks retornan estado UNKNOWN hasta que se implementen
    los validadores específicos.
    """
    from sqlalchemy import select
    
    engine = ComplianceEngine(db)
    
    # Obtener jurisdicción si se especificó
    jurisdiccion = None
    if jurisdiccion_id:
        stmt = select(Jurisdiccion).filter(Jurisdiccion.id == jurisdiccion_id)
        result = await db.execute(stmt)
        jurisdiccion = result.scalar_one_or_none()
        if not jurisdiccion:
            raise HTTPException(status_code=404, detail="Jurisdicción no encontrada")
    
    # Obtener checks a ejecutar
    if check_codes:
        stmt = select(ComplianceCheck).filter(
            ComplianceCheck.check_code.in_(check_codes),
            ComplianceCheck.is_active == True
        )
        result = await db.execute(stmt)
        checks = result.scalars().all()
        
        if not checks:
            raise HTTPException(status_code=404, detail="No se encontraron checks con esos códigos")
    else:
        checks = await engine.get_all_checks(active_only=True)
    
    # Ejecutar checks
    results = []
    for check in checks:
        result = await engine.execute_check(check, jurisdiccion)
        results.append({
            "check_code": check.check_code,
            "check_name": check.check_name,
            "result_id": result.id,
            "status": result.status
        })
    
    return {
        "success": True,
        "executed_checks": len(results),
        "results": results,
        "message": "Checks ejecutados. Nota: Validadores específicos aún no implementados, todos retornan UNKNOWN."
    }


# ============================================================================
# SYNC ENDPOINT
# ============================================================================

@router.post("/sync", response_model=ChecksSyncResponse)
@router.post("/sync/", response_model=ChecksSyncResponse)
async def sync_checks_from_config(
    db: AsyncSession = Depends(get_db)
):
    """
    Sincroniza los checks desde el archivo config/checks.json a la base de datos.
    
    Útil cuando se actualizan las definiciones de checks en el JSON.
    """
    try:
        engine = ComplianceEngine(db)
        synced_count = await engine.sync_checks_to_database()
        
        # Obtener summary de checks por prioridad
        checks = await engine.get_all_checks(active_only=True)
        summary = {}
        for check in checks:
            summary[check.priority] = summary.get(check.priority, 0) + 1
        
        return {
            "success": True,
            "synced_count": synced_count,
            "message": f"Se sincronizaron {synced_count} checks desde el archivo de configuración",
            "checks_summary": summary
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al sincronizar checks: {str(e)}"
        )


# ============================================================================
# STATS ENDPOINT
# ============================================================================

@router.get("/stats")
@router.get("/stats/")
async def get_compliance_stats(
    jurisdiccion_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene estadísticas generales del sistema de compliance.
    
    Incluye conteo de checks por categoría, prioridad, resultados por estado, etc.
    """
    from sqlalchemy import select
    
    engine = ComplianceEngine(db)
    
    # Conteo de checks por prioridad
    checks = await engine.get_all_checks(active_only=True)
    checks_by_priority = {}
    checks_by_category = {}
    
    for check in checks:
        checks_by_priority[check.priority] = checks_by_priority.get(check.priority, 0) + 1
        if check.category:
            checks_by_category[check.category] = checks_by_category.get(check.category, 0) + 1
    
    # Conteo de resultados por estado
    stmt = select(CheckResult)
    if jurisdiccion_id:
        stmt = stmt.filter(CheckResult.jurisdiccion_id == jurisdiccion_id)
    
    result = await db.execute(stmt)
    results = result.scalars().all()
    results_by_status = {}
    for r in results:
        results_by_status[r.status] = results_by_status.get(r.status, 0) + 1
    
    # Calcular compliance score
    score_data = await engine.calculate_compliance_score(jurisdiccion_id)
    
    return {
        "total_checks": len(checks),
        "checks_by_priority": checks_by_priority,
        "checks_by_category": checks_by_category,
        "total_results": len(results),
        "results_by_status": results_by_status,
        "compliance_score": score_data["score"],
        "compliance_level": engine._get_compliance_level(score_data["score"]),
        "jurisdiccion_id": jurisdiccion_id
    }


# ============================================================================
# REQUIRED DOCUMENTS ENDPOINTS
# ============================================================================

@router.post("/documents/sync")
@router.post("/documents/sync/")
async def sync_required_documents(
    db: AsyncSession = Depends(get_db)
):
    """
    Sincroniza documentos requeridos desde config/required_documents.json a la DB.
    
    Carga el inventario de documentos que cada jurisdicción debe tener según las leyes.
    """
    try:
        tracker = DocumentTracker(db)
        synced_by_jurisdiction = await tracker.sync_required_documents()
        
        total = sum(synced_by_jurisdiction.values())
        
        return {
            "success": True,
            "total_synced": total,
            "by_jurisdiction": synced_by_jurisdiction,
            "message": f"Se sincronizaron {total} documentos requeridos"
        }
    except Exception as e:
        import traceback
        error_detail = f"Error al sincronizar documentos: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log to console
        raise HTTPException(
            status_code=500,
            detail=f"Error al sincronizar documentos: {str(e)}"
        )


@router.get("/documents", response_model=List[RequiredDocumentResponse])
@router.get("/documents/", response_model=List[RequiredDocumentResponse])
async def get_required_documents(
    jurisdiccion_id: Optional[int] = Query(None, description="Filtrar por jurisdicción"),
    status: Optional[str] = Query(None, description="Filtrar por estado (missing/downloaded/processed/failed)"),
    document_type: Optional[str] = Query(None, description="Filtrar por tipo de documento"),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene lista de documentos requeridos con filtros.
    
    Permite ver qué documentos se necesitan, cuáles están descargados, y cuáles procesados.
    """
    from sqlalchemy import select
    
    stmt = select(RequiredDocument)
    
    if jurisdiccion_id is not None:
        stmt = stmt.filter(RequiredDocument.jurisdiccion_id == jurisdiccion_id)
    
    if status:
        stmt = stmt.filter(RequiredDocument.status == status)
    
    if document_type:
        stmt = stmt.filter(RequiredDocument.document_type == document_type)
    
    stmt = stmt.order_by(
        RequiredDocument.jurisdiccion_id,
        RequiredDocument.document_type,
        RequiredDocument.period.desc()
    )
    
    result = await db.execute(stmt)
    documents = result.scalars().all()
    
    return documents


@router.get("/documents/overview", response_model=DocumentsOverviewResponse)
@router.get("/documents/overview/")
async def get_documents_overview(
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene overview completo de documentos por todas las jurisdicciones.
    
    Muestra cobertura, documentos faltantes, y estado general del inventario.
    """
    tracker = DocumentTracker(db)
    jurisdictions_overview = await tracker.get_all_jurisdictions_overview()
    
    # Calcular totales directamente de la DB para evitar inconsistencias
    total_stmt = select(func.count(RequiredDocument.id)).select_from(RequiredDocument)
    total_result = await db.execute(total_stmt)
    total_docs = total_result.scalar() or 0
    
    missing_stmt = select(func.count(RequiredDocument.id)).where(RequiredDocument.status == "missing")
    missing_result = await db.execute(missing_stmt)
    total_missing = missing_result.scalar() or 0
    
    processed_stmt = select(func.count(RequiredDocument.id)).where(RequiredDocument.status == "processed")
    processed_result = await db.execute(processed_stmt)
    total_processed = processed_result.scalar() or 0
    
    overall_coverage = (total_processed / total_docs * 100) if total_docs > 0 else 0.0
    
    return {
        "jurisdictions": jurisdictions_overview,
        "total_documents": total_docs,
        "total_missing": total_missing,
        "total_processed": total_processed,
        "overall_coverage": round(overall_coverage, 2)
    }


@router.get("/documents/jurisdiction/{jurisdiccion_id}")
async def get_jurisdiction_documents_summary(
    jurisdiccion_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene resumen de documentos para una jurisdicción específica.
    
    Incluye estadísticas de cobertura y desglose por tipo de documento.
    """
    tracker = DocumentTracker(db)
    summary = await tracker.get_jurisdiction_summary(jurisdiccion_id)
    
    # Obtener los documentos
    docs = await tracker.get_documents_by_jurisdiction(jurisdiccion_id)
    
    return {
        "summary": summary,
        "documents": [
            {
                "id": doc.id,
                "document_name": doc.document_name,
                "document_type": doc.document_type,
                "period": doc.period,
                "status": doc.status,
                "expected_format": doc.expected_format,
                "expected_url": doc.expected_url,
                "local_path": doc.local_path,
                "downloaded_at": doc.downloaded_at.isoformat() if doc.downloaded_at else None,
                "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
                "indexed_in_rag": doc.indexed_in_rag,
                "metadata": doc.metadata_json
            }
            for doc in docs
        ]
    }


@router.patch("/documents/{document_id}/mark-downloaded")
async def mark_document_downloaded(
    document_id: int,
    local_path: str = Query(..., description="Path al archivo descargado"),
    file_size_bytes: int = Query(..., description="Tamaño del archivo en bytes"),
    db: AsyncSession = Depends(get_db)
):
    """Marca un documento como descargado"""
    tracker = DocumentTracker(db)
    doc = await tracker.mark_document_downloaded(document_id, local_path, file_size_bytes)
    
    return {
        "success": True,
        "document_id": doc.id,
        "status": doc.status,
        "file_hash": doc.file_hash,
        "message": f"Documento '{doc.document_name}' marcado como descargado"
    }


@router.patch("/documents/{document_id}/mark-processed")
async def mark_document_processed(
    document_id: int,
    update_data: DocumentUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Marca un documento como procesado con RAG"""
    tracker = DocumentTracker(db)
    doc = await tracker.mark_document_processed(
        document_id=document_id,
        indexed_in_rag=update_data.indexed_in_rag or False,
        embedding_model=update_data.embedding_model,
        num_chunks=update_data.num_chunks,
        metadata=update_data.metadata
    )
    
    return {
        "success": True,
        "document_id": doc.id,
        "status": doc.status,
        "indexed_in_rag": doc.indexed_in_rag,
        "message": f"Documento '{doc.document_name}' marcado como procesado"
    }


@router.patch("/documents/{document_id}/update-url")
async def update_document_url(
    document_id: int,
    expected_url: str = Query(..., description="Nueva URL del documento"),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza la URL esperada de un documento"""
    from sqlalchemy import select
    
    stmt = select(RequiredDocument).filter(RequiredDocument.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail=f"Documento {document_id} no encontrado")
    
    doc.expected_url = expected_url
    doc.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(doc)
    
    return {
        "success": True,
        "document_id": doc.id,
        "document_name": doc.document_name,
        "expected_url": doc.expected_url,
        "message": f"URL actualizada para '{doc.document_name}'"
    }


@router.post("/documents/{document_id}/upload")
async def upload_document_file(
    document_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Sube un archivo para un documento requerido.
    Guarda el archivo localmente y marca el documento como descargado.
    """
    from sqlalchemy import select
    import hashlib
    
    # 1. Obtener documento
    stmt = select(RequiredDocument).filter(RequiredDocument.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail=f"Documento {document_id} no encontrado")
    
    # 2. Crear directorio si no existe
    upload_dir = Path("data/uploaded_documents")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. Generar nombre de archivo seguro
    file_extension = Path(file.filename or "document").suffix or f".{doc.expected_format}"
    safe_filename = f"{doc.document_type}_{doc.period or 'unknown'}_{document_id}{file_extension}"
    file_path = upload_dir / safe_filename
    
    # 4. Guardar archivo
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 5. Calcular hash
    file_hash = hashlib.sha256(content).hexdigest()
    
    # 6. Actualizar documento en DB
    doc.status = "downloaded"
    doc.local_path = str(file_path)
    doc.file_hash = file_hash
    doc.file_size_bytes = len(content)
    doc.downloaded_at = datetime.utcnow()
    doc.last_checked = datetime.utcnow()
    doc.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(doc)
    
    return {
        "success": True,
        "document_id": doc.id,
        "document_name": doc.document_name,
        "local_path": doc.local_path,
        "file_hash": doc.file_hash,
        "file_size_bytes": doc.file_size_bytes,
        "status": doc.status,
        "message": f"Archivo subido correctamente para '{doc.document_name}'"
    }


# ============================================================================
# DOCUMENT PROCESSING PIPELINE ENDPOINTS
# ============================================================================

@router.post("/documents/{document_id}/extract-text")
async def extract_document_text(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Paso 1: Extrae texto de un documento subido.
    Retorna preview del texto, número de páginas, tokens, etc.
    """
    stmt = select(RequiredDocument).filter(RequiredDocument.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail=f"Documento {document_id} no encontrado")
    
    if not doc.local_path or doc.status == "missing":
        raise HTTPException(
            status_code=400, 
            detail="El documento debe estar subido antes de extraer texto"
        )
    
    # Extraer texto
    extraction_result = await ExtractorRegistry.extract(Path(doc.local_path))
    
    if not extraction_result.success:
        raise HTTPException(
            status_code=500,
            detail=f"Error al extraer texto: {extraction_result.error}"
        )
    
    # Preparar resultado
    result_data = {
        "num_pages": extraction_result.stats.total_pages,
        "total_chars": extraction_result.stats.total_chars,
        "total_tokens": extraction_result.stats.total_tokens,
        "preview": extraction_result.full_text[:1000] + "..." if len(extraction_result.full_text) > 1000 else extraction_result.full_text,
        "extracted_at": extraction_result.extracted_at.isoformat()
    }
    
    # Guardar metadata de extracción
    doc.metadata_json = {
        **(doc.metadata_json or {}),
        "extraction": {
            "num_pages": result_data["num_pages"],
            "total_chars": result_data["total_chars"],
            "total_tokens": result_data["total_tokens"],
            "extracted_at": result_data["extracted_at"]
        }
    }
    doc.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(doc)
    
    return {
        "success": True,
        "document_id": doc.id,
        "document_name": doc.document_name,
        "extraction": result_data,
        "message": f"Texto extraído correctamente: {result_data['num_pages']} páginas, {result_data['total_tokens']} tokens"
    }


@router.post("/documents/{document_id}/index-embeddings")
async def index_document_embeddings(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Paso 2: Genera embeddings para el documento.
    Divide en chunks y crea vectores para búsqueda semántica.
    """
    import google.generativeai as genai
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"🔵 Iniciando indexación de embeddings para documento {document_id}")
    
    stmt = select(RequiredDocument).filter(RequiredDocument.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc:
        logger.error(f"❌ Documento {document_id} no encontrado")
        raise HTTPException(status_code=404, detail=f"Documento {document_id} no encontrado")
    
    logger.info(f"📄 Documento encontrado: {doc.document_name}")
    
    if not doc.local_path or doc.status == "missing":
        logger.error(f"❌ Documento sin path local o missing: {doc.status}")
        raise HTTPException(
            status_code=400,
            detail="El documento debe estar subido y con texto extraído"
        )
    
    # Verificar API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("❌ GOOGLE_API_KEY no configurada")
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_API_KEY no configurada"
        )
    
    logger.info("✅ API key encontrada")
    
    # Configurar Google AI
    try:
        genai.configure(api_key=api_key)
        logger.info("✅ Google AI configurado")
    except Exception as e:
        logger.error(f"❌ Error configurando Google AI: {e}")
        raise HTTPException(status_code=500, detail=f"Error configurando Google AI: {str(e)}")
    
    # Extraer texto primero
    logger.info("📖 Extrayendo texto del PDF...")
    
    try:
        extraction_result = await ExtractorRegistry.extract(Path(doc.local_path))
        logger.info(f"✅ Texto extraído: {extraction_result.stats.total_pages} páginas")
    except Exception as e:
        logger.error(f"❌ Error extrayendo texto: {e}")
        raise HTTPException(status_code=500, detail=f"Error al extraer texto: {str(e)}")
    
    if not extraction_result.success:
        logger.error(f"❌ Extracción falló: {extraction_result.error}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al extraer texto: {extraction_result.error}"
        )
    
    # Generar embeddings con Google AI y almacenar en ChromaDB
    logger.info("🔄 Generando embeddings con Google AI...")
    try:
        from app.services.embedding_service import get_embedding_service
        embedding_svc = get_embedding_service()

        # Almacenar en ChromaDB (genera embeddings internamente)
        chromadb_result = await embedding_svc.add_document(
            document_id=f"compliance_doc_{document_id}",
            content=extraction_result.full_text,
            metadata={
                "document_id": str(document_id),
                "document_name": doc.document_name,
                "jurisdiction": doc.jurisdiction_code or "",
                "source": "compliance",
            },
        )
        if not chromadb_result["success"]:
            raise Exception(f"ChromaDB storage failed: {chromadb_result.get('error')}")

        num_chunks = chromadb_result["chunks_created"]
        logger.info(f"✅ Embeddings generados y almacenados en ChromaDB: {num_chunks} chunks")

        embeddings_result = {
            "success": True,
            "model": embedding_svc.google_model,
            "num_chunks": num_chunks,
            "total_tokens": extraction_result.stats.total_tokens,
            "indexed_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error generando/almacenando embeddings: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al generar embeddings: {str(e)}")
    
    # Actualizar documento como procesado
    logger.info("💾 Actualizando documento en DB...")
    doc.status = "processed"
    doc.processed_at = datetime.utcnow()
    doc.indexed_in_rag = True
    doc.embedding_model = embeddings_result["model"]
    doc.num_chunks = embeddings_result["num_chunks"]
    doc.metadata_json = {
        **(doc.metadata_json or {}),
        "embeddings": {
            "model": embeddings_result["model"],
            "num_chunks": embeddings_result["num_chunks"],
            "total_tokens": embeddings_result["total_tokens"],
            "indexed_at": embeddings_result["indexed_at"]
        }
    }
    doc.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(doc)
    
    logger.info(f"✅ Documento {document_id} procesado completamente")
    
    return {
        "success": True,
        "document_id": doc.id,
        "document_name": doc.document_name,
        "status": doc.status,
        "embeddings": {
            "model": embeddings_result["model"],
            "num_chunks": embeddings_result["num_chunks"],
            "total_tokens": embeddings_result["total_tokens"],
            "indexed_at": embeddings_result["indexed_at"]
        },
        "message": f"Embeddings generados: {embeddings_result['num_chunks']} chunks indexados"
    }


@router.get("/documents/{document_id}/processing-status")
async def get_document_processing_status(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el estado de procesamiento de un documento.
    Muestra qué pasos se completaron y qué falta.
    """
    stmt = select(RequiredDocument).filter(RequiredDocument.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail=f"Documento {document_id} no encontrado")
    
    # Determinar pasos completados
    steps = {
        "uploaded": doc.status in ["downloaded", "processed"],
        "text_extracted": doc.metadata_json and "extraction" in (doc.metadata_json or {}),
        "embeddings_generated": doc.status == "processed" and doc.indexed_in_rag,
    }
    
    # Preparar summary
    summary = {
        "document_id": doc.id,
        "document_name": doc.document_name,
        "status": doc.status,
        "indexed_in_rag": doc.indexed_in_rag,
        "metadata": doc.metadata_json
    }
    
    return {
        **summary,
        "steps": steps,
        "next_step": (
            "extract_text" if steps["uploaded"] and not steps["text_extracted"]
            else "index_embeddings" if steps["text_extracted"] and not steps["embeddings_generated"]
            else "completed" if all(steps.values())
            else "upload"
        )
    }

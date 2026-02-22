"""
🗂️ BOLETINES SELECTOR API
Endpoints para listar y seleccionar boletines para análisis
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

BOLETINES_DIR = settings.BOLETINES_DIR

class BoletinInfo(BaseModel):
    """Información de un boletín"""
    filename: str
    date: str
    section: int
    display_name: str
    file_size: int
    last_modified: str
    is_critical: Optional[bool] = False
    red_flags_count: Optional[int] = 0

class BoletinesResponse(BaseModel):
    """Respuesta con lista de boletines"""
    total_count: int
    boletines: List[BoletinInfo]
    month: str
    year: int

def parse_filename(filename: str) -> Dict[str, any]:
    """
    Parsea el nombre del archivo para extraer información
    Formato: YYYYMMDD_N_Secc.pdf
    """
    try:
        base_name = filename.replace('.pdf', '')
        parts = base_name.split('_')
        
        if len(parts) >= 3:
            date_str = parts[0]  # YYYYMMDD
            section = int(parts[1])  # N
            
            # Parsear fecha
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            
            date_obj = datetime(year, month, day)
            
            return {
                'date': date_obj,
                'section': section,
                'date_str': date_obj.strftime('%Y-%m-%d'),
                'display_date': date_obj.strftime('%d/%m/%Y'),
                'valid': True
            }
    except Exception as e:
        logger.warning(f"Error parseando archivo {filename}: {e}")
    
    return {'valid': False}

def get_section_name(section: int) -> str:
    """Retorna el nombre descriptivo de la sección"""
    sections = {
        1: "Designaciones y Decretos",
        2: "Compras y Contrataciones", 
        3: "Subsidios y Transferencias",
        4: "Obras Públicas",
        5: "Notificaciones Judiciales"
    }
    return sections.get(section, f"Sección {section}")

@router.get("/boletines/list", response_model=BoletinesResponse)
async def list_boletines(
    month: Optional[int] = Query(8, description="Mes (1-12)"),
    year: Optional[int] = Query(2025, description="Año"),
    section: Optional[int] = Query(None, description="Filtrar por sección (1-5)"),
    include_red_flags: bool = Query(False, description="Incluir información de red flags")
):
    """
    Lista todos los boletines disponibles para análisis
    """
    try:
        if not BOLETINES_DIR.exists():
            raise HTTPException(status_code=404, detail="Directorio de boletines no encontrado")
        
        boletines = []
        
        # Obtener lista de archivos PDF
        pdf_files = list(BOLETINES_DIR.glob("*.pdf"))
        
        for pdf_file in pdf_files:
            # Parsear información del archivo
            file_info = parse_filename(pdf_file.name)
            
            if not file_info['valid']:
                continue
            
            # Filtrar por mes y año
            if file_info['date'].month != month or file_info['date'].year != year:
                continue
            
            # Filtrar por sección si se especifica
            if section is not None and file_info['section'] != section:
                continue
            
            # Información del archivo
            stat = pdf_file.stat()
            
            # Crear display name
            section_name = get_section_name(file_info['section'])
            display_name = f"{file_info['display_date']} - {section_name}"
            
            boletin_info = BoletinInfo(
                filename=pdf_file.name,
                date=file_info['date_str'],
                section=file_info['section'],
                display_name=display_name,
                file_size=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                is_critical=False,  # TODO: Integrar con análisis DS Lab
                red_flags_count=0   # TODO: Integrar con análisis DS Lab
            )
            
            boletines.append(boletin_info)
        
        # Ordenar por fecha y sección
        boletines.sort(key=lambda x: (x.date, x.section))
        
        # Si se solicita información de red flags, cargarla
        if include_red_flags:
            boletines = await enrich_with_red_flags(boletines)
        
        return BoletinesResponse(
            total_count=len(boletines),
            boletines=boletines,
            month=f"{year}-{month:02d}",
            year=year
        )
    
    except Exception as e:
        logger.error(f"Error listando boletines: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

async def enrich_with_red_flags(boletines: List[BoletinInfo]) -> List[BoletinInfo]:
    """
    Enriquece la lista de boletines con información de red flags reales del DS Lab
    """
    try:
        # Cargar datos reales del DS Lab
        sync_file = settings.DATA_DIR / "reports" / "monolith_sync.json"
        
        if not sync_file.exists():
            logger.warning(f"Archivo de sincronización no encontrado: {sync_file}")
            return boletines
        
        with open(sync_file, 'r', encoding='utf-8') as f:
            sync_data = json.load(f)
        
        red_flags_by_document = sync_data.get('red_flags_by_document', {})
        critical_documents = sync_data.get('critical_documents', [])
        
        # Enriquecer cada boletín con datos reales
        for boletin in boletines:
            if boletin.filename in red_flags_by_document:
                doc_data = red_flags_by_document[boletin.filename]
                boletin.red_flags_count = doc_data.get('red_flags_count', 0)
                boletin.is_critical = boletin.filename in critical_documents or doc_data.get('critical_count', 0) > 0
        
        return boletines
    
    except Exception as e:
        logger.warning(f"Error enriqueciendo con red flags: {e}")
        return boletines

@router.get("/boletines/{filename}/info")
async def get_boletin_info(filename: str):
    """
    Obtiene información detallada de un boletín específico
    """
    try:
        pdf_path = BOLETINES_DIR / filename
        
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="Boletín no encontrado")
        
        # Parsear información
        file_info = parse_filename(filename)
        
        if not file_info['valid']:
            raise HTTPException(status_code=400, detail="Nombre de archivo inválido")
        
        # Información del archivo
        stat = pdf_path.stat()
        
        return {
            "filename": filename,
            "path": str(pdf_path),
            "date": file_info['date_str'],
            "section": file_info['section'],
            "section_name": get_section_name(file_info['section']),
            "file_size": stat.st_size,
            "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "display_name": f"{file_info['display_date']} - {get_section_name(file_info['section'])}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo info de {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/boletines/stats")
async def get_boletines_stats():
    """
    Obtiene estadísticas generales de los boletines
    """
    try:
        if not BOLETINES_DIR.exists():
            raise HTTPException(status_code=404, detail="Directorio de boletines no encontrado")
        
        # Buscar recursivamente en todos los subdirectorios
        pdf_files = list(BOLETINES_DIR.glob("**/*.pdf"))
        
        # Estadísticas por sección
        sections_count = {}
        dates_count = {}
        total_size = 0
        
        for pdf_file in pdf_files:
            file_info = parse_filename(pdf_file.name)
            
            if file_info['valid']:
                section = file_info['section']
                date_str = file_info['date_str']
                
                sections_count[section] = sections_count.get(section, 0) + 1
                dates_count[date_str] = dates_count.get(date_str, 0) + 1
                total_size += pdf_file.stat().st_size
        
        return {
            "total_files": len(pdf_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "sections_distribution": {
                get_section_name(k): v for k, v in sections_count.items()
            },
            "unique_dates": len(dates_count),
            "files_by_section": sections_count,
            "avg_file_size_mb": round((total_size / len(pdf_files)) / (1024 * 1024), 2) if pdf_files else 0
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/documents/{filename}/pdf")
async def serve_pdf(filename: str):
    """
    Sirve el archivo PDF para visualización en el browser
    """
    try:
        pdf_path = BOLETINES_DIR / filename
        
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="PDF no encontrado")
        
        if not pdf_path.suffix.lower() == '.pdf':
            raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")
        
        return FileResponse(
            path=pdf_path,
            media_type='application/pdf',
            filename=filename,
            headers={"Content-Disposition": f"inline; filename={filename}"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sirviendo PDF {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

"""
Router para acceso a texto de documentos procesados
"""
from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path as PathLib
from app.core.config import settings

router = APIRouter(prefix="/documentos", tags=["documentos"])

# Directorio donde están los textos procesados
PROCESSED_DIR = PathLib(__file__).parent.parent.parent.parent.parent / "data" / "processed"


class DocumentTextResponse(BaseModel):
    """Respuesta con texto del documento"""
    filename: str
    content: str
    size_bytes: int


@router.get("/text/{filename}", response_model=DocumentTextResponse)
async def get_document_text(
    filename: str = Path(..., description="Nombre del archivo (ej: 20260203_1_Secc.pdf)")
):
    """
    Obtiene el texto extraído de un documento
    
    Args:
        filename: Nombre del archivo PDF original
        
    Returns:
        Contenido de texto del documento procesado
    """
    # Construir path al archivo de texto
    txt_filename = filename.replace('.pdf', '.txt')
    txt_path = PROCESSED_DIR / txt_filename
    
    if not txt_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Texto no encontrado para documento: {filename}"
        )
    
    try:
        # Leer contenido
        content = txt_path.read_text(encoding='utf-8')
        
        return DocumentTextResponse(
            filename=filename,
            content=content,
            size_bytes=txt_path.stat().st_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error leyendo texto del documento: {str(e)}"
        )


@router.get("/text/{filename}/download")
async def download_document_text(
    filename: str = Path(..., description="Nombre del archivo (ej: 20260203_1_Secc.pdf)")
):
    """
    Descarga el archivo de texto extraído
    """
    txt_filename = filename.replace('.pdf', '.txt')
    txt_path = PROCESSED_DIR / txt_filename
    
    if not txt_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Texto no encontrado para documento: {filename}"
        )
    
    return FileResponse(
        path=str(txt_path),
        filename=txt_filename,
        media_type='text/plain'
    )


@router.get("/pdf/{filename}")
async def get_pdf_document(
    filename: str = Path(..., description="Nombre del archivo PDF")
):
    """
    Obtiene el PDF original (si está disponible)
    """
    boletines_dir = settings.BOLETINES_DIR
    
    # El filename puede venir como 20260203_1_Secc.pdf
    # Buscar por año/mes/dia en la estructura de directorios
    if len(filename) >= 8:
        year = filename[:4]
        month = filename[4:6]
        day = filename[6:8]
        
        # Buscar en estructura de directorios
        possible_paths = [
            boletines_dir / year / month / day / filename,
            boletines_dir / year / month / filename,
            boletines_dir / year / filename,
            boletines_dir / filename
        ]
        
        for pdf_path in possible_paths:
            if pdf_path.exists():
                return FileResponse(
                    path=str(pdf_path),
                    filename=filename,
                    media_type='application/pdf'
                )
    
    raise HTTPException(
        status_code=404,
        detail=f"PDF no encontrado: {filename}"
    )

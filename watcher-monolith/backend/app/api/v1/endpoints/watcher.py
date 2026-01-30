"""
API endpoints para el servicio Watcher
"""

from typing import List, Dict, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pathlib import Path

from app.core.config import settings
from app.services.watcher_service import WatcherService
from app.services.mock_watcher_service import MockWatcherService

router = APIRouter()
watcher_service = WatcherService()

@router.post("/analyze/text/")
async def analyze_text(
    text: str,
    max_fragments: Optional[int] = None
) -> Dict:
    """
    Analiza un texto directamente.
    
    Args:
        text: Texto a analizar
        max_fragments: Número máximo de fragmentos a procesar
    """
    try:
        # Preparar metadata básica
        metadata = {
            "boletin": "text_input",
            "start_page": 1,
            "end_page": 1,
            "section_type": "text"
        }
        
        # Analizar el texto
        result = await watcher_service.analyze_content(text, metadata)
        
        return {
            "text": text,
            "analysis": result,
            "metadata": metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/file/")
async def analyze_file(
    file: UploadFile = File(...),
    max_fragments: Optional[int] = None
) -> Dict:
    """
    Analiza un archivo subido.
    
    Args:
        file: Archivo de texto a analizar
        max_fragments: Número máximo de fragmentos a procesar
    """
    try:
        # Guardar archivo
        input_path = settings.UPLOADS_DIR / file.filename
        output_path = settings.RESULTS_DIR / f"{Path(file.filename).stem}_analysis.jsonl"
        
        content = await file.read()
        with open(input_path, "wb") as f:
            f.write(content)
        
        # Procesar archivo
        result_path = await watcher_service.process_file(input_path, output_path, max_fragments)
        
        return {
            "message": "Archivo procesado correctamente",
            "input_file": str(input_path),
            "result_file": str(result_path)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/text/mock/")
async def analyze_text_mock(
    text: str,
    max_fragments: Optional[int] = None
) -> Dict:
    """
    Analiza un texto usando el servicio mock (para testing).
    
    Args:
        text: Texto a analizar
        max_fragments: Número máximo de fragmentos a procesar
    """
    try:
        # Usar servicio mock
        mock_service = MockWatcherService()
        
        # Preparar metadata básica
        metadata = {
            "boletin": "text_input_mock",
            "start_page": 1,
            "end_page": 1,
            "section_type": "text"
        }
        
        # Analizar el texto con mock
        result = await mock_service.analyze_content(text, metadata)
        
        return {
            "text": text,
            "analysis": result,
            "metadata": metadata,
            "service": "mock"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

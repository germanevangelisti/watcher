
# Agregar al archivo: /watcher-monolith/backend/app/api/v1/endpoints/watcher.py

from pathlib import Path
import sys
import json
from typing import Dict, List, Optional

# Importar agente DS Lab
ds_lab_path = "/Users/germanevangelisti/watcher-agent/watcher-lab/watcher_ds_lab/src"
sys.path.append(ds_lab_path)

from agents.detection_agent import WatcherDetectionAgent
from integrations.pdf_evidence_viewer import PDFEvidenceViewer

@router.post("/analyze-with-redflags", response_model=Dict)
async def analyze_document_with_redflags(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Análisis completo del documento con detección de red flags
    """
    try:
        # Procesar documento (código existente del monolito)
        result = await process_single_document(file)
        
        # Agregar análisis DS Lab
        agent = WatcherDetectionAgent()
        pdf_viewer = PDFEvidenceViewer()
        
        # Convertir resultado a formato compatible
        document_data = {
            'filename': file.filename,
            'transparency_score': result.get('transparency_score', 50),
            'risk_level': result.get('risk_level', 'MEDIO'),
            'num_amounts': len(result.get('amounts', [])),
            'num_entities': len(result.get('entities', [])),
            'seccion': result.get('section', 1),
            'act_type': result.get('act_type', 'OTROS')
        }
        
        # Detectar red flags
        red_flags = agent.analyze_document(document_data)
        
        # Agregar evidencia visual para cada red flag
        enhanced_flags = []
        for flag in red_flags:
            evidence_data = pdf_viewer.extract_evidence_coordinates(
                file_path=Path(file.filename),
                red_flag=flag
            )
            
            flag_dict = asdict(flag)
            flag_dict['visual_evidence'] = evidence_data
            enhanced_flags.append(flag_dict)
        
        # Resultado enriquecido
        enhanced_result = {
            **result,
            'red_flags': enhanced_flags,
            'red_flags_count': len(red_flags),
            'critical_flags': len([f for f in red_flags if f.severity == 'CRITICO']),
            'ds_lab_analysis': True
        }
        
        return enhanced_result
        
    except Exception as e:
        logger.error(f"Error en análisis con red flags: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/redflags/{document_id}")
async def get_document_redflags(document_id: str):
    """
    Obtiene red flags específicas de un documento
    """
    try:
        # Buscar documento en base de datos del monolito
        document = get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        
        # Analizar con DS Lab
        agent = WatcherDetectionAgent()
        red_flags = agent.analyze_document(document)
        
        return {
            'document_id': document_id,
            'red_flags': [asdict(flag) for flag in red_flags],
            'summary': {
                'total': len(red_flags),
                'critical': len([f for f in red_flags if f.severity == 'CRITICO']),
                'high': len([f for f in red_flags if f.severity == 'ALTO'])
            }
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo red flags: {e}")
        raise HTTPException(status_code=500, detail=str(e))

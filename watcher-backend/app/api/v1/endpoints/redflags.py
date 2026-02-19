"""
API endpoints for Red Flags - Datos reales del DS Lab
"""
from pathlib import Path
import json
import logging
from typing import Dict
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()

# Ruta al archivo de sincronización con datos reales del DS Lab
MONOLITH_SYNC_FILE = Path("/Users/germanevangelisti/watcher-agent/watcher-lab/watcher_ds_lab/reports/monolith_sync.json")

def load_sync_data() -> Dict:
    """Carga los datos reales procesados por el DS Lab"""
    try:
        if not MONOLITH_SYNC_FILE.exists():
            logger.warning(f"Archivo de sincronización no encontrado: {MONOLITH_SYNC_FILE}")
            return {}
        
        with open(MONOLITH_SYNC_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando datos de sincronización: {e}")
        return {}

@router.get("/redflags/{document_id}")
async def get_document_redflags(document_id: str):
    """
    Obtiene red flags reales de un documento específico desde los datos procesados por el DS Lab.
    El document_id debe ser el filename del boletín (ej: '20250801_2_Secc.pdf')
    """
    try:
        # Cargar datos reales del DS Lab
        sync_data = load_sync_data()
        
        if not sync_data:
            raise HTTPException(
                status_code=503, 
                detail="Datos de análisis no disponibles. El sistema DS Lab aún no ha procesado los documentos."
            )
        
        # Buscar red flags para este documento
        red_flags_by_document = sync_data.get('red_flags_by_document', {})
        
        if document_id not in red_flags_by_document:
            # Si no hay red flags para este documento, retornar lista vacía
            return {
                'document_id': document_id,
                'red_flags': [],
                'summary': {
                    'total': 0,
                    'critical': 0,
                    'high': 0,
                    'medium': 0,
                    'info': 0
                }
            }
        
        document_data = red_flags_by_document[document_id]
        flags = document_data.get('flags', [])
        
        # Convertir flags al formato esperado por el frontend
        formatted_flags = []
        for flag in flags:
            formatted_flag = {
                'id': flag.get('id', f"flag_{document_id}_{len(formatted_flags)}"),
                'flag_type': flag.get('flag_type', 'IRREGULARIDAD_DETECTADA'),
                'severity': flag.get('severity', 'MEDIO'),
                'confidence': flag.get('confidence', 0.7),
                'description': flag.get('description', 'Irregularidad detectada'),
                'evidence': flag.get('evidence', []),
                'recommendation': flag.get('recommendation'),
                'transparency_score': flag.get('transparency_score'),  # Incluir directamente
                'risk_factors': flag.get('risk_factors', {}),
                'metadata': {
                    **flag.get('metadata', {}),
                    'transparency_score': flag.get('transparency_score'),  # También en metadata para compatibilidad
                    'risk_factors': flag.get('risk_factors', {})
                },
                'visual_evidence': None  # Se puede agregar después si está disponible
            }
            formatted_flags.append(formatted_flag)
        
        # Calcular resumen
        summary = {
            'total': len(formatted_flags),
            'critical': len([f for f in formatted_flags if f['severity'] == 'CRITICO']),
            'high': len([f for f in formatted_flags if f['severity'] == 'ALTO']),
            'medium': len([f for f in formatted_flags if f['severity'] == 'MEDIO']),
            'info': len([f for f in formatted_flags if f['severity'] == 'INFORMATIVO'])
        }
        
        return {
            'document_id': document_id,
            'red_flags': formatted_flags,
            'summary': summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo red flags para {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/redflags")
async def get_all_red_flags():
    """
    Obtiene todas las red flags de todos los documentos procesados
    """
    try:
        sync_data = load_sync_data()
        
        if not sync_data:
            return {
                'total_documents': 0,
                'documents_with_flags': 0,
                'red_flags_by_document': {}
            }
        
        return {
            'total_documents': sync_data.get('total_documents', 0),
            'documents_with_flags': sync_data.get('documents_with_flags', 0),
            'critical_documents': sync_data.get('critical_documents', []),
            'sync_timestamp': sync_data.get('sync_timestamp'),
            'red_flags_by_document': sync_data.get('red_flags_by_document', {})
        }
    except Exception as e:
        logger.error(f"Error obteniendo todas las red flags: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

"""
Esquemas de datos para procesamiento por lotes
"""

from pydantic import BaseModel

class BatchProcessRequest(BaseModel):
    """Esquema para solicitud de procesamiento por lotes."""
    source_dir: str
    batch_size: int = 5  # valor por defecto


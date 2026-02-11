"""
Schemas for Alertas endpoints
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AlertaBase(BaseModel):
    tipo_alerta: str
    nivel_severidad: str
    organismo: str
    programa: Optional[str] = None
    titulo: str
    descripcion: str
    valor_detectado: Optional[float] = None
    valor_esperado: Optional[float] = None
    porcentaje_desvio: Optional[float] = None

class AlertaCreate(AlertaBase):
    boletin_id: Optional[int] = None
    ejecucion_id: Optional[int] = None
    acciones_sugeridas: Optional[dict] = None

class AlertaUpdate(BaseModel):
    estado: Optional[str] = None
    observaciones_revision: Optional[str] = None

class AlertaResponse(AlertaBase):
    id: int
    fecha_deteccion: datetime
    estado: str
    created_at: datetime
    acciones_sugeridas: Optional[dict] = None

    class Config:
        from_attributes = True

class AlertasListResponse(BaseModel):
    alertas: List[AlertaResponse]
    total: int
    page: int
    page_size: int

class AlertasStatsResponse(BaseModel):
    total: int
    criticas: int
    altas: int
    medias: int
    bajas: int
    activas: int
    revisadas: int
    por_tipo: dict
    por_organismo: dict


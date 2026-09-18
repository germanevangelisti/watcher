"""
Schemas for Alertas endpoints
"""

from datetime import datetime

from pydantic import BaseModel


class AlertaBase(BaseModel):
    tipo_alerta: str
    nivel_severidad: str
    organismo: str
    programa: str | None = None
    titulo: str
    descripcion: str
    valor_detectado: float | None = None
    valor_esperado: float | None = None
    porcentaje_desvio: float | None = None

class AlertaCreate(AlertaBase):
    boletin_id: int | None = None
    ejecucion_id: int | None = None
    acciones_sugeridas: dict | None = None

class AlertaUpdate(BaseModel):
    estado: str | None = None
    observaciones_revision: str | None = None

class AlertaResponse(AlertaBase):
    id: int
    fecha_deteccion: datetime
    estado: str
    created_at: datetime
    acciones_sugeridas: dict | None = None

    class Config:
        from_attributes = True

class AlertasListResponse(BaseModel):
    alertas: list[AlertaResponse]
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


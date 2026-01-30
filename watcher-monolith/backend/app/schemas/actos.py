"""
Schemas for Actos Administrativos endpoints
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

class ActoBase(BaseModel):
    tipo_acto: str
    numero: Optional[str] = None
    fecha: Optional[date] = None
    organismo: str
    beneficiario: Optional[str] = None
    monto: Optional[float] = None
    partida: Optional[str] = None
    descripcion: str
    nivel_riesgo: str

class ActoCreate(ActoBase):
    boletin_id: Optional[int] = None
    keywords: Optional[str] = None
    fragmento_original: str
    pagina: Optional[int] = None

class ActoResponse(ActoBase):
    id: int
    created_at: datetime
    keywords: Optional[str] = None

    class Config:
        from_attributes = True

class VinculoResponse(BaseModel):
    id: int
    acto_id: int
    programa_id: int
    score_confianza: float
    metodo_matching: str
    detalles_json: Optional[dict] = None
    programa: Optional[dict] = None  # Will include programa details

    class Config:
        from_attributes = True

class ActoDetailResponse(ActoResponse):
    vinculos: List[VinculoResponse]
    fragmento_original: str
    pagina: Optional[int] = None

class ActosListResponse(BaseModel):
    actos: List[ActoResponse]
    total: int
    page: int
    page_size: int


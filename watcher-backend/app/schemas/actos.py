"""
Schemas for Actos Administrativos endpoints
"""

from datetime import date, datetime

from pydantic import BaseModel


class ActoBase(BaseModel):
    tipo_acto: str
    numero: str | None = None
    fecha: date | None = None
    organismo: str
    beneficiario: str | None = None
    monto: float | None = None
    partida: str | None = None
    descripcion: str
    nivel_riesgo: str

class ActoCreate(ActoBase):
    boletin_id: int | None = None
    keywords: str | None = None
    fragmento_original: str
    pagina: int | None = None

class ActoResponse(ActoBase):
    id: int
    created_at: datetime
    keywords: str | None = None

    class Config:
        from_attributes = True

class VinculoResponse(BaseModel):
    id: int
    acto_id: int
    programa_id: int
    score_confianza: float
    metodo_matching: str
    detalles_json: dict | None = None
    programa: dict | None = None  # Will include programa details

    class Config:
        from_attributes = True

class ActoDetailResponse(ActoResponse):
    vinculos: list[VinculoResponse]
    fragmento_original: str
    pagina: int | None = None

class ActosListResponse(BaseModel):
    actos: list[ActoResponse]
    total: int
    page: int
    page_size: int


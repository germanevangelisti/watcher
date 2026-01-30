"""
Schemas for Presupuesto endpoints
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

class ProgramaBase(BaseModel):
    ejercicio: int
    organismo: str
    programa: str
    subprograma: Optional[str] = None
    partida_presupuestaria: str
    descripcion: str
    monto_inicial: float
    monto_vigente: float

class ProgramaResponse(ProgramaBase):
    id: int
    fecha_aprobacion: date
    meta_fisica: Optional[str] = None
    meta_numerica: Optional[float] = None
    unidad_medida: Optional[str] = None
    fuente_financiamiento: Optional[str] = None

    class Config:
        from_attributes = True

class EjecucionResponse(BaseModel):
    id: int
    fecha_boletin: date
    organismo: str
    beneficiario: str
    concepto: str
    monto: float
    tipo_operacion: str
    monto_acumulado_mes: Optional[float] = None
    monto_acumulado_anual: Optional[float] = None
    categoria_watcher: str
    riesgo_watcher: str

    class Config:
        from_attributes = True

class ProgramaDetailResponse(ProgramaResponse):
    ejecuciones: List[EjecucionResponse]
    total_ejecutado: float
    porcentaje_ejecucion: float

class ProgramasListResponse(BaseModel):
    programas: List[ProgramaResponse]
    total: int
    page: int
    page_size: int

class OrganismoResponse(BaseModel):
    organismo: str
    total_programas: int
    monto_inicial_total: float
    monto_vigente_total: float


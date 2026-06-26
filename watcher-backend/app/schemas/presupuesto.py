"""
Schemas for Presupuesto endpoints
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import date

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
    boletin_id: Optional[int] = None
    presupuesto_base_id: Optional[int] = None
    fecha_boletin: date
    organismo: Optional[str] = None
    beneficiario: Optional[str] = None
    concepto: Optional[str] = None
    monto: float
    tipo_operacion: Optional[str] = None
    partida_presupuestaria: Optional[str] = None
    programa: Optional[str] = None
    categoria_watcher: Optional[str] = None
    riesgo_watcher: Optional[str] = None
    monto_acumulado_mes: Optional[float] = None
    monto_acumulado_trimestre: Optional[float] = None
    monto_acumulado_anual: Optional[float] = None
    requiere_revision: Optional[bool] = False
    is_duplicate: int = 0
    observaciones: Optional[str] = None

    class Config:
        from_attributes = True


class EjecucionListResponse(BaseModel):
    ejecuciones: List[EjecucionResponse]
    total: int
    total_monto: float
    page: int
    page_size: int


class OrgResumenItem(BaseModel):
    organismo: Optional[str]
    count: int
    monto_total: float


class MesResumenItem(BaseModel):
    mes: str   # "2026-02", "2026-03", ...
    count: int
    monto_total: float


class EjecucionResumenResponse(BaseModel):
    total_canonical: int
    total_duplicates: int
    monto_canonical: float
    monto_duplicates: float
    por_organismo: List[OrgResumenItem]
    por_mes: List[MesResumenItem]

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


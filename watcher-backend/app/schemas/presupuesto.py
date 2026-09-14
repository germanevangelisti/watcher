"""
Schemas for Presupuesto endpoints
"""

from pydantic import BaseModel, PlainSerializer
from typing import Annotated, Optional, List
from datetime import date

# ARS values are emitted in millions so JSON never contains 11+ digit
# integers (those get corrupted by some browser inspectors and axios then
# swallows the parse error, which made the UI look empty).
def _money_millions(value: float) -> float:
    return round(float(value) / 1_000_000.0, 4)


JsonMoney = Annotated[
    float,
    PlainSerializer(_money_millions, return_type=float, when_used="json"),
]


class ProgramaBase(BaseModel):
    ejercicio: int
    organismo: str
    programa: str
    subprograma: Optional[str] = None
    partida_presupuestaria: str
    descripcion: str
    monto_inicial: JsonMoney
    monto_vigente: JsonMoney

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
    monto: JsonMoney
    tipo_operacion: Optional[str] = None
    partida_presupuestaria: Optional[str] = None
    programa: Optional[str] = None
    categoria_watcher: Optional[str] = None
    riesgo_watcher: Optional[str] = None
    etapa_gasto: Optional[str] = None
    jurisdiccion: Optional[str] = None
    monto_acumulado_mes: Optional[JsonMoney] = None
    monto_acumulado_trimestre: Optional[JsonMoney] = None
    monto_acumulado_anual: Optional[JsonMoney] = None
    requiere_revision: Optional[bool] = False
    is_duplicate: int = 0
    observaciones: Optional[str] = None

    class Config:
        from_attributes = True


class EjecucionListResponse(BaseModel):
    ejecuciones: List[EjecucionResponse]
    total: int
    total_monto: JsonMoney
    page: int
    page_size: int


class OrgResumenItem(BaseModel):
    organismo: Optional[str]
    count: int
    monto_total: JsonMoney
    monto_compromiso: JsonMoney = 0.0
    monto_ejecucion: JsonMoney = 0.0
    monto_vigente: Optional[JsonMoney] = None
    pct_compromiso: Optional[float] = None
    pct_ejecucion: Optional[float] = None
    sobre_compromiso: bool = False
    sobre_ejecucion: bool = False
    matched: bool = False


class MesResumenItem(BaseModel):
    mes: str   # "2026-02", "2026-03", ...
    count: int
    monto_total: JsonMoney


class EjecucionResumenResponse(BaseModel):
    total_canonical: int
    total_duplicates: int
    monto_canonical: JsonMoney
    monto_duplicates: JsonMoney
    monto_compromiso: JsonMoney = 0.0
    monto_ejecucion: JsonMoney = 0.0
    sobre_compromiso_count: int = 0
    por_organismo: List[OrgResumenItem]
    por_mes: List[MesResumenItem]

class ProgramaDetailResponse(ProgramaResponse):
    ejecuciones: List[EjecucionResponse]
    total_ejecutado: JsonMoney
    porcentaje_ejecucion: float

class ProgramasListResponse(BaseModel):
    programas: List[ProgramaResponse]
    total: int
    page: int
    page_size: int

class OrganismoResponse(BaseModel):
    organismo: str
    total_programas: int
    monto_inicial_total: JsonMoney
    monto_vigente_total: JsonMoney


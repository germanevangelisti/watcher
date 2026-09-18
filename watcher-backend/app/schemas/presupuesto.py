"""
Schemas for Presupuesto endpoints
"""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, PlainSerializer


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
    subprograma: str | None = None
    partida_presupuestaria: str
    descripcion: str
    monto_inicial: JsonMoney
    monto_vigente: JsonMoney

class ProgramaResponse(ProgramaBase):
    id: int
    fecha_aprobacion: date
    meta_fisica: str | None = None
    meta_numerica: float | None = None
    unidad_medida: str | None = None
    fuente_financiamiento: str | None = None

    class Config:
        from_attributes = True

class EjecucionResponse(BaseModel):
    id: int
    boletin_id: int | None = None
    presupuesto_base_id: int | None = None
    fecha_boletin: date
    organismo: str | None = None
    beneficiario: str | None = None
    concepto: str | None = None
    monto: JsonMoney
    tipo_operacion: str | None = None
    partida_presupuestaria: str | None = None
    programa: str | None = None
    categoria_watcher: str | None = None
    riesgo_watcher: str | None = None
    etapa_gasto: str | None = None
    jurisdiccion: str | None = None
    monto_acumulado_mes: JsonMoney | None = None
    monto_acumulado_trimestre: JsonMoney | None = None
    monto_acumulado_anual: JsonMoney | None = None
    requiere_revision: bool | None = False
    is_duplicate: int = 0
    observaciones: str | None = None

    class Config:
        from_attributes = True


class EjecucionListResponse(BaseModel):
    ejecuciones: list[EjecucionResponse]
    total: int
    total_monto: JsonMoney
    page: int
    page_size: int


class OrgResumenItem(BaseModel):
    organismo: str | None
    count: int
    monto_total: JsonMoney
    monto_compromiso: JsonMoney = 0.0
    monto_ejecucion: JsonMoney = 0.0
    monto_vigente: JsonMoney | None = None
    pct_compromiso: float | None = None
    pct_ejecucion: float | None = None
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
    por_organismo: list[OrgResumenItem]
    por_mes: list[MesResumenItem]

class ProgramaDetailResponse(ProgramaResponse):
    ejecuciones: list[EjecucionResponse]
    total_ejecutado: JsonMoney
    porcentaje_ejecucion: float

class ProgramasListResponse(BaseModel):
    programas: list[ProgramaResponse]
    total: int
    page: int
    page_size: int

class OrganismoResponse(BaseModel):
    organismo: str
    total_programas: int
    monto_inicial_total: JsonMoney
    monto_vigente_total: JsonMoney


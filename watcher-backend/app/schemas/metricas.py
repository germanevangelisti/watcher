"""
Schemas for Métricas endpoints
"""

from typing import Any

from pydantic import BaseModel


class MetricasGeneralesResponse(BaseModel):
    # Presupuestarias
    total_programas: int
    monto_total_inicial: float
    monto_total_vigente: float
    monto_total_ejecutado: float
    porcentaje_ejecucion_global: float

    # Actos
    total_actos: int
    actos_alto_riesgo: int
    actos_medio_riesgo: int
    actos_bajo_riesgo: int

    # Alertas
    total_alertas: int
    alertas_criticas: int
    alertas_altas: int

    # Vinculación
    total_vinculos: int
    tasa_vinculacion: float

    # Top 5
    top_organismos_presupuesto: list[dict[str, Any]]
    top_organismos_riesgo: list[dict[str, Any]]

class MetricasOrganismoResponse(BaseModel):
    organismo: str
    total_programas: int
    monto_inicial: float
    monto_vigente: float
    monto_ejecutado: float
    porcentaje_ejecucion: float
    total_actos: int
    actos_alto_riesgo: int
    total_alertas: int
    alertas_criticas: int

class DistribucionRiesgoResponse(BaseModel):
    por_nivel: dict[str, int]
    por_tipo_acto: dict[str, dict[str, int]]
    por_organismo: dict[str, dict[str, int]]
    monto_por_nivel: dict[str, float]


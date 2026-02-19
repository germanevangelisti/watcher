"""
Schemas for Métricas endpoints
"""

from pydantic import BaseModel
from typing import List, Dict, Any

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
    top_organismos_presupuesto: List[Dict[str, Any]]
    top_organismos_riesgo: List[Dict[str, Any]]

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
    por_nivel: Dict[str, int]
    por_tipo_acto: Dict[str, Dict[str, int]]
    por_organismo: Dict[str, Dict[str, int]]
    monto_por_nivel: Dict[str, float]


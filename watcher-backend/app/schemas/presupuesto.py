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
    monto_llamado: JsonMoney = 0.0


class MesResumenItem(BaseModel):
    mes: str   # "2026-02", "2026-03", ...
    count: int
    monto_total: JsonMoney


class CoberturaResumen(BaseModel):
    """Share of measured spend that has a Ley denominator to be contrasted with."""

    monto_total: JsonMoney = 0.0
    monto_con_denominador: JsonMoney = 0.0
    monto_sin_denominador: JsonMoney = 0.0
    count_sin_denominador: int = 0
    pct_sin_denominador: float = 0.0


class CoberturaTemporalResumen(BaseModel):
    """The period the numerator covers, against the annual Ley it is divided by."""

    mes_desde: str | None = None
    mes_hasta: str | None = None
    meses_cubiertos: int = 0
    meses_del_ejercicio: int = 12
    meses_vencidos_sin_ingesta: list[str] = []
    meses_futuros: list[str] = []
    dias_con_publicacion: int = 0
    dias_justificados: int = 0
    dias_faltantes: int = 0
    denominador_es_anual: bool = True


class DenominadorSinDuenoItemResumen(BaseModel):
    organismo: str
    count: int
    monto_vigente: JsonMoney = 0.0


class DenominadorSinDuenoResumen(BaseModel):
    """The ceiling split into what can be a denominator and what cannot."""

    monto_total: JsonMoney = 0.0
    monto_sin_dueno: JsonMoney = 0.0
    monto_verificable: JsonMoney = 0.0
    count_sin_dueno: int = 0
    pct_sin_dueno: float = 0.0
    por_organismo: list[DenominadorSinDuenoItemResumen] = []


class FinalidadDetalleItem(BaseModel):
    """One component inside the `sin_clasificar` bucket.

    `label` is `None` for components that are not finalidades of the classifier
    (the annex's `6`, for "crédito adicional"), so the caller shows `clave`
    instead of inventing a name for them.
    """

    clave: str
    label: str | None = None
    count: int
    monto_inicial: JsonMoney = 0.0
    monto_vigente: JsonMoney = 0.0
    participacion_techo_pct: float = 0.0


class FinalidadItem(BaseModel):
    """One row of the 3+1: a headline finalidad, or the bucket itself."""

    clave: str
    label: str
    count: int
    monto_inicial: JsonMoney = 0.0
    monto_vigente: JsonMoney = 0.0
    participacion_techo_pct: float = 0.0
    detalle: list[FinalidadDetalleItem] = []


class HonestidadResumen(BaseModel):
    """Qué son y qué **no** son los montos de `FinalidadesResumen`.

    Existe para que el disclaimer de la UI lea la afirmación en vez de repetirla
    de memoria: si el copy viviera sólo en el frontend, podría despegarse del
    dato y seguir diciendo "inicial = vigente" un corte donde ya hay variación.

    `inicial_es_vigente` y `filas_inicial_distinto_vigente` se miden fila por
    fila; `notas` es el copy ya listo para mostrar y se genera de esa medición.
    """

    es_techo: bool = True
    inicial_es_vigente: bool = False
    filas_inicial_distinto_vigente: int = 0
    es_credito_modificado: bool = False
    incluye_devengado_cge: bool = False
    notas: list[str] = []


class FinalidadesResumen(BaseModel):
    """Techo Ley/Mapas by finalidad — 1 / 2 / 3 + `sin_clasificar`.

    Money is the ceiling, never execution: there is no `pct_ejecucion` here on
    purpose.  `participacion_techo_pct` is the share of the año's Ley, and the
    Ley is never prorated.
    """

    ejercicio: int
    total_inicial: JsonMoney = 0.0
    total_vigente: JsonMoney = 0.0
    total_registros: int = 0
    items: list[FinalidadItem] = []
    honestidad: HonestidadResumen = HonestidadResumen()


class ProxyBoDetalleItem(BaseModel):
    """Un componente del bucket `sin_clasificar` del proxy BO."""

    clave: str
    label: str | None = None
    count: int = 0
    monto_publicado: JsonMoney = 0.0
    monto_techo: JsonMoney = 0.0
    pct_publicado_techo: float | None = None


class ProxyBoItem(BaseModel):
    """Una fila del proxy BO: publicado atribuido vs techo de esa finalidad.

    `pct_publicado_techo` es `None` cuando no hay techo contra el que comparar: sin
    denominador no hay porcentaje, y un 0% ahí afirmaría algo que no se midió.
    """

    clave: str
    label: str
    count: int = 0
    monto_publicado: JsonMoney = 0.0
    monto_techo: JsonMoney = 0.0
    pct_publicado_techo: float | None = None
    detalle: list[ProxyBoDetalleItem] = []


class CoberturaProxyBoResumen(BaseModel):
    """Cuánto del publicado se pudo atribuir a una finalidad, y cuánto no.

    `monto_sin_programa` se publica en vez de repartirse entre las finalidades: es
    gasto publicado que este slice no puede atribuir, y esconderlo convertiría el
    proxy en un reparto inventado.  `fecha_desde`/`fecha_hasta` declaran el span real
    del numerador, porque el denominador es la Ley anual completa
    (`denominador_es_anual`) y los dos no cubren el mismo período.
    """

    monto_total: JsonMoney = 0.0
    monto_con_programa: JsonMoney = 0.0
    monto_sin_programa: JsonMoney = 0.0
    count_sin_programa: int = 0
    pct_sin_programa: float = 0.0
    monto_atribuido_finalidad: JsonMoney = 0.0
    monto_no_clasificado: JsonMoney = 0.0
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    denominador_es_anual: bool = True


class EtapaProxyBoResumen(BaseModel):
    """Composición del proxy por etapa del gasto.  Se informa, no se resta."""

    clave: str
    label: str
    monto: JsonMoney = 0.0


class HonestidadProxyBoResumen(BaseModel):
    """Qué es y qué **no** es el numerador del proxy.

    Existe para que la UI lea la etiqueta en vez de elegirla: el numerador es
    `publicado en el BO`, y ni `es_devengado` ni `es_devengado_cge` pueden pasar a
    `True` sin que esto deje de ser un proxy.  Un acto publicado no devenga gasto.
    """

    es_proxy_bo: bool = True
    es_devengado: bool = False
    es_devengado_cge: bool = False
    etiqueta_numerador: str = "publicado en el BO"
    notas: list[str] = []


class ProxyBoResumen(BaseModel):
    """Publicado en el BO atribuido por finalidad, contra el techo de esa finalidad.

    Es un proxy de publicación (Should de Ampliación B), no ejecución: la ruta, los
    campos y las notas evitan la palabra "devengado" a propósito.
    """

    ejercicio: int
    items: list[ProxyBoItem] = []
    cobertura: CoberturaProxyBoResumen = CoberturaProxyBoResumen()
    etapas: list[EtapaProxyBoResumen] = []
    honestidad: HonestidadProxyBoResumen = HonestidadProxyBoResumen()


class EjecucionResumenResponse(BaseModel):
    total_canonical: int
    total_duplicates: int
    monto_canonical: JsonMoney
    monto_duplicates: JsonMoney
    monto_compromiso: JsonMoney = 0.0
    monto_ejecucion: JsonMoney = 0.0
    sobre_compromiso_count: int = 0
    cobertura: CoberturaResumen = CoberturaResumen()
    cobertura_temporal: CoberturaTemporalResumen = CoberturaTemporalResumen()
    denominador: DenominadorSinDuenoResumen = DenominadorSinDuenoResumen()
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


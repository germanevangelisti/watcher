"""Proxy BO por finalidad (Should de Ampliación B).

Lo que el Boletín Oficial **publica** (llamados, adjudicaciones, contratos, pagos)
atribuido a los programas de cada finalidad, contra el techo de esa finalidad en la
Ley 11.088.  Es un proxy de publicación, no caja: el nombre del módulo, de la ruta y
de los campos evita la palabra "devengado" a propósito, porque un acto publicado no
devenga gasto y rotularlo así convertiría el boletín en una ejecución que no es.

Tres cosas que este slice NO hace, y que por eso se declaran en los datos y no en el
copy del frontend:

1. **No reparte lo que no tiene programa.**  Una fila del ledger sin
   `presupuesto_base_id` (o matcheada a un programa de otro ejercicio) no se puede
   atribuir a ninguna finalidad.  No se prorratea ni se estima: viaja en la cobertura
   como `monto_sin_programa`, con su conteo de actos.  En el corte V.5 eso es
   **$404,52B / 364 actos**, así que la diferencia entre callarlo y decirlo es la
   diferencia entre un proxy medido y uno inventado.
2. **No inventa un denominador más chico.**  El techo contra el que se compara es el
   de la Ley completa (`presupuesto_base`), que es anual, mientras el numerador cubre
   los meses que el BO publicó.  Se publica el span real del numerador
   (`fecha_desde`/`fecha_hasta`) y `denominador_es_anual: True` para que el 30,5% de
   una finalidad se lea sabiendo que son N de 12 meses.  La Ley no se prorratea:
   prorratearla movería todos los % a la vez y en silencio.
3. **No mezcla la composición.**  `etapas` dice cuánto del proxy es llamado,
   adjudicación + contrato, y pago.  En el corte feb–sep 2026 eso es **99,35%
   llamado**, 0,27% adjudicación + contrato y 0,39% pago, así que mostrar un único
   número "publicado" sin la composición sería el mismo error que V.3.3 corrigió en
   la barra de "Compromiso" (donde el 99,86% del bucket era llamado y el rótulo
   sobreafirmaba por ~720×).  Las etapas se **informan**, no se restan: restar mueve
   el umbral y con él las alertas.

La función de doblado es pura: la query vive en `fetch_proxy_bo`.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from app.db.models import EjecucionPresupuestaria, PresupuestoBase
from app.services.ejecucion_contrast import (
    BUCKET_COMPROMISO,
    BUCKET_EJECUCION,
    bucket_etapa,
    pct_vs_vigente,
)
from app.services.gasto_classifier import ETAPA_LLAMADO
from app.services.presupuesto_finalidades import (
    FINALIDADES_DESTACADAS,
    LABELS_FINALIDAD,
    LABELS_NO_FINALIDAD,
    SIN_CLASIFICAR,
    Finalidades,
    clasificar_partida,
    fetch_finalidades,
)
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

#: Cómo se llama lo que suman los montos de este slice.  Es la etiqueta que la UI
#: tiene que mostrar; "ejecución" y "devengado" están prohibidas para este numerador.
ETIQUETA_NUMERADOR = "publicado en el BO"

#: Claves de las etapas del proxy.  `compromiso` es adjudicación + contrato — el
#: compromiso **asumido**, sin los llamados (que tienen su propia clave para que no
#: se confundan, que es el defecto que V.3.3 encontró en la barra de "Compromiso").
ETAPA_BUCKET_LLAMADO = "llamado"
ETAPA_BUCKET_COMPROMISO = "compromiso_asumido"
ETAPA_BUCKET_EJECUCION = "pago"
ETAPA_BUCKET_OTRO = "sin_etapa"

LABELS_ETAPA: dict[str, str] = {
    ETAPA_BUCKET_LLAMADO: "Llamado a licitación",
    ETAPA_BUCKET_COMPROMISO: "Compromiso asumido (adjudicación + contrato)",
    ETAPA_BUCKET_EJECUCION: "Pago",
    ETAPA_BUCKET_OTRO: "Sin etapa clasificada",
}

ES_PROXY_BO = True
ES_DEVENGADO = False
ES_DEVENGADO_CGE = False

NOTAS_HONESTIDAD: tuple[str, ...] = (
    "Los montos son lo publicado en el BO (llamados, adjudicaciones, contratos y "
    "pagos) contra el techo de la Ley: no son ejecución presupuestaria.",
    "No es Devengado CGE: no hay caja devengada en esta respuesta.",
    "Lo que no tiene programa identificado no se reparte entre finalidades: se "
    "declara en la cobertura.",
)


@dataclass(frozen=True)
class ProxyBoDetalle:
    """Un componente del bucket `sin_clasificar`, con su publicado y su techo."""

    clave: str
    label: str | None
    count: int
    monto_publicado: float
    monto_techo: float
    pct_publicado_techo: float | None


@dataclass(frozen=True)
class ProxyBoItem:
    """Una fila del proxy: publicado atribuido vs techo de esa finalidad.

    `pct_publicado_techo` es `None` cuando no hay techo con el que comparar (una
    finalidad que publicó pero no está en la Ley cargada): sin denominador no hay
    porcentaje, y un 0% ahí afirmaría algo que no se midió.
    """

    clave: str
    label: str
    count: int
    monto_publicado: float
    monto_techo: float
    pct_publicado_techo: float | None
    detalle: tuple[ProxyBoDetalle, ...] = ()


@dataclass(frozen=True)
class CoberturaProxy:
    """Cuánto del publicado se pudo atribuir a una finalidad, y cuánto no.

    Se publica en vez de repartirse: la parte sin programa no es "cero" ni "el
    resto", es gasto publicado que este slice no puede atribuir.
    """

    monto_total: float
    monto_con_programa: float
    monto_sin_programa: float
    count_sin_programa: int
    pct_sin_programa: float
    #: Dentro de lo atribuido: lo que cae en una finalidad real del clasificador
    #: (1–5) y lo que cae en ruido de partida (`sin_partida`, `Recursos`, `Cuentas`,
    #: el `6` del anexo).  El segundo no es un agujero: es un rótulo del anexo.
    monto_atribuido_finalidad: float
    monto_no_clasificado: float
    #: El span real del numerador, medido del ledger, y el hecho de que el
    #: denominador es la Ley anual.  Sin esto, un % bajo se lee como poco gasto
    #: cuando puede ser pocos meses publicados.
    fecha_desde: date | None
    fecha_hasta: date | None
    denominador_es_anual: bool


@dataclass(frozen=True)
class EtapaProxy:
    clave: str
    label: str
    monto: float


@dataclass(frozen=True)
class HonestidadProxy:
    es_proxy_bo: bool
    es_devengado: bool
    es_devengado_cge: bool
    etiqueta_numerador: str
    notas: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProxyBo:
    ejercicio: int
    items: tuple[ProxyBoItem, ...]
    cobertura: CoberturaProxy
    etapas: tuple[EtapaProxy, ...]
    honestidad: HonestidadProxy


def _etapa_bucket(etapa: str | None) -> str:
    """Bucket de `etapas` para una `etapa_gasto`, separando el llamado."""
    if etapa == ETAPA_LLAMADO:
        return ETAPA_BUCKET_LLAMADO
    bucket = bucket_etapa(etapa)
    if bucket == BUCKET_COMPROMISO:
        return ETAPA_BUCKET_COMPROMISO
    if bucket == BUCKET_EJECUCION:
        return ETAPA_BUCKET_EJECUCION
    return ETAPA_BUCKET_OTRO


def _label_detalle(clave: str) -> str | None:
    return LABELS_FINALIDAD.get(clave) or LABELS_NO_FINALIDAD.get(clave)


def agregar_proxy_bo(
    techo: Finalidades,
    filas: Iterable[tuple[int | None, str | None, str | None, float, int]],
    ejercicio: int,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
) -> ProxyBo:
    """Doblar el ledger canónico contra el techo de cada finalidad.

    `filas` son `(programa_id, partida, etapa_gasto, monto, count)` agrupadas.  El
    orden del tuple importa: `programa_id` es `None` cuando la fila del ledger **no**
    matcheó un programa de este ejercicio, y eso no es lo mismo que matchear un
    programa con la partida vacía.  La primera es cobertura perdida (`sin_programa`);
    la segunda es un programa identificado al que el clasificador no le puede poner
    finalidad (`sin_partida`).  Fundirlas en un solo número escondería cuál de los
    dos problemas hay que arreglar.

    Función pura: la query y el span viven en `fetch_proxy_bo`.
    """
    techo_por_clave = {item.clave: item.monto_vigente for item in techo.items}
    techo_detalle = {
        detalle.clave: detalle.monto_vigente
        for item in techo.items
        for detalle in item.detalle
    }

    # clave -> [count, monto]
    por_clave: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    por_etapa: dict[str, float] = defaultdict(float)

    monto_total = 0.0
    monto_con_programa = 0.0
    monto_sin_programa = 0.0
    count_sin_programa = 0
    monto_atribuido = 0.0
    monto_no_clasificado = 0.0

    for programa_id, partida, etapa, monto, count in filas:
        monto = float(monto or 0.0)
        count = int(count or 0)
        monto_total += monto
        por_etapa[_etapa_bucket(etapa)] += monto

        if programa_id is None:
            # Publicado sin programa identificado: se declara, no se reparte.
            monto_sin_programa += monto
            count_sin_programa += count
            continue

        monto_con_programa += monto
        clave = clasificar_partida(partida)
        vals = por_clave[clave]
        vals[0] += count
        vals[1] += monto
        if clave in LABELS_FINALIDAD:
            monto_atribuido += monto
        else:
            monto_no_clasificado += monto

    # Las tres destacadas salen siempre, en orden, aunque no hayan publicado nada:
    # "$0 publicado en Servicios Sociales" es información, y su ausencia sería un
    # agujero.  Es la misma regla que el techo aplica del otro lado.
    destacadas = [
        (clave, por_clave.pop(clave, [0.0, 0.0]))
        for clave in FINALIDADES_DESTACADAS
    ]
    resto = por_clave

    items: list[ProxyBoItem] = [
        ProxyBoItem(
            clave=clave,
            label=LABELS_FINALIDAD[clave],
            count=int(vals[0]),
            monto_publicado=vals[1],
            monto_techo=techo_por_clave.get(clave, 0.0),
            pct_publicado_techo=pct_vs_vigente(
                vals[1], techo_por_clave.get(clave, 0.0)
            ),
        )
        for clave, vals in destacadas
    ]

    # El detalle del bucket es la unión de lo que publicó y lo que el techo tiene:
    # una finalidad con techo y sin nada publicado (finalidad 5, p. ej.) tiene que
    # aparecer en $0 — es el hueco de publicación más informativo del slice.
    claves_detalle = set(resto) | set(techo_detalle)
    detalle = tuple(
        ProxyBoDetalle(
            clave=clave,
            label=_label_detalle(clave),
            count=int(resto.get(clave, [0.0, 0.0])[0]),
            monto_publicado=resto.get(clave, [0.0, 0.0])[1],
            monto_techo=techo_detalle.get(clave, 0.0),
            pct_publicado_techo=pct_vs_vigente(
                resto.get(clave, [0.0, 0.0])[1], techo_detalle.get(clave, 0.0)
            ),
        )
        # Lo más publicado primero — este slice es sobre el BO.  Donde no hay nada
        # publicado, manda el techo, así Servicios Económicos no queda abajo del
        # ruido de parseo por publicar poco.  Desempate por clave para que el mismo
        # corte dé siempre el mismo orden.
        for clave in sorted(
            claves_detalle,
            key=lambda c: (
                -resto.get(c, [0.0, 0.0])[1],
                -techo_detalle.get(c, 0.0),
                c,
            ),
        )
    )

    bucket = resto
    monto_bucket = sum(v[1] for v in bucket.values())
    count_bucket = int(sum(v[0] for v in bucket.values()))
    items.append(
        ProxyBoItem(
            clave=SIN_CLASIFICAR,
            label="Sin clasificar",
            count=count_bucket,
            monto_publicado=monto_bucket,
            monto_techo=techo_por_clave.get(SIN_CLASIFICAR, 0.0),
            pct_publicado_techo=pct_vs_vigente(
                monto_bucket, techo_por_clave.get(SIN_CLASIFICAR, 0.0)
            ),
            detalle=detalle,
        )
    )

    return ProxyBo(
        ejercicio=ejercicio,
        items=tuple(items),
        cobertura=CoberturaProxy(
            monto_total=monto_total,
            monto_con_programa=monto_con_programa,
            monto_sin_programa=monto_sin_programa,
            count_sin_programa=count_sin_programa,
            pct_sin_programa=(
                round(100.0 * monto_sin_programa / monto_total, 2)
                if monto_total > 0
                else 0.0
            ),
            monto_atribuido_finalidad=monto_atribuido,
            monto_no_clasificado=monto_no_clasificado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            denominador_es_anual=True,
        ),
        etapas=tuple(
            EtapaProxy(clave=clave, label=LABELS_ETAPA[clave], monto=por_etapa[clave])
            for clave in LABELS_ETAPA
        ),
        honestidad=HonestidadProxy(
            es_proxy_bo=ES_PROXY_BO,
            es_devengado=ES_DEVENGADO,
            es_devengado_cge=ES_DEVENGADO_CGE,
            etiqueta_numerador=ETIQUETA_NUMERADOR,
            notas=NOTAS_HONESTIDAD,
        ),
    )


async def fetch_proxy_bo(db: AsyncSession, ejercicio: int) -> ProxyBo | None:
    """Leer el ledger canónico del ejercicio y doblarlo contra el techo por finalidad.

    Devuelve `None` cuando el ejercicio no tiene Ley cargada — el mismo hueco que
    `fetch_finalidades`: sin techo no hay contra qué contrastar, y devolver ceros
    afirmaría que no se publicó nada.

    Un ejercicio **con** Ley y sin ledger no es un hueco: es un $0 medido (no hay
    nada publicado), y por eso devuelve el slice completo en cero.
    """
    techo = await fetch_finalidades(db, ejercicio)
    if techo is None:
        return None

    # `ejercicio` va en el ON y no en el WHERE: con un outer join, filtrar ahí
    # convertiría el join en inner y las filas sin programa desaparecerían en vez de
    # declararse.  Una fila matcheada a un programa de otro ejercicio cae como
    # "sin programa" dentro de este marco, que es lo honesto.
    query = (
        select(
            PresupuestoBase.id.label("programa_id"),
            PresupuestoBase.partida_presupuestaria.label("partida"),
            EjecucionPresupuestaria.etapa_gasto,
            func.count(EjecucionPresupuestaria.id).label("cnt"),
            func.coalesce(func.sum(EjecucionPresupuestaria.monto), 0).label("total"),
        )
        .select_from(EjecucionPresupuestaria)
        .outerjoin(
            PresupuestoBase,
            and_(
                PresupuestoBase.id == EjecucionPresupuestaria.presupuesto_base_id,
                PresupuestoBase.ejercicio == ejercicio,
            ),
        )
        .where(EjecucionPresupuestaria.is_duplicate == 0)
        .group_by(
            PresupuestoBase.id,
            PresupuestoBase.partida_presupuestaria,
            EjecucionPresupuestaria.etapa_gasto,
        )
    )
    result = await db.execute(query)
    filas = [
        (r.programa_id, r.partida, r.etapa_gasto, float(r.total), int(r.cnt))
        for r in result.all()
    ]

    span = await db.execute(
        select(
            func.min(EjecucionPresupuestaria.fecha_boletin),
            func.max(EjecucionPresupuestaria.fecha_boletin),
        ).where(EjecucionPresupuestaria.is_duplicate == 0)
    )
    fecha_desde, fecha_hasta = span.one()

    return agregar_proxy_bo(
        techo, filas, ejercicio, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta
    )

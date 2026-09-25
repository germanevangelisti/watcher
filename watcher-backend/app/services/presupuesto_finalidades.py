"""Techo Ley/Mapas agrupado por finalidad (Ampliación B — Must MB).

`presupuesto_base.partida_presupuestaria` guarda el `fin_fun_det` del anexo de la
Ley 11.088 tal como lo imprime el PDF (`1.6.0` = finalidad 1, función 6, detalle
0).  El primer componente es, entonces, la finalidad del clasificador oficial, y
el slice ciudadano es 1 / 2 / 3 + `sin_clasificar`.

El bucket `sin_clasificar` NO se lleva el resto en silencio.  En el corte 2026 la
finalidad 4 (Servicios Económicos) es **$3.066,50B = 40,71% del techo** — la línea
más grande del presupuesto — así que cada componente que cae dentro del bucket
viaja en `detalle` con su monto y su label.  Llamar "sin clasificar" a 3 billones
sin decirlo sería mentir el techo, que es justo lo que el bucket existe para
evitar (ver `knowledgebase/vision/mvp.md`, riesgos MB).

Honestidad del corte, vinculante:

- Los montos son **techo** (`presupuesto_base`), nunca ejecución.  No se expone
  ningún `pct_ejecucion` / `pct_compromiso`: eso es el contraste del BO, no este
  slice.
- `monto_inicial == monto_vigente` en 480/480 filas 2026 — el seed asigna el
  mismo monto de Mapas/Ley a ambos.  Se publican los dos porque son idénticos;
  la "variación sancionado ≠ vigente" es 0 **por construcción**, no medida.

El corte viaja además con su bloque `honestidad`: los flags que el disclaimer de
la UI necesita, y el copy que los acompaña.  El copy NO se hardcodea — `inicial_es_vigente`
se **mide** fila por fila y las notas se generan de esa medición, así que el día
que el corte tenga variación el copy cambia solo en vez de seguir mintiendo.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from app.db.models import PresupuestoBase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

#: Labels del clasificador por finalidad y función.  Se usan tanto para las tres
#: finalidades que publican fila propia como para el `detalle` del bucket.
LABELS_FINALIDAD: dict[str, str] = {
    "1": "Administración Gubernamental",
    "2": "Servicios de Defensa y Seguridad",
    "3": "Servicios Sociales",
    "4": "Servicios Económicos",
    "5": "Deuda Pública",
}

#: Las finalidades que el slice publica como fila.  Todo lo demás — incluida la
#: finalidad 4 y la 5, que son finalidades reales — cae en `sin_clasificar`, y
#: sale a la luz por `detalle`.
FINALIDADES_DESTACADAS: tuple[str, ...] = ("1", "2", "3")

#: Clave del bucket que junta lo que no es una de las tres filas.
SIN_CLASIFICAR = "sin_clasificar"

#: Clave para las filas con `partida_presupuestaria` vacía.
SIN_PARTIDA = "sin_partida"

#: Labels para los componentes del bucket que no son finalidades del
#: clasificador.  `6` no figura en el clasificador (el anexo lo usa para
#: "crédito adicional"), así que queda sin label y el consumidor muestra `clave`.
LABELS_NO_FINALIDAD: dict[str, str] = {
    SIN_PARTIDA: "Partida vacía",
    "Recursos": "Recursos",
    "Cuentas": "Cuentas especiales",
}

#: Los tres cortes estructurales del slice.  Este endpoint lee `presupuesto_base`
#: y nada más: no hay crédito modificado (post-modificaciones SIFEP) ni Devengado
#: CGE en esa tabla, y los montos son techo, no ejecución.  Se publican igual como
#: campos —y no como copy suelto en el frontend— para que la UI lea la afirmación
#: en vez de repetirla de memoria.
ES_TECHO = True
ES_CREDITO_MODIFICADO = False
INCLUYE_DEVENGADO_CGE = False

#: Copy de la parte estructural, la que no depende de ninguna medición.
NOTAS_ESTRUCTURALES: tuple[str, ...] = (
    "Los montos son techo de la Ley 11.088 / Mapas: no hay ejecución acá.",
    "No es crédito modificado.",
    "No es Devengado CGE: no hay caja devengada en esta respuesta.",
)


def clasificar_partida(partida: str | None) -> str:
    """Clave de bucket de una `partida_presupuestaria`.

    `'1.6.0'` → `'1'`; `'Recursos'` → `'Recursos'`; `''`/`None` → `'sin_partida'`.

    Se parte por el primer punto en vez de mirar el primer carácter: `'Recursos'`
    y `'Cuentas'` empiezan con letra y quedarían indistinguibles de una finalidad
    homónima si algún día el anexo trajera una.
    """
    raw = (partida or "").strip()
    if not raw:
        return SIN_PARTIDA
    head = raw.split(".", 1)[0].strip()
    return head or SIN_PARTIDA


@dataclass(frozen=True)
class FinalidadDetalle:
    """Un componente del bucket `sin_clasificar`, con su monto a la vista."""

    clave: str
    label: str | None
    count: int
    monto_inicial: float
    monto_vigente: float
    participacion_techo_pct: float


@dataclass(frozen=True)
class FinalidadItem:
    """Una fila del 3+1: una finalidad destacada, o el bucket."""

    clave: str
    label: str
    count: int
    monto_inicial: float
    monto_vigente: float
    participacion_techo_pct: float
    detalle: tuple[FinalidadDetalle, ...] = ()


@dataclass(frozen=True)
class Honestidad:
    """Qué son y qué **no** son los montos del corte.

    `es_techo`, `es_credito_modificado` e `incluye_devengado_cge` son
    estructurales: describen de dónde sale el número.  `inicial_es_vigente` y su
    conteo son **medidos** fila por fila, así que pueden dejar de valer sin que
    nadie toque este archivo — y por eso viajan con el dato y no como copy fijo.
    """

    es_techo: bool
    inicial_es_vigente: bool
    filas_inicial_distinto_vigente: int
    es_credito_modificado: bool
    incluye_devengado_cge: bool
    notas: tuple[str, ...] = ()


@dataclass(frozen=True)
class Finalidades:
    """El techo del ejercicio repartido en 3+1.

    `total_inicial`/`total_vigente` se acumulan con las mismas sumas, en el mismo
    orden, que los items, así que `sum(items) == total` vale exacto.
    """

    ejercicio: int
    total_inicial: float
    total_vigente: float
    total_registros: int
    items: tuple[FinalidadItem, ...]
    honestidad: Honestidad


def _pct(monto: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * monto / total, 2)


def _label_detalle(clave: str) -> str | None:
    return LABELS_FINALIDAD.get(clave) or LABELS_NO_FINALIDAD.get(clave)


def _notas_honestidad(
    registros: int, filas_inicial_distinto_vigente: int
) -> tuple[str, ...]:
    """El copy del corte, generado de la medición — no de una plantilla fija.

    Con las notas hardcodeadas, el día que el corte traiga variación
    sancionado ≠ vigente la API seguiría diciendo "inicial = vigente".  Acá la
    frase cambia con el dato, que es la única forma de que el copy no mienta.
    """
    if registros == 0:
        variacion = (
            "Este corte no tiene filas: no se afirma nada sobre inicial vs vigente."
        )
    elif filas_inicial_distinto_vigente == 0:
        variacion = (
            f"monto_inicial == monto_vigente en las {registros} filas del corte: la "
            "variación sancionado ≠ vigente es 0 por construcción (el seed asigna el "
            "mismo monto de Mapas/Ley a los dos), no medida."
        )
    else:
        variacion = (
            f"monto_inicial ≠ monto_vigente en {filas_inicial_distinto_vigente} de "
            f"{registros} filas: la variación sancionado ≠ vigente NO es 0 en este "
            "corte."
        )
    return (*NOTAS_ESTRUCTURALES, variacion)


def agregar_finalidades(
    rows: Iterable[tuple[str | None, float | None, float | None]],
    ejercicio: int,
) -> Finalidades:
    """Doblar `(partida, monto_inicial, monto_vigente)` en el slice 3+1.

    Función pura: la query vive en `fetch_finalidades`.  Las tres finalidades
    destacadas salen siempre, en orden, aunque el ejercicio no tenga filas de
    alguna — una fila en $0 es información, una fila ausente es un agujero.
    """
    acc: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    registros = 0
    #: Filas donde inicial y vigente difieren.  Se cuentan acá para que
    #: `inicial_es_vigente` sea una medición del corte y no una afirmación de fe.
    distintos = 0
    for partida, inicial, vigente in rows:
        vals = acc[clasificar_partida(partida)]
        ini = float(inicial or 0.0)
        vig = float(vigente or 0.0)
        vals[0] += 1
        vals[1] += ini
        vals[2] += vig
        if ini != vig:
            distintos += 1
        registros += 1

    # `sin_clasificar` es "todo lo que no es 1/2/3".  Tanto el total como el
    # bucket se suman sobre las mismas listas y en el mismo orden que los items,
    # así que `sum(items) == total` vale exacto y el bucket no puede despegarse
    # del techo sin que se note.
    destacadas = [
        (clave, acc.pop(clave, [0.0, 0.0, 0.0])) for clave in FINALIDADES_DESTACADAS
    ]
    resto = acc

    total_inicial = sum(v[1] for _, v in destacadas) + sum(v[1] for v in resto.values())
    total_vigente = sum(v[2] for _, v in destacadas) + sum(v[2] for v in resto.values())

    items: list[FinalidadItem] = [
        FinalidadItem(
            clave=clave,
            label=LABELS_FINALIDAD[clave],
            count=int(vals[0]),
            monto_inicial=vals[1],
            monto_vigente=vals[2],
            participacion_techo_pct=_pct(vals[2], total_vigente),
        )
        for clave, vals in destacadas
    ]

    count_bucket = int(sum(v[0] for v in resto.values()))
    inicial_bucket = sum(v[1] for v in resto.values())
    vigente_bucket = sum(v[2] for v in resto.values())
    detalle = tuple(
        FinalidadDetalle(
            clave=clave,
            label=_label_detalle(clave),
            count=int(vals[0]),
            monto_inicial=vals[1],
            monto_vigente=vals[2],
            participacion_techo_pct=_pct(vals[2], total_vigente),
        )
        # Lo más grande primero: el ciudadano tiene que ver Servicios
        # Económicos antes que el ruido de parseo.
        for clave, vals in sorted(
            resto.items(), key=lambda kv: kv[1][2], reverse=True
        )
    )
    items.append(
        FinalidadItem(
            clave=SIN_CLASIFICAR,
            label="Sin clasificar",
            count=count_bucket,
            monto_inicial=inicial_bucket,
            monto_vigente=vigente_bucket,
            participacion_techo_pct=_pct(vigente_bucket, total_vigente),
            detalle=detalle,
        )
    )

    return Finalidades(
        ejercicio=ejercicio,
        total_inicial=total_inicial,
        total_vigente=total_vigente,
        total_registros=registros,
        items=tuple(items),
        honestidad=Honestidad(
            es_techo=ES_TECHO,
            # Un corte sin filas no afirma nada: `inicial == vigente` es una
            # propiedad del corte, y sin corte no hay propiedad que valga.
            inicial_es_vigente=registros > 0 and distintos == 0,
            filas_inicial_distinto_vigente=distintos,
            es_credito_modificado=ES_CREDITO_MODIFICADO,
            incluye_devengado_cge=INCLUYE_DEVENGADO_CGE,
            notas=_notas_honestidad(registros, distintos),
        ),
    )


async def fetch_finalidades(db: AsyncSession, ejercicio: int) -> Finalidades | None:
    """Leer `presupuesto_base` del ejercicio y doblarlo en 3+1.

    Devuelve `None` cuando el ejercicio no tiene Ley/Mapas cargada.  Es a
    propósito: un ejercicio sin presupuesto no es "techo $0", es un hueco, y el
    llamador tiene que poder declararlo en vez de dibujar una torta vacía.
    """
    result = await db.execute(
        select(
            PresupuestoBase.partida_presupuestaria,
            PresupuestoBase.monto_inicial,
            PresupuestoBase.monto_vigente,
        ).where(PresupuestoBase.ejercicio == ejercicio)
    )
    rows = [(r[0], r[1], r[2]) for r in result.all()]
    if not rows:
        return None
    return agregar_finalidades(rows, ejercicio)

"""
Presupuesto Tools — contexto de ejecución presupuestaria para el Insight Agent.

Lee de las mismas fuentes que los endpoints de `/presupuesto`:
  - resumen de ejecución  → `get_ejecucion_resumen` (GET /presupuesto/ejecucion/resumen/)
  - organismos por gasto   → `por_organismo` de ese mismo resumen (gasto publicado
                             contrastado contra el vigente del organismo)
  - finalidades / desvío   → `fetch_finalidades` (techo) + `fetch_proxy_bo`
                             (publicado vs techo por finalidad)

Montos en millones de ARS, como los muestra la UI.  Nada se hardcodea: todo
se lee de la DB en runtime, y sin datos se devuelve None para que el prompt
lo declare en vez de inventar números.
"""

import logging
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from typing import Any

from app.api.v1.endpoints.presupuesto import get_ejecucion_resumen as _endpoint_resumen
from app.db.models import EjecucionPresupuestaria, PresupuestoBase
from app.services.ejecucion_contrast import pct_vs_vigente
from app.services.presupuesto_finalidades import fetch_finalidades
from app.services.presupuesto_matching import canonical_organismo_name, preferred_organismo_display
from app.services.proxy_bo_finalidad import fetch_proxy_bo
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

INTENT_RESUMEN = "ejecucion_resumen"
INTENT_ORGANISMOS = "organismos"
INTENT_FINALIDADES = "finalidades"
# Cuarta pregunta, la que faltaba: "desglosá los gastos de X".  Las otras tres son
# agregadas; ninguna devuelve el detalle de un organismo puntual.
INTENT_ORGANISMO_DETALLE = "organismo_detalle"

# Disciplina de honestidad heredada de Ampliación B (sin tocar su UI)
HONESTIDAD = (
    "El numerador es lo PUBLICADO en el Boletín Oficial (proxy BO: llamados, "
    "adjudicaciones, contratos y pagos); NO es Devengado de la Contaduría ni caja.",
    "El denominador es el presupuesto vigente ANUAL de la Ley; no se prorratea por los "
    "meses cubiertos.",
)


def _norm(text: str) -> str:
    """lowercase sin tildes, para matchear 'desvío'/'desvio', 'ejecución'/'ejecucion'."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


_EJECUCION_WORDS = ("ejecut", "ejecucion", "gasto", "gastad", "se gasto", "cuanto se gasto")
_PRESUPUESTO_WORDS = ("presupuest", "vigente", "credito", "techo")
_GASTO_WORDS = ("gasto", "gasta", "gastan", "gastaron", "erogacion", "ejecut", "ejecucion", "presupuest")
_ORG_WORDS = ("organismo", "ministerio", "reparticion", "secretaria", "agencia")
_FINALIDAD_WORDS = ("finalidad", "finalidades", "funcion", "funciones")
_DESVIO_WORDS = ("desvio", "desviacion", "desvian", "sobreejecu", "subejecu", "brecha")
# Verbos de "abrime este organismo", que ninguno de los tres intents agregados cubre.
_DETALLE_WORDS = (
    "desglos", "detall", "discrimin", "por etapa", "por mes", "composicion",
    "en que se gasto", "a que se destin", "como se compone",
)


def detect_presupuesto_intents(query: str) -> set[str]:
    """
    Qué contexto de presupuesto pide una query.

    (a) "% del presupuesto vigente ejecutado"   → ejecucion_resumen
    (b) "organismos que concentran mayor gasto" → organismos
    (c) "finalidades con mayor desvío"          → finalidades
    (d) "desglosá los gastos de <organismo>"    → organismo_detalle
    """
    q = _norm(query)
    intents: set[str] = set()

    has_ejecucion = any(w in q for w in _EJECUCION_WORDS)
    has_presupuesto = any(w in q for w in _PRESUPUESTO_WORDS)
    has_pct = "porcentaje" in q or "%" in q or "cuanto" in q

    if (has_ejecucion and (has_presupuesto or has_pct)) or (has_presupuesto and has_pct):
        intents.add(INTENT_RESUMEN)

    # (d) No pide un agregado: pide abrir uno.  Necesita señal de gasto además del
    # verbo, así "desglosá la metodología" no se lleva un contexto de presupuesto.
    pide_detalle = any(w in q for w in _DETALLE_WORDS) and any(w in q for w in _GASTO_WORDS)
    if pide_detalle:
        intents.add(INTENT_ORGANISMO_DETALLE)

    # El agregado y el desglose compiten por la misma frase: "desglosá los gastos del
    # ministerio de salud" trae "ministerio" y "gastos", que es la firma de (b).  Si
    # piden abrir un organismo puntual, el top-5 es ruido, no contexto.
    if (any(w in q for w in _ORG_WORDS) and any(w in q for w in _GASTO_WORDS)
            and not pide_detalle):
        intents.add(INTENT_ORGANISMOS)

    if any(w in q for w in _FINALIDAD_WORDS) or (
        any(w in q for w in _DESVIO_WORDS) and has_presupuesto
    ):
        intents.add(INTENT_FINALIDADES)

    return intents


def _m(value: float | None) -> float | None:
    """ARS → millones de ARS (unidad de la UI)."""
    return None if value is None else round(float(value) / 1_000_000.0, 2)


# Tokens que no identifican a un organismo (ni sirven para sus iniciales).
_ORG_GENERICOS = {
    "de", "del", "la", "las", "los", "y", "e", "el",
    "s.a.", "s.a", "s.a.u", "s.a.u.", "s.r.l.", "s.e.m.", "sa", "sau", "srl", "sem",
}
# Largo mínimo de una sigla para fusionar organismos.  Con 3 letras las colisiones
# son demasiado frecuentes como para unir dos nombres en un mismo bucket.
_LARGO_MIN_SIGLA = 4


def _tokens_distintivos(canon: str) -> set[str]:
    """Palabras que identifican al organismo, sin genéricos ni siglas societarias."""
    return {t for t in _norm(canon).split() if t not in _ORG_GENERICOS and len(t) > 1}


def _org_acronyms(canon: str) -> set[str]:
    """Siglas atribuibles a un nombre canónico: el paréntesis y las iniciales.

    Es lo que puentea `EPEC` con `EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA S.A.U`,
    que la canonización de nombres no junta porque son cadenas distintas.
    """
    siglas: set[str] = set()
    for parent in re.findall(r"\(([^)]*)\)", canon):
        letras = re.sub(r"[^A-Z]", "", parent)
        if len(letras) >= _LARGO_MIN_SIGLA:
            siglas.add(letras)

    palabras = [p for p in canon.split() if p.lower() not in _ORG_GENERICOS and len(p) > 1]
    if len(palabras) >= 2:
        iniciales = "".join(p[0] for p in palabras)
        if len(iniciales) >= _LARGO_MIN_SIGLA:
            siglas.add(iniciales)
    return siglas


def _familias_de_organismos(canones: Iterable[str]) -> list[set[str]]:
    """Agrupa los canónicos que son el mismo organismo, vía siglas compartidas.

    `canonical_organismo_name` ya junta las grafías con tilde y mayúsculas, pero deja
    `EPEC` aparte del nombre completo.  Sin esta unión, el desglose de EPEC mostraría
    una fracción de su gasto publicado.
    """
    padre: dict[str, str] = {}

    def find(x: str) -> str:
        padre.setdefault(x, x)
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    for canon in canones:
        raiz = find(canon)
        for sigla in _org_acronyms(canon):
            otra = find(sigla)
            if otra != raiz:
                padre[otra] = raiz

    familias: dict[str, set[str]] = defaultdict(set)
    for canon in canones:
        familias[find(canon)].add(canon)
    return list(familias.values())


def resolver_familia_organismo(consulta: str, canones: Iterable[str]) -> set[str] | None:
    """Qué organismo nombra la consulta.  None si no nombra a ninguno.

    Tres formas de nombrar al mismo organismo, en orden de fuerza:

    1. **Nombre completo**: todas sus palabras identificatorias están en la frase.
    2. **Nombre parcial**: ≥2 palabras identificatorias y ≥60% del nombre — cubre
       "Secretaría de Infraestructura Hídrica" contra "...Hídrica y Gasífera".
    3. **Sigla**: aparece como palabra suelta, o es prefijo de una palabra de la
       frase — así "acif" llega a la familia cuya sigla es `ACIFSEM`.

    Los empates se resuelven por orden determinista; con el corpus actual no se dan.
    """
    q = _norm(consulta)
    q_palabras = set(re.sub(r"[^a-z0-9]+", " ", q).split())
    q_largas = {t for t in q_palabras if len(t) >= _LARGO_MIN_SIGLA}

    mejor_clave = (0, 0, 0)
    mejor: set[str] | None = None
    for familia in _familias_de_organismos(canones):
        clave = (0, 0, 0)
        for canon in sorted(familia):
            tokens = _tokens_distintivos(canon)
            if len(tokens) < 2:
                continue
            comunes = tokens & q_palabras
            if tokens <= q_palabras:
                clave = max(clave, (2, len(tokens), 0))
            elif len(comunes) >= 2 and len(comunes) / len(tokens) >= 0.6:
                clave = max(clave, (1, len(comunes), 0))

        if clave[0] == 0:
            for canon in sorted(familia):
                for sigla in _org_acronyms(canon):
                    baja = sigla.lower()
                    if re.search(rf"\b{re.escape(baja)}\b", q) or any(
                        baja.startswith(t) for t in q_largas
                    ):
                        clave = max(clave, (0, len(sigla), 0))

        if (clave[0] or clave[1]) and clave > mejor_clave:
            mejor_clave, mejor = clave, familia
    return mejor


class PresupuestoTools:
    """Herramientas de lectura de ejecución presupuestaria para el chat."""

    @staticmethod
    async def resolve_ejercicio(db: AsyncSession) -> int:
        """Ejercicio con Ley cargada: el año en curso si existe, si no el último cargado."""
        year = date.today().year
        result = await db.execute(
            select(func.max(PresupuestoBase.ejercicio)).where(PresupuestoBase.ejercicio <= year)
        )
        return result.scalar() or year

    @staticmethod
    async def get_ejecucion_resumen(db: AsyncSession, ejercicio: int | None = None) -> dict[str, Any] | None:
        """Resumen global: vigente, publicado, compromiso/ejecución y % sobre vigente."""
        ejercicio = ejercicio or await PresupuestoTools.resolve_ejercicio(db)

        vigente = (await db.execute(
            select(func.coalesce(func.sum(PresupuestoBase.monto_vigente), 0))
            .where(PresupuestoBase.ejercicio == ejercicio)
        )).scalar() or 0.0

        r = await _endpoint_resumen(
            fecha_desde=None, fecha_hasta=None, jurisdiccion=None, ejercicio=ejercicio, db=db
        )
        if not vigente and not r.total_canonical:
            return None

        t = r.cobertura_temporal
        return {
            "ejercicio": ejercicio,
            "unidad": "millones de ARS",
            "monto_vigente_total": _m(vigente),
            "monto_publicado_total": _m(r.monto_canonical),
            "monto_compromiso": _m(r.monto_compromiso),
            "monto_ejecucion_pagos": _m(r.monto_ejecucion),
            "pct_ejecucion_sobre_vigente": pct_vs_vigente(r.monto_ejecucion, vigente),
            "pct_compromiso_sobre_vigente": pct_vs_vigente(r.monto_compromiso, vigente),
            "actos_publicados": r.total_canonical,
            "organismos_sobre_compromiso": r.sobre_compromiso_count,
            "periodo": {
                "mes_desde": t.mes_desde,
                "mes_hasta": t.mes_hasta,
                "meses_cubiertos": t.meses_cubiertos,
                "meses_del_ejercicio": t.meses_del_ejercicio,
                "meses_vencidos_sin_ingesta": list(t.meses_vencidos_sin_ingesta),
            },
            "pct_publicado_sin_denominador": r.cobertura.pct_sin_denominador,
            "honestidad": list(HONESTIDAD),
            "_por_organismo": r.por_organismo,
        }

    @staticmethod
    def top_organismos(resumen: dict[str, Any], limit: int = 10) -> list[dict[str, Any]]:
        """Organismos que concentran más gasto publicado (del mismo resumen)."""
        orgs = sorted(resumen.get("_por_organismo") or [], key=lambda o: o.monto_total, reverse=True)
        return [
            {
                "organismo": o.organismo,
                "monto_publicado": _m(o.monto_total),
                "monto_compromiso": _m(o.monto_compromiso),
                "monto_ejecucion_pagos": _m(o.monto_ejecucion),
                "monto_vigente": _m(o.monto_vigente),
                "pct_ejecucion": o.pct_ejecucion,
                "pct_compromiso": o.pct_compromiso,
                "actos": o.count,
            }
            for o in orgs[:limit]
        ]

    @staticmethod
    async def get_finalidades_desvio(db: AsyncSession, ejercicio: int | None = None) -> dict[str, Any] | None:
        """Techo por finalidad + publicado BO vs techo, ordenado por mayor desvío."""
        ejercicio = ejercicio or await PresupuestoTools.resolve_ejercicio(db)
        finalidades = await fetch_finalidades(db, ejercicio)
        if finalidades is None:
            return None
        proxy = await fetch_proxy_bo(db, ejercicio)
        proxy_by_clave = {p.clave: p for p in proxy.items} if proxy else {}

        items = []
        for f in finalidades.items:
            p = proxy_by_clave.get(f.clave)
            items.append({
                "clave": f.clave,
                "finalidad": f.label,
                "monto_techo": _m(f.monto_vigente),
                "participacion_techo_pct": f.participacion_techo_pct,
                "monto_publicado_bo": _m(p.monto_publicado) if p else None,
                "pct_publicado_sobre_techo": p.pct_publicado_techo if p else None,
            })

        # Desvío = distancia del % publicado respecto del promedio del ejercicio
        pcts = [i["pct_publicado_sobre_techo"] for i in items if i["pct_publicado_sobre_techo"] is not None]
        promedio = round(sum(pcts) / len(pcts), 2) if pcts else None
        for i in items:
            pct = i["pct_publicado_sobre_techo"]
            i["desvio_pp_vs_promedio"] = (
                round(pct - promedio, 2) if pct is not None and promedio is not None else None
            )
        items.sort(key=lambda i: abs(i["desvio_pp_vs_promedio"] or 0), reverse=True)

        return {
            "ejercicio": ejercicio,
            "unidad": "millones de ARS",
            "pct_publicado_promedio": promedio,
            "finalidades": items,
            "notas": list(finalidades.honestidad.notas) + (list(proxy.honestidad.notas) if proxy else []),
        }


    @staticmethod
    async def get_organismo_desglose(
        db: AsyncSession, consulta: str, ejercicio: int | None = None,
    ) -> dict[str, Any] | None:
        """Desglose de lo publicado para UN organismo, por etapa y por mes.

        Es la pregunta que faltaba: las otras tres son agregadas.  Devuelve None si
        la consulta no nombra a ningún organismo de los datos — no si el organismo
        existe pero no publicó nada, que es un caso distinto y se informa con ceros.

        Junta las grafías del mismo organismo.  En el corpus, EPEC aparece como
        `EPEC`, `EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA S.A.U` y variantes con
        tilde, punto y `(EPEC)`: sin unirlas, el desglose mostraría una fracción.
        """
        ejercicio = ejercicio or await PresupuestoTools.resolve_ejercicio(db)

        filas = (await db.execute(
            select(
                EjecucionPresupuestaria.organismo,
                EjecucionPresupuestaria.etapa_gasto,
                EjecucionPresupuestaria.fecha_boletin,
                EjecucionPresupuestaria.monto,
            ).where(
                EjecucionPresupuestaria.is_duplicate == 0,
                extract("year", EjecucionPresupuestaria.fecha_boletin) == ejercicio,
            )
        )).all()
        if not filas:
            return None

        por_canon: dict[str, list[tuple[str, str | None, Any, float]]] = defaultdict(list)
        for organismo, etapa, fecha, monto in filas:
            clave = canonical_organismo_name(organismo)
            if clave:
                por_canon[clave].append((organismo, etapa, fecha, float(monto or 0.0)))

        familia = resolver_familia_organismo(consulta, list(por_canon))
        if not familia:
            return None

        propias = [fila for canon in familia for fila in por_canon.get(canon, [])]
        if not propias:
            return None

        por_etapa: dict[str, dict[str, float]] = defaultdict(lambda: {"monto": 0.0, "actos": 0})
        por_mes: dict[str, dict[str, float]] = defaultdict(lambda: {"monto": 0.0, "actos": 0})
        compromiso = ejecucion = 0.0

        for _grafia, etapa, fecha, monto in propias:
            etapa = etapa or "(sin etapa)"
            mes = fecha.strftime("%Y-%m") if hasattr(fecha, "strftime") else str(fecha)[:7]
            for acumulador, clave in ((por_etapa, etapa), (por_mes, mes)):
                acumulador[clave]["monto"] += monto
                acumulador[clave]["actos"] += 1
            if etapa == "pago":
                ejecucion += monto
            else:
                compromiso += monto

        grafias = sorted({fila[0] for fila in propias})
        canon_principal = preferred_organismo_display(grafias)

        vigente = (await db.execute(
            select(PresupuestoBase.organismo, PresupuestoBase.monto_vigente)
            .where(PresupuestoBase.ejercicio == ejercicio)
        )).all()
        vigente_organismo = sum(
            float(monto or 0.0) for organismo, monto in vigente
            if canonical_organismo_name(organismo) in familia
        )

        return {
            "ejercicio": ejercicio,
            "unidad": "millones de ARS",
            "organismo": canon_principal,
            "grafias_unificadas": grafias,
            "monto_publicado": _m(sum(f[3] for f in propias)),
            "monto_compromiso": _m(compromiso),
            "monto_ejecucion_pagos": _m(ejecucion),
            "monto_vigente": _m(vigente_organismo) or None,
            "pct_ejecucion_sobre_vigente": pct_vs_vigente(ejecucion, vigente_organismo),
            "actos": len(propias),
            "por_etapa": sorted(
                ({"etapa": e, "monto": _m(v["monto"]), "actos": int(v["actos"])}
                 for e, v in por_etapa.items()),
                key=lambda i: i["monto"] or 0.0, reverse=True,
            ),
            "por_mes": sorted(
                ({"mes": m, "monto": _m(v["monto"]), "actos": int(v["actos"])}
                 for m, v in por_mes.items()),
                key=lambda i: i["mes"],
            ),
            "honestidad": list(HONESTIDAD),
        }


def public_resumen(resumen: dict[str, Any]) -> dict[str, Any]:
    """El resumen sin los objetos internos (para el contexto del modelo)."""
    return {k: v for k, v in resumen.items() if not k.startswith("_")}


def build_presupuesto_system_block(resumen: dict[str, Any] | None) -> str:
    """Bloque fijo del system prompt con el resumen de ejecución presupuestaria."""
    if not resumen:
        return (
            "RESUMEN DE EJECUCIÓN PRESUPUESTARIA: sin datos de ejecución disponibles "
            "(no hay presupuesto ni ejecución cargados, o falló la lectura). "
            "Si te preguntan por presupuesto, decilo explícitamente y NO inventes cifras."
        )

    p = resumen.get("periodo") or {}
    lines = [
        f"RESUMEN DE EJECUCIÓN PRESUPUESTARIA — ejercicio {resumen['ejercicio']} "
        f"(fuente: /presupuesto/ejecucion/resumen/, montos en {resumen['unidad']}):",
        f"- Presupuesto vigente total: {resumen['monto_vigente_total']}",
        f"- Publicado en Boletín Oficial: {resumen['monto_publicado_total']} "
        f"({resumen['actos_publicados']} actos)",
        f"- Compromiso (llamados/adjudicaciones/contratos): {resumen['monto_compromiso']} "
        f"= {resumen['pct_compromiso_sobre_vigente']}% del vigente",
        f"- Ejecución (pagos publicados): {resumen['monto_ejecucion_pagos']} "
        f"= {resumen['pct_ejecucion_sobre_vigente']}% del vigente",
        f"- Período cubierto: {p.get('mes_desde')} a {p.get('mes_hasta')} "
        f"({p.get('meses_cubiertos')} de {p.get('meses_del_ejercicio')} meses); "
        f"meses vencidos sin ingesta: {p.get('meses_vencidos_sin_ingesta') or 'ninguno'}",
        f"- Publicado sin denominador (organismo sin match en la Ley): "
        f"{resumen['pct_publicado_sin_denominador']}%",
        "Reglas de honestidad:",
    ]
    lines += [f"- {n}" for n in resumen.get("honestidad", HONESTIDAD)]
    lines.append(
        "- Nunca llames 'Devengado' a estos montos; decí 'publicado en BO' o 'proxy BO'. "
        "Aclarará el período cubierto cuando des un %."
    )
    return "\n".join(lines)

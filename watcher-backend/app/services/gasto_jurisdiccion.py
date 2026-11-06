"""Gasto detectado agregado por jurisdicción, para el mapa (WMA1).

Es el mismo universo que `GET /gasto/detectado`: actos con monto y figura de
gasto, sin `no_es_gasto`.  Cambia la forma del resultado, no el criterio:

- `actos` cuenta actos **canónicos** (las republicaciones no cuentan dos veces);
  `republicaciones` dice cuántas quedaron afuera.
- `gasto` suma sin republicaciones, igual que `suma` en el listado.
- `gasto_per_capita` usa la población del Censo 2022 y es `None` cuando la
  jurisdicción no tiene actos: "sin datos" no es "$0 por habitante".

Las jurisdicciones sin ningún acto se devuelven igual (con `cobertura: false`)
porque el mapa tiene que pintarlas en gris: un hueco no es gasto cero.

El gasto provincial no se reparte entre municipios (no hay forma de saber en qué
jurisdicción se gastó), así que va en `por_nivel` y no en `jurisdicciones`.
"""

from __future__ import annotations

from app.db.models import Analisis
from app.services.gasto_classifier import TIPO_NO_ES_GASTO
from app.services.jurisdicciones import catalogo, nivel_de, resolver
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

FUENTE_CATALOGO = {
    "catalogo": "ReFeGLo (Ministerio del Interior) — Registro Federal de Gobiernos Locales",
    "poblacion": "Censo Nacional de Población, Hogares y Viviendas 2022 (INDEC)",
    "limites": "OpenStreetMap, boundary=administrative admin_level=7 (© OpenStreetMap contributors, ODbL)",
    "fecha": "2026-11-06",
    "nota": (
        "El gasto es el detectado en los boletines y portales del corte: en muchos actos "
        "el monto es el presupuesto oficial del llamado, no lo adjudicado ni lo pagado. "
        "El gasto provincial no se asigna a municipios. Las áreas grises no tienen datos, "
        "no gasto cero."
    ),
}

_NIVELES_CON_JURISDICCION = ("municipal", "comunal")


async def por_jurisdiccion(db: AsyncSession) -> dict:
    canonico = func.coalesce(Analisis.is_duplicate_gasto, 0) == 0
    universo = [
        Analisis.monto_numerico > 0,
        Analisis.tipo_gasto.is_not(None),
        Analisis.tipo_gasto != TIPO_NO_ES_GASTO,
    ]
    filas = (
        await db.execute(
            select(
                Analisis.nivel,
                Analisis.municipio,
                func.count().label("actos"),
                func.coalesce(
                    func.sum(case((canonico, 1), else_=0)), 0
                ).label("actos_canonicos"),
                func.coalesce(
                    func.sum(case((canonico, Analisis.monto_numerico), else_=0.0)), 0.0
                ).label("gasto"),
            )
            .where(*universo)
            .group_by(Analisis.nivel, Analisis.municipio)
        )
    ).all()

    acumulado: dict[str, dict] = {}
    por_nivel: dict[str, dict] = {}
    sin_jurisdiccion = {"actos": 0, "gasto": 0.0, "niveles": set()}

    for nivel, municipio, actos, actos_canonicos, gasto in filas:
        nivel = nivel or "desconocido"
        total_nivel = por_nivel.setdefault(nivel, {"nivel": nivel, "actos": 0, "gasto": 0.0})
        total_nivel["actos"] += int(actos_canonicos)
        total_nivel["gasto"] += float(gasto)

        if nivel not in _NIVELES_CON_JURISDICCION:
            continue
        entrada = resolver(municipio)
        if entrada is None:
            sin_jurisdiccion["actos"] += int(actos_canonicos)
            sin_jurisdiccion["gasto"] += float(gasto)
            sin_jurisdiccion["niveles"].add(nivel)
            continue

        acumula = acumulado.setdefault(
            entrada["codigo"], {"actos": 0, "actos_totales": 0, "republicaciones": 0, "gasto": 0.0}
        )
        acumula["actos"] += int(actos_canonicos)
        acumula["actos_totales"] += int(actos)
        acumula["republicaciones"] += int(actos) - int(actos_canonicos)
        acumula["gasto"] += float(gasto)

    jurisdicciones = []
    for entrada in catalogo():
        datos = acumulado.get(
            entrada["codigo"], {"actos": 0, "actos_totales": 0, "republicaciones": 0, "gasto": 0.0}
        )
        poblacion = entrada.get("poblacion_2022")
        gasto = round(datos["gasto"], 2)
        jurisdicciones.append({
            "codigo": entrada["codigo"],
            "nombre": entrada["nombre"],
            "tipo": entrada.get("tipo"),
            "departamento": entrada.get("departamento"),
            "nivel": nivel_de(entrada),
            "poblacion_2022": poblacion,
            "actos": datos["actos"],
            "republicaciones": datos["republicaciones"],
            "gasto": gasto,
            # Sin actos no hay per cápita: no se inventa un cero.
            "gasto_per_capita": round(gasto / poblacion, 2) if poblacion and datos["actos"] else None,
            "cobertura": datos["actos"] > 0,
        })

    return {
        "jurisdicciones": jurisdicciones,
        "por_nivel": sorted(por_nivel.values(), key=lambda n: n["nivel"]),
        "sin_jurisdiccion": {
            "actos": sin_jurisdiccion["actos"],
            "gasto": round(sin_jurisdiccion["gasto"], 2),
            "niveles": sorted(sin_jurisdiccion["niveles"]),
        },
        "totales": {
            "actos": sum(j["actos"] for j in jurisdicciones) + sin_jurisdiccion["actos"],
            "gasto": round(sum(j["gasto"] for j in jurisdicciones) + sin_jurisdiccion["gasto"], 2),
            "con_cobertura": sum(1 for j in jurisdicciones if j["cobertura"]),
            "jurisdicciones": len(jurisdicciones),
        },
        "fuente": FUENTE_CATALOGO,
    }

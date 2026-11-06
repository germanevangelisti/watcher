"""Genera el catálogo de jurisdicciones de Córdoba y su GeoJSON estático (WMA1).

Por qué existe: el mapa de gasto por jurisdicción necesita (a) la lista completa
de municipios y comunas —incluidas las que **no** tienen datos, que se pintan en
gris—, (b) la población del Censo 2022 para el gasto per cápita y (c) límites
simplificados para dibujar.  Nada de eso se pide en tiempo de ejecución: el mapa
no debe depender de una API externa que puede no responder.

Fuentes (bajadas el 2026-11-06):

- **Nombres, tipo, departamento, código y población**: ReFeGLo — Base de Registro
  Federal de Gobiernos Locales (Ministerio del Interior), campo
  ``población_censo_2022``.  427 gobiernos locales de Córdoba (260 municipios y
  167 comunas).  CSV separado por ``;`` y codificado en latin-1.
  ``http://datos.mininterior.gob.ar/dataset/8431ab79-3f44-41ee-b72b-cdc645f68d1e``
- **Límites**: OpenStreetMap, relaciones ``boundary=administrative`` +
  ``admin_level=7`` dentro de la relación de la provincia de Córdoba
  (``rel(3592494)``), vía Overpass API.  © OpenStreetMap contributors, ODbL 1.0.
  Se eligió OSM porque el IGN (``ign.gob.ar``) y IDECOR no respondieron desde
  este entorno; el archivo generado queda versionado, así que el frontend no
  consulta Overpass.

Los nombres de OSM traen prefijos ("Municipio de …", "Comuna de …") y variantes
("Negro Huasi" es la comuna que ReFeGLo llama "Las Cañadas").  El emparejamiento
es por nombre normalizado, después por subconjunto de tokens y, como último
recurso, por centroide más cercano (< 40 km) con similitud de nombre > 0,55.
Todo emparejamiento no exacto se imprime para revisarlo.

Uso (desde ``watcher-backend/``):

    python scripts/build_municipios_cordoba.py \
        --refeglo brgl.csv --osm geo7.json \
        --catalogo app/data/municipios_cordoba.json \
        --geojson ../watcher-frontend/public/geo/municipios-cordoba.geojson
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import math
import re
import unicodedata
from pathlib import Path

# Variantes de nombre entre OSM y ReFeGLo que la normalización no resuelve.
ALIASES = {
    "negro huasi": "las canadas",
}

PREFIJOS = re.compile(r"^(municipio|municipalidad|comuna|la ciudad de|ciudad de)\s+(de\s+)?")
SIMPLIFY_TOL = 0.0015  # grados (~150 m): sobra para un mapa provincial


def normalizar(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = s.lower().strip()
    s = PREFIJOS.sub("", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _poblacion(raw: str | None) -> int | None:
    limpio = (raw or "").replace(".", "").strip()
    return int(limpio) if limpio.isdigit() else None


def _coordenada(raw: str | None) -> float | None:
    try:
        return float((raw or "").replace(",", "."))
    except ValueError:
        return None


def leer_refeglo(path: Path) -> list[dict]:
    rows = list(csv.DictReader(path.open(encoding="latin-1"), delimiter=";"))
    catalogo = []
    for r in rows:
        if r["provincia"].strip().lower() != "córdoba":
            continue
        catalogo.append({
            "codigo": r["cod_gobierno_local"].strip(),
            "nombre": " ".join(r["gobierno_local"].split()),
            "tipo": r["categoria_de_gobierno"].strip().lower(),
            "departamento": " ".join(r["departamento"].split()),
            "poblacion_2022": _poblacion(r.get("población_censo_2022")),
            "lat": _coordenada(r.get("latitud")),
            "lon": _coordenada(r.get("longitud")),
        })
    return catalogo


# --- geometría -------------------------------------------------------------


def _distancia_punto_segmento(p, a, b) -> float:
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def simplificar(puntos: list, tol: float) -> list:
    """Douglas-Peucker.  Los límites son para mirar, no para medir."""
    if len(puntos) < 3:
        return puntos
    dmax, idx = 0.0, 0
    for i in range(1, len(puntos) - 1):
        d = _distancia_punto_segmento(puntos[i], puntos[0], puntos[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        return simplificar(puntos[: idx + 1], tol)[:-1] + simplificar(puntos[idx:], tol)
    return [puntos[0], puntos[-1]]


def _ensamblar_anillos(members: list) -> list[tuple[str, list]]:
    """Une los ``way`` de una relación en anillos cerrados (lon, lat)."""
    ways = []
    for m in members:
        geom = m.get("geometry") or []
        if len(geom) >= 2:
            ways.append((m.get("role") or "outer", [(g["lon"], g["lat"]) for g in geom]))
    anillos, usado = [], [False] * len(ways)
    for i, (role, pts) in enumerate(ways):
        if usado[i]:
            continue
        usado[i] = True
        anillo = list(pts)
        cambio = True
        while cambio and anillo[0] != anillo[-1]:
            cambio = False
            for j, (_, otro) in enumerate(ways):
                if usado[j]:
                    continue
                if otro[0] == anillo[-1]:
                    anillo.extend(otro[1:])
                elif otro[-1] == anillo[-1]:
                    anillo.extend(list(reversed(otro))[1:])
                elif otro[-1] == anillo[0]:
                    anillo = otro[:-1] + anillo
                elif otro[0] == anillo[0]:
                    anillo = list(reversed(otro))[:-1] + anillo
                else:
                    continue
                usado[j] = True
                cambio = True
                break
        if anillo[0] != anillo[-1]:
            anillo.append(anillo[0])
        if len(anillo) >= 4:
            anillos.append((role, anillo))
    return anillos


def _dentro_de(punto, anillo) -> bool:
    x, y = punto
    dentro = False
    for i in range(len(anillo) - 1):
        x1, y1 = anillo[i]
        x2, y2 = anillo[i + 1]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
            dentro = not dentro
    return dentro


def _centroide(members: list) -> tuple[float, float] | None:
    pts = [(g["lon"], g["lat"]) for m in members for g in (m.get("geometry") or [])]
    if not pts:
        return None
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


# --- emparejamiento --------------------------------------------------------


def emparejar(relaciones: list[dict], catalogo: list[dict]) -> tuple[dict, list[str]]:
    """Devuelve {osm_id: entrada del catálogo} y el log de matches no exactos."""
    por_nombre = {}
    for c in catalogo:
        por_nombre.setdefault(normalizar(c["nombre"]), c)
    for alias, destino in ALIASES.items():
        if destino in por_nombre:
            por_nombre[alias] = por_nombre[destino]

    usados: set[str] = set()
    resultado: dict[int, dict] = {}
    log: list[str] = []
    pendientes: list[dict] = []

    def tokens(s: str) -> set[str]:
        return set(normalizar(s).split())

    for el in relaciones:
        raw = (el.get("tags") or {}).get("name", "")
        c = por_nombre.get(normalizar(raw))
        if c and c["codigo"] not in usados:
            usados.add(c["codigo"])
            resultado[el["id"]] = c
        else:
            pendientes.append(el)

    restantes = []
    for el in pendientes:
        raw = (el.get("tags") or {}).get("name", "")
        t = tokens(raw)
        cands = [
            c for c in catalogo
            if c["codigo"] not in usados and t
            and (t <= tokens(c["nombre"]) or tokens(c["nombre"]) <= t)
        ]
        if len(cands) == 1:
            usados.add(cands[0]["codigo"])
            resultado[el["id"]] = cands[0]
            log.append(f"subset: {raw!r} -> {cands[0]['nombre']!r}")
        else:
            restantes.append(el)

    for el in restantes:
        raw = (el.get("tags") or {}).get("name", "")
        centro = _centroide(el.get("members") or [])
        if not centro:
            log.append(f"SIN GEOMETRIA: {raw!r}")
            continue
        mejor = None
        for c in catalogo:
            if c["codigo"] in usados or c["lat"] is None or c["lon"] is None:
                continue
            km = math.hypot(centro[0] - c["lon"], centro[1] - c["lat"]) * 111
            sim = difflib.SequenceMatcher(None, normalizar(raw), normalizar(c["nombre"])).ratio()
            score = (km, -sim)
            if mejor is None or score < mejor[0]:
                mejor = (score, c, km, sim)
        if mejor and mejor[2] < 40 and mejor[3] > 0.55:
            _, c, km, sim = mejor
            usados.add(c["codigo"])
            resultado[el["id"]] = c
            log.append(f"centroide: {raw!r} -> {c['nombre']!r} ({km:.1f} km, sim {sim:.2f})")
        else:
            log.append(f"NO EMPAREJADO: {raw!r}")
    return resultado, log


def construir_geojson(relaciones: list[dict], matches: dict[int, dict], catalogo: list[dict]) -> dict:
    features = []
    for el in relaciones:
        cat = matches.get(el["id"])
        if not cat:
            continue
        anillos = _ensamblar_anillos(el.get("members") or [])
        outers = [r for role, r in anillos if role != "inner"]
        inners = [r for role, r in anillos if role == "inner"]
        if not outers:
            continue
        outers.sort(key=len, reverse=True)
        polys = [[simplificar(o, SIMPLIFY_TOL)] for o in outers]
        for inner in inners:
            simp = simplificar(inner, SIMPLIFY_TOL)
            for poly in polys:
                if _dentro_de(inner[0], poly[0]):
                    poly.append(simp)
                    break
        features.append({
            "type": "Feature",
            "properties": {
                "codigo": cat["codigo"],
                "nombre": cat["nombre"],
                "tipo": cat["tipo"],
                "departamento": cat["departamento"],
                "poblacion_2022": cat["poblacion_2022"],
            },
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [[list(p) for p in anillo] for anillo in poly] for poly in polys
                ],
            },
        })

    # Las jurisdicciones sin polígono en OSM no se pierden: quedan como punto.
    con_poligono = {f["properties"]["codigo"] for f in features}
    for c in catalogo:
        if c["codigo"] in con_poligono or c["lat"] is None or c["lon"] is None:
            continue
        features.append({
            "type": "Feature",
            "properties": {
                "codigo": c["codigo"],
                "nombre": c["nombre"],
                "tipo": c["tipo"],
                "departamento": c["departamento"],
                "poblacion_2022": c["poblacion_2022"],
            },
            "geometry": {"type": "Point", "coordinates": [c["lon"], c["lat"]]},
        })
    return {"type": "FeatureCollection", "features": features}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refeglo", required=True, type=Path)
    parser.add_argument("--osm", required=True, type=Path)
    parser.add_argument("--catalogo", required=True, type=Path)
    parser.add_argument("--geojson", required=True, type=Path)
    args = parser.parse_args()

    catalogo = leer_refeglo(args.refeglo)
    crudo = json.loads(args.osm.read_text(encoding="utf-8"))
    relaciones = [e for e in crudo["elements"] if e.get("type") == "relation"]
    matches, log = emparejar(relaciones, catalogo)

    for linea in log:
        print(linea)
    print(f"catálogo: {len(catalogo)} · relaciones OSM: {len(relaciones)} · emparejadas: {len(matches)}")

    args.catalogo.parent.mkdir(parents=True, exist_ok=True)
    args.catalogo.write_text(
        json.dumps(catalogo, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8",
    )
    args.geojson.parent.mkdir(parents=True, exist_ok=True)
    args.geojson.write_text(
        json.dumps(construir_geojson(relaciones, matches, catalogo), ensure_ascii=False,
                   separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"escrito: {args.catalogo} ({args.catalogo.stat().st_size / 1024:.0f} KB)")
    print(f"escrito: {args.geojson} ({args.geojson.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()

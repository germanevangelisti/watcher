#!/usr/bin/env python3
"""
Exportar la muestra etiquetada a ciegas de M8 (historia `pm-gasto-deteccion-ampliada`).

El criterio de la historia pide precisión ≥ 90% en `nivel` y ≥ 80% en `tipo_gasto`
sobre ≥ 100 actos **etiquetados a mano**.  Este script produce ese insumo.

Cómo se evita que la etiqueta se contamine:

- El CSV/MD que recibe quien etiqueta trae **sólo las entradas** (fecha, organismo,
  tipo_acto del LLM, descripción, fragmento, monto) y las columnas de etiqueta
  vacías.  La predicción del clasificador (`tipo_gasto`, `nivel`, el motivo) va a
  un JSON aparte que no se entrega.
- El `muestra_id` es un hash opaco, no el id de `analisis`: sin él no se puede
  joinear la muestra contra la base para leer la predicción.
- `tipo_acto` sí va: es la salida del LLM de extracción (un insumo), no una
  predicción del clasificador que se está midiendo.

El muestreo es estratificado a propósito.  Una muestra aleatoria plana sobre el
universo sería casi toda `no_es_gasto` (73%), y la precisión resultante mediría lo
que ya sabemos en vez de la parte difícil: por eso hay cupo por tipo, y además se
sobre-muestrean los dos riesgos declarados (actos municipales/comunales y
fragmentos cortos).

Uso:
    python scripts/muestra_etiquetado_gasto.py
    python scripts/muestra_etiquetado_gasto.py --n 150 --out .tmp-muestra-gasto
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.gasto_classifier import TIPOS_GASTO, classify_gasto
from app.services.presupuesto_matching import parse_date

DB_PATH = Path(__file__).parent.parent / "sqlite.db"

_SELECT = """
    SELECT
        a.id AS id, a.boletin_id, a.tipo_acto, a.organismo, a.descripcion, a.fragmento,
        a.monto_numerico, b.date AS boletin_date, b.section AS boletin_section,
        b.source_url
    FROM analisis a
    JOIN boletines b ON a.boletin_id = b.id
    WHERE a.monto_numerico > 0
    ORDER BY b.date, a.id
"""

COLUMNAS = [
    "muestra_id", "fecha", "organismo", "tipo_acto", "descripcion", "fragmento",
    "monto", "nivel_real", "tipo_gasto_real", "nota",
]


def _muestra_id(analisis_id: int, seed: int) -> str:
    """Hash opaco: no se puede volver al id de `analisis` desde la muestra."""
    h = hashlib.sha1(f"{seed}:{analisis_id}".encode()).hexdigest()
    return h[:10]


def seleccionar(filas: list[dict], n: int, seed: int) -> list[dict]:
    """Estratificado por tipo predicho + sobre-muestreo de los riesgos."""
    rng = random.Random(seed)
    for f in filas:
        f["_clasif"] = classify_gasto(f, section=f.get("boletin_section"))

    # Estrato 1: cupo por tipo predicho, para que la muestra no sea 73% no_es_gasto.
    por_tipo: dict[str, list[dict]] = {}
    for f in filas:
        por_tipo.setdefault(f["_clasif"].tipo_gasto, []).append(f)

    cupo_tipo = max(2, (n * 3 // 5) // max(1, len(TIPOS_GASTO)))
    elegidas: list[dict] = []
    vistos: set[int] = set()
    for tipo in sorted(por_tipo):
        candidatas = por_tipo[tipo][:]
        rng.shuffle(candidatas)
        for f in candidatas[:cupo_tipo]:
            elegidas.append(f)
            vistos.add(f["id"])

    # Estrato 2: los riesgos declarados, que un muestreo proporcional subrepresenta.
    resto = [f for f in filas if f["id"] not in vistos]
    rng.shuffle(resto)
    riesgos = (
        [f for f in resto if f["_clasif"].nivel in ("municipal", "comunal")]
        + [f for f in resto if len(f.get("fragmento") or "") < 120]
    )
    for f in riesgos:
        if len(elegidas) >= n:
            break
        if f["id"] not in vistos:
            elegidas.append(f)
            vistos.add(f["id"])

    # Estrato 3: relleno aleatorio hasta N.
    for f in resto:
        if len(elegidas) >= n:
            break
        if f["id"] not in vistos:
            elegidas.append(f)
            vistos.add(f["id"])

    rng.shuffle(elegidas)
    return elegidas


def run(n: int, out: Path, seed: int) -> None:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    filas = [dict(r) for r in conn.execute(_SELECT).fetchall()]
    conn.close()

    elegidas = seleccionar(filas, n, seed)
    out.mkdir(parents=True, exist_ok=True)

    predicciones = {}
    with (out / "gasto_muestra_etiquetado.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS)
        w.writeheader()
        for f in elegidas:
            mid = _muestra_id(f["id"], seed)
            fecha = parse_date(f.get("boletin_date") or "")
            predicciones[mid] = {
                "nivel": f["_clasif"].nivel,
                "tipo_gasto": f["_clasif"].tipo_gasto,
                "motivo": f["_clasif"].tipo_gasto_motivo,
                "es_gasto_publico": f["_clasif"].is_gasto_publico,
                "section": f.get("boletin_section"),
                "largo_fragmento": len(f.get("fragmento") or ""),
            }
            w.writerow({
                "muestra_id": mid,
                "fecha": fecha.isoformat() if fecha else "",
                "organismo": (f.get("organismo") or "").strip(),
                "tipo_acto": f.get("tipo_acto") or "",
                "descripcion": (f.get("descripcion") or "").strip(),
                "fragmento": (f.get("fragmento") or "").strip()[:600],
                "monto": f.get("monto_numerico"),
                "nivel_real": "",
                "tipo_gasto_real": "",
                "nota": "",
            })

    # Copia imprimible para etiquetar leyendo, sin abrir el CSV en Excel.
    (out / "gasto_muestra_etiquetado.md").write_text(
        _md(elegidas, seed), encoding="utf-8"
    )

    (out / "gasto_muestra_predicciones.json").write_text(
        json.dumps(predicciones, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    meta = {
        "seed": seed,
        "n_pedido": n,
        "n_exportado": len(elegidas),
        "universo": len(filas),
        "por_tipo_predicho": dict(Counter(p["tipo_gasto"] for p in predicciones.values())),
        "por_nivel_predicho": dict(Counter(p["nivel"] for p in predicciones.values())),
        "con_fragmento_corto": sum(1 for p in predicciones.values() if p["largo_fragmento"] < 120),
    }
    (out / "gasto_muestra_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"muestra: {len(elegidas)} actos de {len(filas)} → {out}")
    print(f"  seed {seed} · tipos {meta['por_tipo_predicho']}")
    print(f"  niveles {meta['por_nivel_predicho']} · fragmento<120: {meta['con_fragmento_corto']}")
    print("  PARA ETIQUETAR: gasto_muestra_etiquetado.md (o .csv)")
    print("  NO ENTREGAR: gasto_muestra_predicciones.json")


def _md(filas: list[dict], seed: int) -> str:
    lineas = [
        "# Muestra para etiquetar — M8 detección de gasto",
        "",
        "Completá `nivel_real` y `tipo_gasto_real` en cada fila. **No mires ninguna predicción:**",
        "este archivo no la trae (está en un JSON aparte que no se entrega).",
        "",
        "`nivel_real`: `provincial` · `municipal` · `comunal` · `desconocido`",
        "",
        "`tipo_gasto_real`: " + " · ".join(f"`{t}`" for t in TIPOS_GASTO),
        "",
        "En `nota` podés anotar por qué dudaste; esas notas valen más que el número final.",
        "",
        "| muestra_id | fecha | organismo | tipo_acto | monto | descripcion / fragmento | nivel_real | tipo_gasto_real |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for f in filas:
        fecha = parse_date(f.get("boletin_date") or "")
        texto = ((f.get("descripcion") or "").strip() or (f.get("fragmento") or "").strip())[:300]
        texto = texto.replace("|", "/").replace("\n", " ")
        lineas.append(
            f"| {_muestra_id(f['id'], seed)} | {fecha.isoformat() if fecha else ''} "
            f"| {(f.get('organismo') or '').strip()[:60]} | {f.get('tipo_acto') or ''} "
            f"| {f.get('monto_numerico')} | {texto} | | |"
        )
    return "\n".join(lineas) + "\n"


def main() -> None:
    # La consola de Windows es cp1252 y no puede escribir "→" ni algunos acentos.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=150, help="Tamaño de la muestra (mínimo útil: 100).")
    parser.add_argument("--seed", type=int, default=20261012, help="Semilla del muestreo.")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent.parent / ".tmp-muestra-gasto")
    args = parser.parse_args()

    global DB_PATH
    run(n=args.n, out=args.out, seed=args.seed)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Medir la precisión del clasificador M8 contra la muestra etiquetada a mano.

Lee el CSV que devolvió quien etiquetó (`nivel_real`, `tipo_gasto_real`) y el JSON
de predicciones que no se le entregó, y reporta:

- precisión por eje (`nivel`, `tipo_gasto`), con el **límite inferior de Wilson al
  95%**: con n=100, un 88% puntual no es significativamente ≥ 90%, así que el
  punto solo no alcanza para decir que el criterio se cumple;
- matriz de confusión por eje;
- desagregado por sección del boletín y por largo del fragmento, que es donde
  están los riesgos declarados (fragmentos de ~290 caracteres);
- la lista de las filas que fallan, para poder mirarlas.

Uso:
    python scripts/medir_clasificacion_gasto.py
    python scripts/medir_clasificacion_gasto.py --muestra .tmp-muestra-gasto/gasto_muestra_etiquetado.csv
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from etiquetas_gasto import NIVELES, OBJETOS, TIPOS_GASTO, leer_csv, norm_label  # noqa: E402

MINIMO = 100
UMBRAL_NIVEL = 0.90
UMBRAL_TIPO = 0.80


def wilson_lower(k: int, n: int, z: float = 1.96) -> float:
    """Lower bound of the 95% Wilson interval for k/n."""
    if n == 0:
        return 0.0
    p = k / n
    centro = p + z * z / (2 * n)
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centro - margen) / (1 + z * z / n)


def _leer(muestra: Path, predicciones: Path):
    labels = {r["muestra_id"]: r for r in leer_csv(muestra)}
    preds = json.loads(predicciones.read_text(encoding="utf-8"))

    # Una etiqueta que no es del vocabulario se contaría como error de
    # clasificación.  Antes que publicar un número que mide un typo, se corta y
    # se listan para corregirlas.
    validos_tipo = set(TIPOS_GASTO) | {""}
    validos_nivel = set(NIVELES) | {""}
    validos_objeto = set(OBJETOS) | {""}
    invalidos = [
        (mid, "nivel_real", r.get("nivel_real"))
        for mid, r in labels.items()
        if norm_label(r.get("nivel_real"), "nivel") not in validos_nivel
    ] + [
        (mid, "tipo_gasto_real", r.get("tipo_gasto_real"))
        for mid, r in labels.items()
        if norm_label(r.get("tipo_gasto_real"), "tipo_gasto") not in validos_tipo
    ] + [
        (mid, "objeto_real", r.get("objeto_real"))
        for mid, r in labels.items()
        if norm_label(r.get("objeto_real"), "objeto") not in validos_objeto
    ]
    if invalidos:
        raise SystemExit(
            "❌ etiquetas fuera del vocabulario — corregilas antes de medir.\n"
            f"   nivel_real: {', '.join(sorted(NIVELES))}\n"
            f"   tipo_gasto_real: {', '.join(sorted(TIPOS_GASTO))}\n"
            f"   objeto_real: {', '.join(sorted(OBJETOS))}\n"
            + "\n".join(f"   {mid} · {campo}: {valor!r}" for mid, campo, valor in invalidos[:15])
            + (f"\n   ... y {len(invalidos) - 15} más" if len(invalidos) > 15 else "")
        )

    pares, sin_etiquetar = [], 0
    for mid, fila in labels.items():
        nivel = norm_label(fila.get("nivel_real"), "nivel")
        tipo = norm_label(fila.get("tipo_gasto_real"), "tipo_gasto")
        objeto = norm_label(fila.get("objeto_real"), "objeto")
        if not nivel and not tipo and not objeto:
            sin_etiquetar += 1
            continue
        if mid not in preds:
            raise SystemExit(f"❌ muestra_id {mid} no está en las predicciones: ¿mezclaste archivos?")
        pares.append((mid, fila, preds[mid], nivel, tipo, objeto))
    return pares, sin_etiquetar


def _reporte(pares, sin_etiquetar: int) -> str:
    out: list[str] = []
    n = len(pares)
    out.append(f"filas etiquetadas: {n}  ·  sin etiquetar: {sin_etiquetar}")
    if n < MINIMO:
        out.append(
            f"⚠️  el criterio de la historia pide ≥ {MINIMO} actos etiquetados: "
            f"con {n} la medición no alcanza."
        )

    for eje, umbral, idx_real, idx_pred in (
        ("nivel", UMBRAL_NIVEL, 3, lambda p: p["nivel"]),
        ("tipo_gasto", UMBRAL_TIPO, 4, lambda p: p["tipo_gasto"]),
        # Eje nuevo: se mide, pero el criterio de la historia no le puso umbral.
        ("objeto", None, 5, lambda p: p.get("objeto", "")),
    ):
        usables = [t for t in pares if t[idx_real]]
        aciertos = sum(1 for t in usables if t[idx_real] == idx_pred(t[2]))
        total = len(usables)
        acc = aciertos / total if total else 0.0
        cota = wilson_lower(aciertos, total)
        if umbral is None:
            estado = "(sin umbral acordado: se mide para informar)"
        else:
            estado = "✅ cumple" if cota >= umbral else "❌ no alcanza"
        out.append(
            f"\n{eje}: {aciertos}/{total} = {acc:.1%}  ·  Wilson 95% ≥ {cota:.1%}  "
            + (f"(umbral {umbral:.0%}) → " if umbral is not None else "")
            + estado
        )

        conf = Counter((t[idx_real], idx_pred(t[2])) for t in usables)
        out.append("  matriz (real → predicho):")
        for (real, pred), v in sorted(conf.items(), key=lambda kv: -kv[1]):
            marca = "" if real == pred else "   ← error"
            out.append(f"    {real:22s} → {pred:22s} {v}{marca}")

        fallos = [t for t in usables if t[idx_real] != idx_pred(t[2])]
        out.append(f"  fallas ({len(fallos)}):")
        for mid, fila, pred, real, _tipo, _objeto in fallos[:25]:
            out.append(
                f"    {mid} | {real} → {pred} | {(fila.get('organismo') or '')[:38]} "
                f"| {((fila.get('descripcion') or fila.get('fragmento') or '')[:70])}"
            )
        if len(fallos) > 25:
            out.append(f"    ... y {len(fallos) - 25} más")

        # Dónde falla: los riesgos declarados de la historia.
        por_riesgo: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for t in usables:
            pred = t[2]
            corto = pred["largo_fragmento"] < 120
            mun = pred["nivel"] in ("municipal", "comunal") or t[idx_real] in ("municipal", "comunal")
            claves = [f"fragmento {'<120' if corto else '>=120'}", f"{'muni/comunal' if mun else 'provincial'}"]
            for k in claves:
                por_riesgo[k][1] += 1
                if t[idx_real] == idx_pred(pred):
                    por_riesgo[k][0] += 1
        out.append("  desagregado:")
        for k, (ok, tot) in sorted(por_riesgo.items()):
            out.append(f"    {k:24s} {ok}/{tot} = {ok / tot:.1%}")

    return "\n".join(out)


def main() -> None:
    # La consola de Windows es cp1252 y no puede escribir "→" ni algunos acentos.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    base = Path(__file__).parent.parent / ".tmp-muestra-gasto"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--muestra", type=Path, default=base / "gasto_muestra_etiquetado.csv")
    parser.add_argument("--predicciones", type=Path, default=base / "gasto_muestra_predicciones.json")
    args = parser.parse_args()

    if not args.muestra.exists():
        raise SystemExit(f"❌ no existe {args.muestra} — corré scripts/muestra_etiquetado_gasto.py")

    pares, sin = _leer(args.muestra, args.predicciones)
    print(_reporte(pares, sin))


if __name__ == "__main__":
    main()

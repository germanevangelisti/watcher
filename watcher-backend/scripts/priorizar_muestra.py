#!/usr/bin/env python3
"""
Reordena la muestra de M8 para etiquetar primero los casos informativos.

De dónde sale el orden: son las filas donde el juez LLM local y las reglas **no
coinciden** — en `nivel`, en "¿hay gasto público?", o en las dos. El juez quedó
descartado como medición (su sesgo es de una sola dirección y está en el prompt),
pero es estable: 95% de coincidencia entre `qwen2.5:7b` y `qwen2.5:14b`. Un
instrumento sesgado pero estable sirve para **señalar dónde mirar**, que es lo
único que se le pide acá.

**No agrega ninguna columna**: sólo ordena. La instrucción que recibe quien
etiqueta no puede decirle cuál es la respuesta, ni siquiera indirectamente.

Qué mide cada bloque, porque no es lo mismo:

- las **dudosas** primero: si el clasificador se sostiene ahí, eso es un **piso**
  (los casos más difíciles), no un promedio de la población;
- el **resto** después: ésas son las que se parecen al corpus.

Uso:
    python scripts/priorizar_muestra.py
    python scripts/etiquetar_gasto.py --muestra .tmp-muestra-gasto/gasto_muestra_priorizada.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from etiquetas_gasto import escribir_csv, leer_csv  # noqa: E402

BASE = Path(__file__).parent.parent / ".tmp-muestra-gasto"


def _recalcular_predicciones(filas: list[dict], destino: Path) -> dict[str, dict]:
    """Predicciones del clasificador **de hoy** para las filas de la muestra.

    El clasificador es justamente lo que se está midiendo, así que este archivo no
    puede quedar viejo: si no se recalcula, el medidor compara etiquetas hechas
    contra las predicciones de la versión anterior.

    La `section` del boletín es un **insumo** de la clasificación —no una
    predicción— y se conserva del archivo anterior, porque el CSV de la muestra no
    la lleva a propósito: sólo lleva lo que quien etiqueta necesita leer.
    """
    from app.services.gasto_classifier import classify_gasto

    previas = json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else {}
    nuevas: dict[str, dict] = {}
    for fila in filas:
        mid = fila["muestra_id"]
        section = (previas.get(mid) or {}).get("section")
        c = classify_gasto(
            {
                "tipo_acto": fila.get("tipo_acto"),
                "descripcion": fila.get("descripcion"),
                "fragmento": fila.get("fragmento"),
                "organismo": fila.get("organismo"),
            },
            section=section,
        )
        nuevas[mid] = {
            "nivel": c.nivel,
            "tipo_gasto": c.tipo_gasto,
            "objeto": c.objeto,
            "motivo": c.tipo_gasto_motivo,
            "es_gasto_publico": c.is_gasto_publico,
            "section": section,
            "largo_fragmento": len(fila.get("fragmento") or ""),
        }
    destino.write_text(json.dumps(nuevas, ensure_ascii=False, indent=1), encoding="utf-8")
    return nuevas


def _cargar_jsonl(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {
        json.loads(line)["muestra_id"]: json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def run(muestra: Path, out: Path) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    filas = leer_csv(muestra)
    preds = _recalcular_predicciones(filas, out / "gasto_muestra_predicciones.json")

    # El 14b donde exista (mejor modelo), si no el 7b.
    juez = _cargar_jsonl(out / "gasto_juez_llm.jsonl")
    juez.update(_cargar_jsonl(out / "juez14b" / "gasto_juez_llm.jsonl"))

    dudosas, resto = [], []
    por_nivel = por_gasto = 0
    for i, fila in enumerate(filas):
        mid = fila["muestra_id"]
        j, p = juez.get(mid), preds.get(mid)
        if not j or not p:
            resto.append((i, fila))
            continue
        d_nivel = j["nivel"] != p["nivel"]
        d_gasto = j["hay_gasto_publico"] != (p["tipo_gasto"] != "no_es_gasto")
        if d_nivel or d_gasto:
            por_nivel += d_nivel
            por_gasto += d_gasto
            # Las que fallan en los dos ejes van primero.
            dudosas.append((0 if (d_nivel and d_gasto) else 1, i, fila))
        else:
            resto.append((i, fila))

    dudosas.sort(key=lambda t: (t[0], t[1]))
    ordenadas = [f for _, _, f in dudosas] + [f for _, f in resto]

    destino = out / "gasto_muestra_priorizada.csv"
    # Regenerar el orden no puede borrar trabajo: si ya se etiquetó sobre el
    # archivo priorizado, esas etiquetas ganan sobre lo que traiga la muestra
    # original (que puede estar sin tocar).
    rescatadas = 0
    if destino.exists():
        previas = {f["muestra_id"]: f for f in leer_csv(destino)}
        for fila in ordenadas:
            previa = previas.get(fila["muestra_id"]) or {}
            if any(
                (previa.get(c) or "").strip()
                for c in ("nivel_real", "tipo_gasto_real", "objeto_real", "nota")
            ):
                # Todas las columnas de etiqueta, no sólo las dos primeras: la vez
                # que me olvidé de `objeto_real` acá se perdieron 87 etiquetas.
                for col in ("nivel_real", "tipo_gasto_real", "objeto_real", "nota"):
                    fila[col] = previa.get(col, "")
                rescatadas += 1
    escribir_csv(destino, ordenadas)

    etiquetadas = sum(
        1 for f in ordenadas if (f.get("nivel_real") or "").strip() or (f.get("tipo_gasto_real") or "").strip()
    )
    print(f"muestra: {len(filas)} actos · dudosas primero: {len(dudosas)}")
    print(f"  discrepan en nivel: {por_nivel} · en ¿hay gasto?: {por_gasto}")
    print("  (una fila puede discrepar en los dos ejes)")
    print(f"  ya etiquetadas: {etiquetadas}" + (f" · rescatadas del priorizado anterior: {rescatadas}" if rescatadas else ""))
    print(f"\nescrito: {destino}")
    rel = destino.relative_to(Path(__file__).parent.parent)
    print("\nPara etiquetar, y después medir:")
    print(f"   .\\.venv\\Scripts\\python.exe scripts/etiquetar_gasto.py --muestra {rel}")
    print(f"   .\\.venv\\Scripts\\python.exe scripts/medir_clasificacion_gasto.py --muestra {rel}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--muestra", type=Path, default=BASE / "gasto_muestra_etiquetado.csv")
    parser.add_argument("--out", type=Path, default=BASE)
    args = parser.parse_args()
    run(args.muestra, args.out)


if __name__ == "__main__":
    main()

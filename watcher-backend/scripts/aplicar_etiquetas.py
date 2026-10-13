#!/usr/bin/env python3
"""
Aplicar etiquetas en bloque sobre la muestra de M8.

El asistente (`etiquetar_gasto.py`) es para etiquetar de a una fila, leyendo. Este
es para cargar etiquetas ya decididas en otro lado: una revisión en lote, una
corrección, o una etiqueta que hizo otro instrumento.

El JSON es `{muestra_id: {nivel, tipo_gasto, objeto, nota}}`; las claves faltantes
y las filas que no aparecen quedan como estaban. Se valida el vocabulario: una
etiqueta que no existe corta la corrida en vez de contarse como error después.

Uso:
    python scripts/aplicar_etiquetas.py --json .tmp-muestra-gasto/etiquetas.json
    python scripts/aplicar_etiquetas.py --json etiquetas.json --muestra .tmp-muestra-gasto/gasto_muestra_priorizada.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from etiquetas_gasto import (  # noqa: E402
    NIVELES,
    OBJETOS,
    TIPOS_GASTO,
    escribir_csv,
    leer_csv,
    norm_label,
)

BASE = Path(__file__).parent.parent / ".tmp-muestra-gasto"

CAMPOS = (
    ("nivel", "nivel_real", set(NIVELES)),
    ("tipo_gasto", "tipo_gasto_real", set(TIPOS_GASTO)),
    ("objeto", "objeto_real", set(OBJETOS)),
)


def run(muestra: Path, json_path: Path) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    etiquetas = json.loads(json_path.read_text(encoding="utf-8"))
    filas = leer_csv(muestra)
    por_id = {f["muestra_id"]: f for f in filas}

    invalidos = []
    for mid, campos in etiquetas.items():
        for clave, _col, validos in CAMPOS:
            valor = norm_label(campos.get(clave), clave)
            if valor and valor not in validos:
                invalidos.append((mid, clave, campos.get(clave), sorted(validos)))
    if invalidos:
        raise SystemExit(
            "❌ etiquetas fuera del vocabulario:\n"
            + "\n".join(f"   {mid} · {clave}: {valor!r} (válidos: {', '.join(v)})" for mid, clave, valor, v in invalidos[:15])
        )

    aplicadas, desconocidas = 0, []
    for mid, campos in etiquetas.items():
        fila = por_id.get(mid)
        if fila is None:
            desconocidas.append(mid)
            continue
        for clave, col, _validos in CAMPOS:
            valor = norm_label(campos.get(clave), clave)
            if valor:
                fila[col] = valor
        if campos.get("nota") is not None:
            fila["nota"] = str(campos["nota"]).strip()
        aplicadas += 1

    escribir_csv(muestra, filas)
    etiquetadas = sum(
        1 for f in filas
        if (f.get("nivel_real") or "").strip() or (f.get("tipo_gasto_real") or "").strip()
    )
    print(f"etiquetas aplicadas: {aplicadas} de {len(etiquetas)}")
    if desconocidas:
        print(f"  ⚠️  muestra_id que no están en la muestra ({len(desconocidas)}): {', '.join(desconocidas[:6])}…")
    print(f"muestra: {etiquetadas}/{len(filas)} etiquetadas → {muestra}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, required=True, help="Etiquetas {muestra_id: {nivel, tipo_gasto, objeto, nota}}")
    parser.add_argument("--muestra", type=Path, default=BASE / "gasto_muestra_priorizada.csv")
    args = parser.parse_args()
    run(args.muestra, args.json)


if __name__ == "__main__":
    main()

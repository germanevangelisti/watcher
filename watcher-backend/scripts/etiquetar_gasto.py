#!/usr/bin/env python3
"""
Asistente para etiquetar a mano la muestra de M8 (historia `pm-gasto-deteccion-ampliada`).

Muestra un acto por vez, pide las dos etiquetas y **guarda después de cada uno**,
así que se puede cortar cuando quieras y seguir después: al volver a correrlo
arranca en la primera fila sin etiquetar.

**No lee el archivo de predicciones.** Ese es el punto del ejercicio: la etiqueta
tiene que ser tu juicio sobre el acto, no una corrección de lo que dijo el
clasificador. Si querés ver la predicción, mirá
`gasto_muestra_predicciones.json` — pero entonces la medición deja de servir.

Atajos en cada pregunta:
    1..9 (o el nombre)   responder
    s                    saltear este acto (queda sin etiquetar)
    q                    guardar y salir
    ?                    ver las opciones de nuevo

Uso:
    python scripts/etiquetar_gasto.py
    python scripts/etiquetar_gasto.py --muestra .tmp-muestra-gasto/gasto_muestra_etiquetado.csv
"""

from __future__ import annotations

import argparse
import sys
import textwrap
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

SALIR = "__salir__"
SALTEAR = "__saltear__"


def _ars(valor) -> str:
    try:
        n = float(valor)
    except (TypeError, ValueError):
        return "-"
    return "$ " + f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _mostrar(fila: dict, i: int, total: int, pendientes: int) -> None:
    print("\n" + "─" * 78)
    print(f" [{i}/{total}]  faltan {pendientes}")
    print(f" Fecha:       {fila.get('fecha') or '-'}")
    print(f" Organismo:   {fila.get('organismo') or '-'}")
    print(f" Tipo de acto: {fila.get('tipo_acto') or '-'}   Monto: {_ars(fila.get('monto'))}")
    desc = (fila.get("descripcion") or "").strip()
    if desc:
        print(" Descripción: " + textwrap.fill(desc, 78, subsequent_indent=" " * 14))
    frag = (fila.get("fragmento") or "").strip()
    if frag and frag != desc:
        print(" Fragmento:   " + textwrap.fill(frag[:400], 78, subsequent_indent=" " * 14))
    print("─" * 78)


def _opciones(titulo: str, valores: tuple[str, ...]) -> None:
    print(f" {titulo}:")
    for n, v in enumerate(valores, 1):
        print(f"     {n} = {v}")
    print()


def _preguntar(titulo: str, valores: tuple[str, ...], letra: str, campo: str) -> str:
    """Devuelve el valor canónico, o SALIR / SALTEAR."""
    _opciones(titulo, valores)
    while True:
        try:
            crudo = input(f" {letra}> ").strip()
        except EOFError:
            # stdin cerrado (o corrida sin terminal): no perder lo hecho.
            return SALIR

        if crudo == "?":
            _opciones(titulo, valores)
            continue
        if crudo.lower() in ("q", "salir"):
            return SALIR
        if crudo.lower() in ("s", "saltear"):
            return SALTEAR
        if crudo.isdigit() and 1 <= int(crudo) <= len(valores):
            return valores[int(crudo) - 1]

        valor = norm_label(crudo, campo)
        if valor in valores:
            return valor
        print(f"   ✗ {crudo!r} no es una opción. Número, nombre, s para saltear, q para salir, ? para verlas.")


def run(muestra: Path) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if not muestra.exists():
        raise SystemExit(f"❌ no existe {muestra} — corré scripts/muestra_etiquetado_gasto.py")
    if "predicciones" in muestra.name:
        raise SystemExit("❌ ese es el archivo de predicciones. La muestra a etiquetar es gasto_muestra_etiquetado.csv")

    filas = leer_csv(muestra)
    total = len(filas)
    pendientes = [
        i for i, f in enumerate(filas)
        if not (norm_label(f.get("nivel_real"), "nivel") and norm_label(f.get("tipo_gasto_real")))
    ]

    print(f"\nMuestra: {muestra}")
    print(f"{total} actos · ya etiquetados {total - len(pendientes)} · por etiquetar {len(pendientes)}")
    print("En cada acto: número o nombre · s saltear · q guardar y salir · ? opciones")
    print("Cada respuesta se guarda al instante; podés cortar con Ctrl+C y seguir después.")

    hechos = 0
    try:
        for n, i in enumerate(pendientes, 1):
            fila = filas[i]
            _mostrar(fila, i + 1, total, len(pendientes) - n + 1)

            nivel = _preguntar("nivel_real", NIVELES, "nivel", "nivel")
            if nivel == SALIR:
                break
            if nivel == SALTEAR:
                print("   (salteado)")
                continue

            tipo = _preguntar("tipo_gasto_real", TIPOS_GASTO, "tipo", "tipo_gasto")
            if tipo == SALIR:
                break
            if tipo == SALTEAR:
                print("   (salteado)")
                continue

            objeto = _preguntar("objeto_real", OBJETOS, "objeto", "objeto")
            if objeto == SALIR:
                break
            if objeto == SALTEAR:
                objeto = ""

            try:
                nota = input(" nota (opcional, Enter para seguir)> ").strip()
            except EOFError:
                nota = ""

            fila["nivel_real"] = nivel
            fila["tipo_gasto_real"] = tipo
            fila["objeto_real"] = objeto
            fila["nota"] = nota
            escribir_csv(muestra, filas)  # se guarda acto por acto
            hechos += 1
    except KeyboardInterrupt:
        print("\n\nInterrumpido — guardando lo que había.")
    finally:
        escribir_csv(muestra, filas)

    etiquetados = sum(
        1 for f in filas if norm_label(f.get("nivel_real"), "nivel") and norm_label(f.get("tipo_gasto_real"))
    )
    print(f"\nEtiquetaste {hechos} en esta corrida · quedan {total - etiquetados} de {total}")
    if total - etiquetados == 0:
        print("\nListo. Para medir:")
    else:
        print("\nPodés volver a correrlo para seguir donde quedaste. Para medir lo que hay:")
    print("   .\\.venv\\Scripts\\python.exe scripts/medir_clasificacion_gasto.py")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--muestra", type=Path, default=BASE / "gasto_muestra_etiquetado.csv")
    args = parser.parse_args()
    run(args.muestra)


if __name__ == "__main__":
    main()

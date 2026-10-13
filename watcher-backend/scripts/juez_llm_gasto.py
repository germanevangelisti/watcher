#!/usr/bin/env python3
"""
Juez LLM local sobre la muestra de M8 — para ver dónde las reglas y un modelo
discrepan, **antes** de decidir con qué se mide la precisión.

Diseño, y por qué es así:

- **No le enseña la taxonomía.** Al modelo se le pregunta *qué es el acto, en
  términos llanos*, y nada más. Si se le explicaran las categorías
  (`obra_publica`, `subsidio_transferencia`…) estaríamos midiendo las reglas del
  clasificador contra un prompt que las repite, y la concordancia saldría alta
  por construcción.
- Por eso la comparación mecánica se hace sólo sobre los dos ejes que no
  necesitan nuestro vocabulario: **nivel** (provincial/municipal/comunal, que es
  un hecho, no una categoría nuestra) y **¿hay gasto público?** (contra
  `tipo_gasto == no_es_gasto`). El eje `tipo_gasto` no se puntúa: se deja la frase
  del modelo al lado de lo que dijeron las reglas, para leerlo.
- **Corre local, siempre.** Usa `build_provider("ollama", …)`, que levanta si no
  se puede, en vez de `resolve_llm_provider()` (que respeta `LLM_PROVIDER` y
  podría mandar texto de boletines a la nube sin que nadie lo note).
- **El modelo nunca ve la predicción.** El JSON de predicciones se lee recién en
  el paso de comparación, para restar; nunca entra al prompt.
- Reanudable: cada respuesta se appendea a un JSONL; volver a correrlo saltea lo
  ya hecho.

Uso:
    python scripts/juez_llm_gasto.py --limite 5     # prueba chica
    python scripts/juez_llm_gasto.py                # los 150
    python scripts/juez_llm_gasto.py --report       # sólo comparar lo ya juzgado
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from etiquetas_gasto import leer_csv, norm_label  # noqa: E402

BASE = Path(__file__).parent.parent / ".tmp-muestra-gasto"
CACHE = "gasto_juez_llm.jsonl"

#: Prompt mínimo a propósito: describe la tarea en castellano llano y no nombra
#: ninguna categoría del clasificador.
#:
#: El orden de las claves es el arreglo, no la estética: el modelo genera en
#: orden, así que `frase_del_gasto` sale **antes** que el veredicto y
#: `hay_gasto_publico` queda encadenado a la cita. El prompt anterior preguntaba
#: el booleano primero y el modelo anclaba en el `monto` del acto: 11 de 11
#: desacuerdos con las reglas iban en la dirección de "sí gasta", igual con 7b
#: que con 14b.
JUEZ_PROMPT = """Leé este acto publicado en el Boletín Oficial de la Provincia de Córdoba (Argentina).

Contestá SÓLO un objeto JSON, con las claves EN ESTE ORDEN:

{{
  "frase_del_gasto": "copiá TEXTUALMENTE, del acto, la frase que muestra que se dispone de dinero público (una compra, una contratación, una obra, un subsidio, una transferencia). Si el acto no tiene una frase así, poné cadena vacía.",
  "hay_gasto_publico": "true o false. Va true SÓLO si pegaste una frase arriba; si frase_del_gasto quedó vacía, acá va false.",
  "objeto": "qué se compra o se hace, con las palabras del acto (por ejemplo 'resmas de papel A4', 'pavimento de la calle Carrega Núñez', 'servicio de vigilancia'). Si el acto no lo dice, cadena vacía. No lo interpretes ni lo resumas: copiá.",
  "nivel": "uno de: provincial | municipal | comunal | desconocido. A qué nivel de gobierno pertenece el acto según quién lo emite, de acuerdo a lo que el propio acto diga. Si el acto no lo dice, poné desconocido."
}}

Que el texto tenga un monto NO prueba que se disponga de dinero: un expediente judicial puede citar una deuda, una sociedad puede informar su capital, y un decreto puede mover partidas sin pagarle a nadie. Para eso está `frase_del_gasto`.

Acto:
- Fecha: {fecha}
- Organismo: {organismo}
- Monto: {monto}
- Texto: {texto}
"""

NIVELES_JUEZ = ("provincial", "municipal", "comunal", "desconocido")


def _texto_del_acto(fila: dict) -> str:
    partes = [fila.get("descripcion"), fila.get("fragmento")]
    return " ".join(str(p).strip() for p in partes if str(p or "").strip())[:2000]


async def _juzgar(provider, fila: dict, timeout_s: float) -> dict | None:
    prompt = JUEZ_PROMPT.format(
        fecha=fila.get("fecha") or "-",
        organismo=fila.get("organismo") or "-",
        monto=fila.get("monto") or "-",
        texto=_texto_del_acto(fila) or "(sin texto)",
    )
    for intento in (1, 2):
        try:
            raw = await asyncio.wait_for(
                provider.generate_text(prompt, temperature=0.0, max_tokens=400),
                timeout=timeout_s,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"   ! el modelo falló ({exc}); intento {intento}/2")
            continue
        m = re.search(r"\{.*\}", raw or "", flags=re.S)
        if not m:
            continue
        try:
            data = json.loads(m.group(0))
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("nivel"):
            nivel = norm_label(str(data.get("nivel")), "nivel")
            if nivel not in NIVELES_JUEZ:
                nivel = "desconocido"
            frase = str(data.get("frase_del_gasto") or "").strip()
            dicho = bool(data.get("hay_gasto_publico"))
            return {
                "frase_del_gasto": frase,
                "objeto": str(data.get("objeto") or "").strip(),
                "nivel": nivel,
                # La coherencia se fuerza acá además de pedirla en el prompt: un
                # `true` sin cita se contradice con su propia evidencia y no
                # puede entrar a la comparación como si valiera.
                "hay_gasto_publico": dicho and bool(frase),
                "incoherente": dicho and not frase,
            }
    return None


async def juzgar(muestra: Path, salida: Path, modelo: str, limite: int | None, timeout_s: float) -> None:
    filas = leer_csv(muestra)
    if limite:
        filas = filas[:limite]

    archivo = salida / CACHE
    salida.mkdir(parents=True, exist_ok=True)
    hechos: dict[str, dict] = {}
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if linea.strip():
                d = json.loads(linea)
                hechos[d["muestra_id"]] = d

    pendientes = [f for f in filas if f["muestra_id"] not in hechos]
    print(f"actos: {len(filas)} · ya juzgados: {len(hechos)} · por juzgar: {len(pendientes)}")
    if not pendientes:
        return

    from app.services.llm_provider import build_provider

    provider = build_provider("ollama", model=modelo)
    print(f"modelo: {modelo} (Ollama local — el texto no sale de la máquina)")
    print("Esto tarda: son ~5-15 s por acto.\n")

    fallos = 0
    with archivo.open("a", encoding="utf-8") as fh:
        for i, fila in enumerate(pendientes, 1):
            veredicto = await _juzgar(provider, fila, timeout_s)
            if veredicto is None:
                fallos += 1
                print(f" [{i}/{len(pendientes)}] {fila['muestra_id']} · sin respuesta utilizable")
                continue
            registro = {"muestra_id": fila["muestra_id"], "organismo": fila.get("organismo"), **veredicto}
            fh.write(json.dumps(registro, ensure_ascii=False) + "\n")
            fh.flush()
            print(
                f" [{i}/{len(pendientes)}] {veredicto['nivel']:12s} "
                f"{'gasto' if veredicto['hay_gasto_publico'] else 'no-gasto':9s} "
                f"{'cita' if veredicto['frase_del_gasto'] else 'sin cita':9s} · {veredicto['objeto'][:52]}"
            )

    print(f"\nlisto · fallos sin respuesta: {fallos}")
    print(f"cache: {archivo}")


def _wilson(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    centro = p + z * z / (2 * n)
    margen = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (centro - margen) / (1 + z * z / n)


def reporte(salida: Path, pred_path: Path) -> None:
    archivo = salida / CACHE
    if not archivo.exists():
        raise SystemExit("❌ todavía no hay juicios — corré el script sin --report")
    juez = {json.loads(line)["muestra_id"]: json.loads(line) for line in archivo.read_text(encoding="utf-8").splitlines() if line.strip()}
    preds = json.loads(Path(pred_path).read_text(encoding="utf-8"))

    pares = [
        (mid, j, preds[mid])
        for mid, j in juez.items()
        if mid in preds
    ]
    n = len(pares)
    print(f"actos juzgados y comparables: {n}\n")

    # Eje nivel: hecho, no categoría nuestra.
    ok_nivel = sum(1 for _, j, p in pares if j["nivel"] == p["nivel"])
    print(f"nivel:        coinciden {ok_nivel}/{n} = {ok_nivel / n:.1%}  ·  Wilson 95% ≥ {_wilson(ok_nivel, n):.1%}")

    # Eje "hay gasto público" contra la única categoría de las reglas que no exige
    # nuestro vocabulario.
    ok_gasto = sum(1 for _, j, p in pares if j["hay_gasto_publico"] == (p["tipo_gasto"] != "no_es_gasto"))
    print(f"hay gasto:    coinciden {ok_gasto}/{n} = {ok_gasto / n:.1%}  ·  Wilson 95% ≥ {_wilson(ok_gasto, n):.1%}")

    # Un `true` sin cita es una respuesta que se contradice con su propia
    # evidencia: si aparece seguido, el prompt no se está siguiendo y el número
    # de arriba no mide lo que dice medir.
    incoh = sum(1 for _, j, _ in pares if j.get("incoherente"))
    con = sum(1 for _, j, _ in pares if j["frase_del_gasto"])
    print(f"cita textual: {con}/{n} actos · respuestas incoherentes (dijo gasto y no citó): {incoh}")

    print("\ndiscrepancias en nivel:")
    for mid, j, p in pares:
        if j["nivel"] != p["nivel"]:
            print(f"  {mid} | reglas: {p['nivel']:12s} juez: {j['nivel']:12s} | {(p.get('organismo') or '')[:34]:34s} | {j['objeto'][:56]}")

    print("\ndiscrepancias en ¿hay gasto?:")
    for mid, j, p in pares:
        if j["hay_gasto_publico"] != (p["tipo_gasto"] != "no_es_gasto"):
            print(f"  {mid} | reglas: {p['tipo_gasto']:22s} juez: {'gasto' if j['hay_gasto_publico'] else 'no-gasto'} | cita: {j['frase_del_gasto'][:60] or '(ninguna)'}")

    # Eje tipo: sin puntaje, al lado para leer. Es donde la taxonomía es nuestra y
    # puntuar exigiría mapear la frase con las mismas reglas que se están midiendo.
    md = salida / "gasto_juez_vs_reglas.md"
    with md.open("w", encoding="utf-8") as fh:
        fh.write("# Juez LLM vs reglas — M8\n\n")
        fh.write("El eje `tipo_gasto` **no se puntúa**: la frase del juez se lee al lado de lo que\n")
        fh.write("dijeron las reglas. Puntuar exigiría mapear la frase con las mismas reglas que se\n")
        fh.write("están midiendo, y eso mide mi prompt contra sí mismo.\n\n")
        fh.write("| muestra_id | organismo | reglas: tipo | juez: nivel | juez: ¿gasto? | objeto que copió del acto | frase que citó |\n")
        fh.write("| --- | --- | --- | --- | --- | --- | --- |\n")
        for mid, j, p in pares:
            fh.write(
                f"| {mid} | {(p.get('organismo') or '')[:40]} | {p['tipo_gasto']} | {j['nivel']} "
                f"| {'sí' if j['hay_gasto_publico'] else 'no'} | {j['objeto'][:90]} | {j['frase_del_gasto'][:110] or '(ninguna)'} |\n"
            )
    print(f"\ntabla al lado (para leer el eje tipo): {md}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--muestra", type=Path, default=BASE / "gasto_muestra_etiquetado.csv")
    parser.add_argument("--predicciones", type=Path, default=BASE / "gasto_muestra_predicciones.json")
    parser.add_argument("--out", type=Path, default=BASE)
    parser.add_argument("--modelo", default=None, help="default: OLLAMA_MODEL del .env")
    parser.add_argument("--limite", type=int, default=None, help="juzgar sólo los primeros N")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--report", action="store_true", help="sólo comparar lo ya juzgado")
    args = parser.parse_args()

    if args.report:
        reporte(args.out, args.predicciones)
        return

    modelo = args.modelo
    if not modelo:
        from app.core.config import settings

        modelo = settings.OLLAMA_MODEL

    asyncio.run(juzgar(args.muestra, args.out, modelo, args.limite, args.timeout))
    print()
    reporte(args.out, args.predicciones)


if __name__ == "__main__":
    main()

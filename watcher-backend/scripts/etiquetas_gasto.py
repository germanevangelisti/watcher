"""Vocabulario y entrada/salida del CSV de etiquetado de M8.

Compartido por `etiquetar_gasto.py` (el asistente) y `medir_clasificacion_gasto.py`
(el medidor), para que una etiqueta que el asistente acepta no pueda ser rechazada
después por el medidor.

No conoce las predicciones: sólo el vocabulario y el formato del archivo.
"""

from __future__ import annotations

import csv
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.gasto_classifier import NIVELES, OBJETOS, TIPOS_GASTO

__all__ = [
    "COLUMNAS",
    "NIVELES",
    "OBJETOS",
    "TIPOS_GASTO",
    "escribir_csv",
    "leer_csv",
    "norm_label",
]

COLUMNAS = [
    "muestra_id", "fecha", "organismo", "tipo_acto", "descripcion", "fragmento",
    "monto", "nivel_real", "tipo_gasto_real", "objeto_real", "nota",
]

#: Cómo se escribe cada etiqueta a mano, contra el vocabulario del clasificador.
#: Sin esto, "Concurso de precios" o "Subsidio / transferencia" —que es como
#: cualquiera las escribiría— contarían como error de clasificación.
#:
#: **Por campo, no uno solo**: hay palabras que son sinónimo en un eje y valor
#: legítimo en otro.  `no_aplica` es cómo se escribe el nivel `desconocido` y
#: también es un objeto válido; `subsidio` es `subsidio_transferencia` como figura
#: y `transferencia` como objeto.  Un mapa único traducía al eje equivocado (y en
#: Python, con claves repetidas, la última pisaba a la primera en silencio).
ALIAS_NIVEL = {
    "provincia": "provincial",
    "municipio": "municipal",
    "muni": "municipal",
    "capital": "municipal",
    "comuna": "comunal",
    "sin_nivel": "desconocido",
    "no_aplica": "desconocido",
    "n_a": "desconocido",
    "na": "desconocido",
}

ALIAS_TIPO = {
    "licitaciones": "licitacion",
    "concurso_de_precios": "concurso_precios",
    "concurso": "concurso_precios",
    "compulsa": "concurso_precios",
    "compulsa_abreviada": "concurso_precios",
    "subasta": "subasta_electronica",
    "compra": "compra_directa",
    "contratacion_directa": "contratacion",
    "contrato": "contratacion",
    "convenio": "contratacion",
    "subsidio": "subsidio_transferencia",
    "transferencia": "subsidio_transferencia",
    "otros": "otro",
    "no_gasto": "no_es_gasto",
    "no_es": "no_es_gasto",
}

ALIAS_OBJETO = {
    "bienes": "bien",
    "insumos": "bien",
    "obras": "obra",
    "servicios": "servicio",
    "subsidio": "transferencia",
    "transferencias": "transferencia",
}

_ALIAS_POR_CAMPO = {"nivel": ALIAS_NIVEL, "tipo_gasto": ALIAS_TIPO, "objeto": ALIAS_OBJETO}


def norm_label(valor: str | None, campo: str | None = None) -> str:
    """Normalize a hand-written label onto the classifier's vocabulary.

    `Provincial`, `PROVINCIAL`, `provincial ` and `Subsidio / Transferencia` all
    land on the same value.  `campo` (`"nivel"`, `"tipo_gasto"` o `"objeto"`)
    elige el mapa de sinónimos; sin él se prueban los tres, así que conviene
    pasarlo siempre que se sepa de qué eje se trata.

    A label that is still unknown afterwards stays unknown on purpose: a typo
    (`obrapublica`) has to fail loudly rather than be silently forgiven, because
    it would be counted as a miss.
    """
    if not valor:
        return ""
    s = unicodedata.normalize("NFKD", str(valor).strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    if campo is not None:
        return _ALIAS_POR_CAMPO.get(campo, {}).get(s, s)
    for mapa in (ALIAS_NIVEL, ALIAS_TIPO, ALIAS_OBJETO):
        if s in mapa:
            return mapa[s]
    return s


def leer_csv(path: Path) -> list[dict]:
    """Read the labelling CSV as Excel on a Spanish Windows writes it.

    Excel re-saves with the locale's list separator (`;`) and often in cp1252,
    which would break a plain `csv.DictReader` on the UTF-8 comma file we
    exported.  The delimiter is decided from the header line only, so a comma
    inside a label cannot flip it.
    """
    raw = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit(f"❌ no pude decodificar {path} (¿otra codificación?)")

    lineas = text.splitlines()
    header = lineas[0] if lineas else ""
    delim = ";" if header.count(";") > header.count(",") else ","
    filas = [dict(r) for r in csv.DictReader(lineas, delimiter=delim)]
    for f in filas:
        for col in COLUMNAS:
            f.setdefault(col, "")
            if f[col] is None:
                f[col] = ""
    return filas


def escribir_csv(path: Path, filas: list[dict]) -> None:
    """Rewrite the CSV in the canonical shape (UTF-8, coma, mismas columnas)."""
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNAS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(filas)

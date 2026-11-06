"""Catálogo de municipios y comunas de Córdoba (WMA1).

El listado de gasto guarda `analisis.municipio` tal como lo nombra el acto
("Rio Ceballos", "Río Ceballos", "La Ciudad De Río Ceballos" son la misma
jurisdicción).  El mapa necesita una clave estable y la lista **completa** de
gobiernos locales —incluidas las que no tienen ningún acto, que se pintan en
gris—, así que este módulo resuelve el nombre crudo contra el catálogo y expone
la población del Censo 2022 para el gasto per cápita.

El catálogo se genera con `scripts/build_municipios_cordoba.py` (fuente y fecha
en `app/data/FUENTES-municipios.md`); acá sólo se lee.  Nada de red en runtime.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

_RUTA = Path(__file__).resolve().parent.parent / "data" / "municipios_cordoba.json"

# Formas que no se resuelven normalizando: erratas de la fuente.
_ALIASES = {
    "carrillobo": "carrilobo",
}

# "Municipalidad de X", "Municipio de X", "La Ciudad de X" no son parte del nombre.
_PREFIJOS = re.compile(r"^(municipio|municipalidad|comuna|la ciudad de|ciudad de)\s+(de\s+)?")


def normalizar(nombre: str | None) -> str:
    """Minúsculas, sin acentos ni puntuación, sin el prefijo institucional."""
    sin_acentos = (
        unicodedata.normalize("NFKD", nombre or "").encode("ascii", "ignore").decode().lower()
    )
    return re.sub(r"[^a-z0-9]+", " ", _PREFIJOS.sub("", sin_acentos.strip())).strip()


@lru_cache(maxsize=1)
def catalogo() -> tuple[dict, ...]:
    return tuple(json.loads(_RUTA.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def _por_nombre() -> dict[str, dict]:
    indice: dict[str, dict] = {}
    for entrada in catalogo():
        indice.setdefault(normalizar(entrada["nombre"]), entrada)
    return indice


@lru_cache(maxsize=1)
def _por_codigo() -> dict[str, dict]:
    return {entrada["codigo"]: entrada for entrada in catalogo()}


def por_codigo(codigo: str | None) -> dict | None:
    return _por_codigo().get(codigo or "")


def _tokens(nombre: str) -> set[str]:
    return set(normalizar(nombre).split())


def resolver(nombre: str | None) -> dict | None:
    """Nombre crudo del acto → entrada del catálogo, o `None` si no hay certeza.

    Un nombre ambiguo (p. ej. "Los Chañaritos", que existe dos veces) devuelve
    `None`: mejor declarar el gasto como no asignado que ponerlo en el municipio
    equivocado.
    """
    clave = normalizar(nombre)
    if not clave:
        return None
    clave = _ALIASES.get(clave, clave)
    exacto = _por_nombre().get(clave)
    if exacto:
        return exacto
    # "Zorros" por "Los Zorros": el nombre corto es subconjunto del canónico.
    candidatos = [
        entrada
        for clave_catalogo, entrada in _por_nombre().items()
        if clave in clave_catalogo.split() or set(clave_catalogo.split()) <= set(clave.split())
    ]
    return candidatos[0] if len(candidatos) == 1 else None


def nivel_de(entrada: dict) -> str:
    """Nivel de gobierno que le corresponde por su tipo de gobierno local."""
    return "municipal" if entrada.get("tipo") == "municipio" else "comunal"

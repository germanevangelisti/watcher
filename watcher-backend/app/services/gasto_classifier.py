"""Rules-based classification of an acto as public spending (P.7.1).

The raw sum of `analisis.monto_numerico` is not public spending: it mixes tender
calls, re-publications, judicial auctions, corporate filings and budget line
transfers.  This module decides, per acto, whether it belongs in the spending
ledger at all, at which stage of the spending cycle it sits, and against which
jurisdiction's budget it should be counted.

Rules only — no LLM call.  Signals used: `tipo_acto`, the boletín section, and
keywords over the acto text.

Two distinctions drive everything downstream:

- A tender call (`llamado`) is a *commitment*, not a payment.  A transfer or
  subsidy (`pago`) is *execution*.  The UI must never add them into one bar.
- A budget line transfer (`modificacion`) moves the ceiling without spending
  anything, so it is not spending even though it carries a large monto.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# ── Etapas del ciclo de gasto ──────────────────────────────────────────────────

ETAPA_LLAMADO = "llamado"
ETAPA_ADJUDICACION = "adjudicacion"
ETAPA_CONTRATO = "contrato"
ETAPA_PAGO = "pago"
ETAPA_MODIFICACION = "modificacion"
ETAPA_NO_APLICA = "no_aplica"

ETAPAS_GASTO = (
    ETAPA_LLAMADO,
    ETAPA_ADJUDICACION,
    ETAPA_CONTRATO,
    ETAPA_PAGO,
    ETAPA_MODIFICACION,
    ETAPA_NO_APLICA,
)

# Etapas that commit budget without disbursing it
ETAPAS_COMPROMISO = (ETAPA_LLAMADO, ETAPA_ADJUDICACION, ETAPA_CONTRATO)
# Etapas that actually disburse
ETAPAS_EJECUCION = (ETAPA_PAGO,)

# ── Jurisdicciones ─────────────────────────────────────────────────────────────

JURISDICCION_PROVINCIAL = "provincial"
JURISDICCION_MUNICIPAL = "municipal"
JURISDICCION_FUERA = "fuera_presupuesto"

JURISDICCIONES = (JURISDICCION_PROVINCIAL, JURISDICCION_MUNICIPAL, JURISDICCION_FUERA)

# ── Tipos de gasto (figura / objeto, M8) ───────────────────────────────────────
#
# A second axis, independent of `etapa_gasto`: the stage of the spending cycle is
# *when*, this is *what*.  An awarded tender reads "licitacion · adjudicacion" —
# the figure and the moment, in two fields, rather than one value that has to
# choose between them.

TIPO_LICITACION = "licitacion"
TIPO_CONCURSO_PRECIOS = "concurso_precios"
# La subasta electrónica es una figura propia de la Ley 10.155, no un concurso de
# precios: el portal de compras la declara como su propio tipo de proceso, y
# meterla adentro de `concurso_precios` producía un desacuerdo falso con quien
# etiqueta (el acto dice SUBASTA ELECTRÓNICA y ninguna de las dos lecturas
# anteriores era la suya).
TIPO_SUBASTA_ELECTRONICA = "subasta_electronica"
TIPO_COMPRA_DIRECTA = "compra_directa"
TIPO_CONTRATACION = "contratacion"
TIPO_OBRA_PUBLICA = "obra_publica"
TIPO_SERVICIO = "servicio"
TIPO_SUBSIDIO_TRANSFERENCIA = "subsidio_transferencia"
TIPO_OTRO = "otro"
# Not a classification failure: the correct answer for a judicial edicto or a
# corporate filing that carries a monto.  Kept out of the citizen's listing by
# ``is_gasto_publico``, not by being discarded.
TIPO_NO_ES_GASTO = "no_es_gasto"

TIPOS_GASTO = (
    TIPO_LICITACION,
    TIPO_CONCURSO_PRECIOS,
    TIPO_SUBASTA_ELECTRONICA,
    TIPO_COMPRA_DIRECTA,
    TIPO_CONTRATACION,
    TIPO_OBRA_PUBLICA,
    TIPO_SERVICIO,
    TIPO_SUBSIDIO_TRANSFERENCIA,
    TIPO_OTRO,
    TIPO_NO_ES_GASTO,
)

# ── Objeto del gasto (qué se compra o se hace) ──────────────────────────────────
#
# Tercer eje, y el que faltaba: `tipo_gasto` dice la figura por la que el dinero se
# mueve (licitación, concurso de precios, contratación), esto dice qué se compró.
# Un acto que dice "Licitación para la obra de drenaje" es `licitacion` + `obra`, y
# el ciudadano puede filtrar por las dos cosas. Con un solo campo había que elegir,
# y la elección no era del clasificador sino de quien lee.

OBJETO_OBRA = "obra"
OBJETO_BIEN = "bien"
OBJETO_SERVICIO = "servicio"
OBJETO_TRANSFERENCIA = "transferencia"
OBJETO_OTRO = "otro"
OBJETO_NO_APLICA = "no_aplica"

OBJETOS = (
    OBJETO_OBRA,
    OBJETO_BIEN,
    OBJETO_SERVICIO,
    OBJETO_TRANSFERENCIA,
    OBJETO_OTRO,
    OBJETO_NO_APLICA,
)

# ── Niveles de gobierno ────────────────────────────────────────────────────────

NIVEL_PROVINCIAL = "provincial"
NIVEL_MUNICIPAL = "municipal"
NIVEL_COMUNAL = "comunal"
# El corpus tiene entidades nacionales publicando en el boletín provincial (UNC,
# Colegio Nacional de Monserrat): sin este valor quedaban como `provincial`.
NIVEL_NACIONAL = "nacional"
NIVEL_DESCONOCIDO = "desconocido"

NIVELES = (NIVEL_PROVINCIAL, NIVEL_MUNICIPAL, NIVEL_COMUNAL, NIVEL_NACIONAL, NIVEL_DESCONOCIDO)

# ── Quién emite, según el organismo ────────────────────────────────────────────
#
# Se aplican sobre el organismo ya sin acentos, así que van sin diacríticos.

# Entidades nacionales.
_RE_ORG_NACIONAL = re.compile(
    r"universidad\s+nacional|colegio\s+nacional|banco\s+nacion|\banses\b|\bpami\b"
    r"|\bafip\b|\barca\b|vialidad\s+nacional|\bnacion\b",
    re.IGNORECASE,
)

# Organismos del Poder Judicial provincial.  Existen para que una **mención** en el
# cuerpo no decida el nivel: en *"MUNICIPALIDAD SAN ESTEBAN C/ ARGENTINA DE
# FOMENTO"* —una subasta de un juzgado provincial— la municipalidad es la parte
# actora, y el acto quedaba `municipal`.
_RE_ORG_JUDICIAL = re.compile(
    r"tribunal|juzgado|\bcamara\b|poder\s+judicial|fiscalia|sindicatura|martillero",
    re.IGNORECASE,
)

# ── Secciones del boletín provincial ───────────────────────────────────────────

SECCION_LEGISLACION = 1
SECCION_JUDICIAL = 2
SECCION_SOCIEDADES = 3
SECCION_LICITACIONES = 4
SECCION_MUNICIPAL = 5

# Sections whose content is structurally outside the provincial budget:
# S2 is judicial (edictos, remates, ejecuciones fiscales) and S3 is private
# corporate filings (capital, escisiones, asambleas).
_SECCIONES_NO_GASTO = {SECCION_JUDICIAL, SECCION_SOCIEDADES}


def _parse_section(section: Any) -> int | None:
    """Normalize the many shapes of `boletines.section` to 1-5.

    Seen in the wild: "1".."5" (current provincial rows), "S1".."S5" (older
    fixtures), "1_Secc" (scraper config), 4 (int).
    """
    if section is None:
        return None
    if isinstance(section, int):
        return section if 1 <= section <= 5 else None
    match = re.search(r"\d", str(section))
    if not match:
        return None
    value = int(match.group())
    return value if 1 <= value <= 5 else None


# ── Keyword sets ───────────────────────────────────────────────────────────────
#
# All patterns run against accent-stripped text (see `_strip_accents`).  Boletín
# text is inconsistent about accents and PDF extraction drops them, so matching
# "adjudicase" once beats spelling out "adjud[ií]c" in every pattern.

# Budget line transfers: they move the ceiling, they do not pay anyone.
_RE_MODIFICACION = re.compile(
    r"compensacion\s+de\s+(?:partidas|creditos)"
    r"|incremento\s+de\s+partidas"
    r"|modificacion\s+(?:del\s+)?presupuestaria"
    r"|modificacion\s+de\s+partidas"
    r"|reasignacion\s+de\s+(?:partidas|creditos)"
    r"|adecuacion\s+de\s+partidas"
    r"|ampliacion\s+de\s+partidas"
    r"|transferencia\s+de\s+partidas"
    r"|refuerzo\s+presupuestario",
    re.IGNORECASE,
)

# Judicial acts: notifications and asset auctions, never provincial spending.
# "subasta" alone is not enough — "subasta electrónica" is a procurement method.
_RE_JUDICIAL = re.compile(
    r"\bremate\b"
    r"|subasta\s+judicial"
    r"|ejecucion\s+fiscal"
    r"|\bmartiller[oa]\b"
    r"|\bedicto\b"
    r"|cita\s+y\s+emplaza"
    r"|concurso\s+preventivo"
    r"|\bquiebra\b"
    r"|\busucapion\b"
    r"|juicio\s+sucesorio"
    r"|declaratoria\s+de\s+herederos",
    re.IGNORECASE,
)

# Private corporate filings published in S3.
_RE_SOCIETARIO = re.compile(
    r"aumento\s+de\s+capital"
    r"|capital\s+social"
    r"|\bescision\b"
    r"|fusion\s+por\s+absorcion"
    r"|cesion\s+de\s+cuotas"
    r"|transformacion\s+societaria"
    r"|disolucion\s+(?:y\s+liquidacion|de\s+la\s+sociedad)"
    r"|reforma\s+de\s+estatuto"
    r"|asamblea\s+(?:general\s+)?(?:ordinaria|extraordinaria)"
    r"|designacion\s+de\s+autoridades",
    re.IGNORECASE,
)

_RE_ADJUDICACION = re.compile(r"adjudic|preadjudic", re.IGNORECASE)

_RE_CONTRATO = re.compile(
    r"contratacion\s+directa"
    r"|\bcontrato\b"
    # El boletín usa el imperativo: "CONTRÁTASE el servicio de limpieza".  Sin
    # esto, la familia entera de contrataciones directas quedaba afuera.
    r"|\bcontrat\w+se\b"
    r"|\bconvenio\b"
    r"|prorroga\s+de\s+contrato"
    r"|redeterminacion\s+de\s+precios"
    r"|ampliacion\s+de\s+obra",
    re.IGNORECASE,
)

_RE_PAGO = re.compile(
    r"\bsubsidio\b"
    r"|\btransferencia\b"
    r"|aporte\s+no\s+reintegrable"
    r"|\bpaguese\b"
    r"|autoriz\w*\s+(?:el\s+)?pago"
    r"|orden\s+de\s+pago"
    r"|\blibrese\b"
    r"|\bdevengad[oa]\b"
    r"|\babonar\b"
    # El imperativo ABÓNESE y los pagos que el acto ordena sin decir "pago":
    r"|\babon\w*se\b|\bsubsidiar\b|\bprestamo\b"
    r"|pago\s+de\s+(?:la\s+|el\s+)?obras?"
    r"|otorg\w*\s+(?:el\s+valor\s+de|la\s+suma\s+de|dinero)"
    r"|\bremuneraciones\s+del\s+personal\b"
    # "OTÓRGUENSE un incentivo educativo" mueve plata y no tenía ninguna señal:
    # la puerta de gasto lo perdía.  El verbo suelto no alcanza —"otórguese
    # personería jurídica" no gasta— así que pide el objeto de la concesión.
    r"|\bincentivo\b|\bbeca\b"
    r"|otorg\w*\s+(?:un\s+|una\s+)?(?:subsidio|aporte|incentivo|beca|ayuda)",
    re.IGNORECASE,
)

_RE_LLAMADO = re.compile(
    r"licitacion"
    r"|llama[sd]e?\s+a"
    r"|llamado\s+a"
    r"|\bpliego\b"
    r"|compulsa\s+abreviada"
    r"|concurso\s+de\s+precios"
    r"|subasta\s+electronica"
    r"|apertura\s+de\s+(?:las\s+)?ofertas"
    r"|presupuesto\s+oficial",
    re.IGNORECASE,
)

_RE_MUNICIPAL = re.compile(
    r"municipalidad|municipio|\bcomuna\b|concejo\s+deliberante|\bordenanza\b",
    re.IGNORECASE,
)

# ── Figuras y objetos de gasto (M8) ────────────────────────────────────────────
#
# Separate from the stage keywords above: those say *when* in the spending cycle
# the acto sits, these say *what* was bought.  Both run over accent-stripped
# text, so the patterns carry no diacritics.

# Public works.  The object beats the procedure that awarded it: a "Licitación
# Pública para obra de pavimento" is an obra, and `etapa_gasto` still records
# that it is at the `llamado` stage.
_RE_OBRA = re.compile(
    r"\bobra\s+publica\b"
    # "obra social" is a health insurer and "mano de obra" is a price component,
    # not a work.  Both would otherwise pull acts into `obra_publica`.
    r"|(?<!mano\sde\s)\bobras?\b(?!\s+social)"
    r"|paviment|repaviment|asfalt|bacheo|cordon\s+cuneta"
    r"|red\s+cloacal|\bcloaca|agua\s+potable|desague|pluvial"
    r"|construccion|edificio\s+escolar|viviend"
    r"|ampliacion\s+de\s+obra",
    re.IGNORECASE,
)

# Services: bought as a service rather than as a good.  Bare "servicio" is
# deliberately absent — "Servicio Administrativo Financiero" is an org unit and
# "servicio de la deuda" is debt, neither is a procurement of a service.
_RE_SERVICIO = re.compile(
    r"servicio\s+de\s+(?:limpieza|vigilancia|seguridad|mantenimiento|recoleccion"
    r"|transporte|alumbrado|comedor|catering|jardineria|poda|logistica"
    r"|informatica|publicidad|comunicacion|capacitacion|consultoria|auditoria)"
    r"|prestacion\s+de\s+servicios?"
    r"|locacion\s+de\s+(?:obra|servicio|inmueble|vehiculo|equipo)"
    r"|\balquiler\b"
    r"|mantenimiento\s+(?:de|preventivo|correctivo)"
    # `limpieza` pelado matcheaba "ADQUISICIÓN DE ELEMENTOS DE LIMPIEZA" — una
    # compra de insumos leída como servicio de limpieza.  El servicio necesita
    # su preposición.
    r"|limpieza\s+(?:de|integral|diaria|general)"
    r"|\bvigilancia\b|seguridad\s+privada",
    re.IGNORECASE,
)

# Explicit figures.  These are the procedure names of Ley 10.155 / 8.614, so
# they are unambiguous when present and outrank the loose `contrato|convenio`
# that `_RE_CONTRATO` matches (a tender call often mentions its "contrato").
_RE_CONCURSO_PRECIOS = re.compile(
    # "Concurso de Precios" y "Concurso Privado de Precios": el boletín usa las
    # dos, y la segunda no estaba contemplada (dos actos de Cosquín caían en
    # `otro`).
    r"concurso\s+(?:privado\s+|publico\s+|abreviado\s+)?de\s+precios"
    r"|compulsa\s+abreviada",
    re.IGNORECASE,
)

_RE_SUBASTA_ELECTRONICA = re.compile(r"subasta\s+electronica", re.IGNORECASE)

_RE_COMPRA_DIRECTA = re.compile(
    r"compra\s+directa|adquisicion\s+directa"
    r"|necesidad\s+y\s+urgencia|urgencia\s+manifiesta",
    re.IGNORECASE,
)

# Verbos de compra: la señal de que lo que se adquiere es un bien.  "Elementos de
# limpieza" es una compra de insumos; "servicio de limpieza" es un servicio, y esa
# diferencia la decide el verbo, no el sustantivo.
_RE_COMPRA_VERBO = re.compile(
    # `\badqui\w*` cubre adquisición, adquirir y el imperativo ADQUIÉRASE, que es
    # como el boletín ordena una compra sin nombrar procedimiento — y que no
    # matcheaba ninguna señal de etapa, así que la compra se perdía entera.
    r"\badqui\w*|\bcompra\w*|\bprovision\w*|\bsuministro\w*"
    r"|proveeduria|\breposicion\w*",
    re.IGNORECASE,
)

# Plata que ENTRA (o que sólo se pide): el acto no dispone de dinero público, aunque
# sus palabras se parezcan a las de un gasto.  Cada patrón tiene una fila medida
# detrás — una venta de lote leída como `licitacion`, *"transferencia"* entre dos
# cuentas propias del municipio, una concesión donde la comuna cobra canon, un
# convenio tributario donde recauda para la provincia, y una solicitud de subsidio.
_RE_INGRESO = re.compile(
    r"\bventa\s+de\s+(?:lote|terreno|inmueble|vehiculo|automotor|bien|chatarra)"
    r"|oferta\s+publica\s+de\s+(?:venta|transferencia)|llamado\s+a\s+venta"
    r"|subasta\s+(?:electronica\s+)?de\s+(?:un\s+)?(?:lote|inmueble|vehiculo)"
    r"|transfer\w*\s+de\s+la\s+cuenta\s+corriente|de\s+la\s+cuenta\s+n"
    r"|concesion\s+de\s+(?:uso|locales|explotacion)|entrega\s+de\s+concesion"
    r"|prorroga\s+del\s+contrato\s+de\s+concesion"
    r"|convenio\s+de\s+cooperacion\b[^.]{0,60}tributaria"
    r"|\bsolicita\s+(?:un\s+)?subsidio\b"
    r"|facilidades\s+de\s+pago|regimen\s+de\s+regularizacion"
    r"|valores\s+a\s+abonar|importes\s+mensuales\s+que\s+deben\s+ingresar",
    re.IGNORECASE,
)

# The instrument, narrower than `_RE_PAGO`: that one also carries generic
# payment verbs ("paguese", "abonar") which do not identify a figure — an acto
# that pays a contract is still a `contratacion`.
_RE_SUBSIDIO = re.compile(
    r"\bsubsidio\b|\btransferencia\b|aporte\s+no\s+reintegrable|ayuda\s+economica"
    r"|\bincentivo\b|\bbeca\b|aporte\s+(?:economico|financiero)",
    re.IGNORECASE,
)

# Comunas are the smallest level: a `comuna` is not a `municipalidad`.
_RE_COMUNA = re.compile(r"\bcomunas?\b|comision\s+comunal|comunales", re.IGNORECASE)

# `municipio_de_organismo` strips this prefix off an organismo label.  Kept
# accent-tolerant and applied to the raw label so the returned name keeps its
# accents ("Río Ceballos", not "Rio Ceballos").
_RE_ORG_MUNICIPIO = re.compile(
    r"^\s*(?:municipalidad|municipio|intendente\s+municipal|comunas?"
    r"|comisi[oó]n\s+comunal|concejo\s+deliberante)\s+(?:de\s+|del\s+)?(.+?)\s*$",
    re.IGNORECASE,
)

# tipo_acto values that are payments by nature
_TIPOS_PAGO = {"subsidio", "transferencia"}
# tipo_acto values that are tender calls by nature
_TIPOS_LLAMADO = {"licitacion"}


@dataclass(frozen=True)
class GastoClassification:
    """Outcome of classifying one acto."""

    is_gasto_publico: bool
    etapa_gasto: str
    jurisdiccion: str
    tipo_gasto: str
    objeto: str
    nivel: str
    municipio: str | None
    motivo: str
    tipo_gasto_motivo: str

    def as_analisis_fields(self) -> dict[str, Any]:
        """Shape expected by `Analisis` / `create_analisis`.

        One reason column, not two: `gasto_motivo` carries the figure's reason
        for an acto that spends and the exclusion's reason for one that does
        not — that is what the listing has to show.  `motivo` keeps its P.7.1
        meaning for the callers that already read it.
        """
        return {
            "is_gasto_publico": self.is_gasto_publico,
            "etapa_gasto": self.etapa_gasto,
            "jurisdiccion_gasto": self.jurisdiccion,
            "tipo_gasto": self.tipo_gasto,
            "objeto": self.objeto,
            "nivel": self.nivel,
            "municipio": self.municipio,
            "gasto_motivo": (
                self.motivo if self.tipo_gasto == TIPO_NO_ES_GASTO else self.tipo_gasto_motivo
            ),
        }

    @property
    def cuenta_contra_presupuesto_provincial(self) -> bool:
        """Whether this acto may sum into the provincial accumulators."""
        return self.is_gasto_publico and self.jurisdiccion == JURISDICCION_PROVINCIAL


def _strip_accents(s: str) -> str:
    """Drop diacritics so patterns match 'adjudicase' and 'adjudícase' alike."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _haystack(acto: Mapping[str, Any]) -> str:
    """Concatenate the acto text fields the keyword rules run over."""
    parts = [
        acto.get("descripcion"),
        acto.get("texto_original"),
        acto.get("relacion_principal"),
        acto.get("fragmento"),
        acto.get("organismo"),
    ]
    joined = " \n ".join(str(p) for p in parts if p)
    return _strip_accents(joined[:4000])


def _classify_jurisdiccion(section: int | None, text: str) -> str:
    if section in _SECCIONES_NO_GASTO:
        return JURISDICCION_FUERA
    if section == SECCION_MUNICIPAL:
        return JURISDICCION_MUNICIPAL
    if _RE_MUNICIPAL.search(text):
        return JURISDICCION_MUNICIPAL
    return JURISDICCION_PROVINCIAL


def _classify_etapa(tipo_acto: str, text: str) -> tuple[str, str]:
    """Return (etapa, motivo) for an acto already known to be spending-like.

    Precedence is by position in the spending cycle, latest stage first: an acto
    that adjudicates a tender is an `adjudicacion` even though its text still
    says "Licitación Pública".  `tipo_acto` wins for payments because the LLM
    field is more reliable there than keyword soup.
    """
    if tipo_acto in _TIPOS_PAGO:
        return ETAPA_PAGO, f"tipo_acto={tipo_acto}"
    if _RE_ADJUDICACION.search(text):
        return ETAPA_ADJUDICACION, "keyword adjudicacion"
    if _RE_CONTRATO.search(text):
        return ETAPA_CONTRATO, "keyword contrato"
    if _RE_PAGO.search(text):
        return ETAPA_PAGO, "keyword pago"
    if _RE_LLAMADO.search(text) or tipo_acto in _TIPOS_LLAMADO:
        return ETAPA_LLAMADO, "keyword llamado"
    # Va **último**: es la señal más débil, porque el verbo de compra no dice en qué
    # etapa está — sólo que se compra.  Antes del llamado convertía "Licitación para
    # la compra de X" en un contrato.
    if _RE_COMPRA_VERBO.search(text):
        return ETAPA_CONTRATO, "verbo de compra"
    return ETAPA_NO_APLICA, "sin señal de gasto"


def _classify_tipo_gasto(tipo_acto: str, text: str) -> tuple[str, str]:
    """Return (tipo_gasto, motivo): la FIGURA por la que el dinero se mueve.

    Es el procedimiento, no el objeto.  Una "Licitación para la obra de drenaje"
    es `licitacion` acá y `obra` en `objeto`; los dos ejes existen porque el
    ciudadano quiere poder filtrar por "obras" y por "licitaciones" a la vez, y
    con un solo campo había que elegir — y la elección no la podía hacer el
    clasificador.

    Precedencia: las figuras explícitas antes que el `contrato|convenio` suelto de
    `_RE_CONTRATO`, que todo pliego menciona.
    """
    if tipo_acto in _TIPOS_PAGO or _RE_SUBSIDIO.search(text):
        return TIPO_SUBSIDIO_TRANSFERENCIA, "subsidio/transferencia"
    if _RE_SUBASTA_ELECTRONICA.search(text):
        return TIPO_SUBASTA_ELECTRONICA, "keyword subasta electronica"
    if _RE_CONCURSO_PRECIOS.search(text):
        return TIPO_CONCURSO_PRECIOS, "keyword concurso de precios"
    if _RE_COMPRA_DIRECTA.search(text):
        return TIPO_COMPRA_DIRECTA, "keyword compra directa"
    if _RE_LLAMADO.search(text) or tipo_acto in _TIPOS_LLAMADO:
        return TIPO_LICITACION, "keyword licitacion"
    if _RE_CONTRATO.search(text):
        return TIPO_CONTRATACION, "keyword contratacion"
    return TIPO_OTRO, "gasto con monto y sin figura reconocible en el texto"


def _classify_objeto(tipo_gasto: str, text: str) -> str:
    """Qué se compra o se hace, ya sabiendo por qué figura se mueve el dinero.

    El orden importa: una transferencia es una transferencia aunque su texto
    mencione una obra, y una obra es una obra antes que un servicio ("obra de
    mantenimiento" se compra como obra).
    """
    if tipo_gasto == TIPO_NO_ES_GASTO:
        return OBJETO_NO_APLICA
    if tipo_gasto == TIPO_SUBSIDIO_TRANSFERENCIA:
        return OBJETO_TRANSFERENCIA
    if _RE_OBRA.search(text):
        return OBJETO_OBRA
    if _RE_SERVICIO.search(text):
        return OBJETO_SERVICIO
    if _RE_COMPRA_VERBO.search(text):
        return OBJETO_BIEN
    return OBJETO_OTRO


def _classify_nivel(section: int | None, organismo: Any, text: str, jurisdiccion: str) -> str:
    """Nivel de gobierno de **quien emite** el acto.

    El orden importa, y es la corrección de un bug medido: una **mención** en el
    cuerpo no decide el nivel.  Manda el organismo; la mención en el texto es la
    última señal y va después de la sección, porque es la más débil.
    """
    org = _strip_accents(str(organismo or "")).strip().lower()

    # 1. Quién emite, según el organismo.
    if _RE_ORG_NACIONAL.search(org):
        return NIVEL_NACIONAL
    if _RE_COMUNA.search(org):
        return NIVEL_COMUNAL
    if _RE_MUNICIPAL.search(org):
        return NIVEL_MUNICIPAL
    if _RE_ORG_JUDICIAL.search(org):
        return NIVEL_PROVINCIAL

    # 2. La sección 5 del boletín provincial **es** la municipal.
    if section == SECCION_MUNICIPAL:
        return NIVEL_MUNICIPAL

    # 3. El cuerpo del acto, sólo si el organismo no dijo nada.
    if _RE_COMUNA.search(text):
        return NIVEL_COMUNAL
    if _RE_MUNICIPAL.search(text):
        return NIVEL_MUNICIPAL
    if jurisdiccion == JURISDICCION_PROVINCIAL:
        return NIVEL_PROVINCIAL
    return NIVEL_DESCONOCIDO


def municipio_de_organismo(organismo: Any) -> str | None:
    """Municipality name out of an organismo label, or ``None``.

    The corpus spells these "Municipalidad de Carrilobo", "Comuna de Los
    Reartes", "Intendente Municipal de Río Ceballos".  Only the label is read,
    never the body text — which mentions municipalities in passing and would
    invent a jurisdiction out of a mention.
    """
    if not organismo:
        return None
    match = _RE_ORG_MUNICIPIO.match(str(organismo).strip())
    if not match:
        return None
    name = match.group(1).strip(" .,-")
    return name.title() if name else None


def classify_gasto(
    acto: Mapping[str, Any],
    section: Any = None,
) -> GastoClassification:
    """Classify one acto for the spending ledger.

    `acto` accepts either the LLM extraction dict or a row-like mapping from
    `analisis`; it reads `tipo_acto`, `descripcion`, `texto_original`,
    `relacion_principal`, `fragmento` and `organismo`, all optional.
    `section` is `boletines.section` in any of its observed shapes.

    Actos with no recognizable spending signal default to
    `is_gasto_publico=False`: the ledger is a claim about public money, so an
    unclassifiable acto stays out of it rather than inflating the total.
    """
    sec = _parse_section(section)
    text = _haystack(acto)
    tipo_acto = str(acto.get("tipo_acto") or "").strip().lower()
    jurisdiccion = _classify_jurisdiccion(sec, text)
    nivel = _classify_nivel(sec, acto.get("organismo"), text, jurisdiccion)
    municipio = municipio_de_organismo(acto.get("organismo"))

    # Budget line transfers first: they can appear in S1 legislation and would
    # otherwise read as spending via "transferencia".
    if _RE_MODIFICACION.search(text):
        motivo = "modificacion de partidas: mueve el techo, no paga"
        return GastoClassification(
            is_gasto_publico=False,
            etapa_gasto=ETAPA_MODIFICACION,
            jurisdiccion=jurisdiccion,
            tipo_gasto=TIPO_NO_ES_GASTO,
            nivel=nivel,
            municipio=municipio,
            objeto=OBJETO_NO_APLICA,
            motivo=motivo,
            tipo_gasto_motivo=motivo,
        )

    if _RE_JUDICIAL.search(text):
        motivo = "acto judicial (edicto/remate/ejecucion fiscal)"
        return GastoClassification(
            is_gasto_publico=False,
            etapa_gasto=ETAPA_NO_APLICA,
            jurisdiccion=JURISDICCION_FUERA,
            tipo_gasto=TIPO_NO_ES_GASTO,
            nivel=nivel,
            municipio=municipio,
            objeto=OBJETO_NO_APLICA,
            motivo=motivo,
            tipo_gasto_motivo=motivo,
        )

    if _RE_SOCIETARIO.search(text):
        motivo = "acto societario privado (capital/escision/asamblea)"
        return GastoClassification(
            is_gasto_publico=False,
            etapa_gasto=ETAPA_NO_APLICA,
            jurisdiccion=JURISDICCION_FUERA,
            tipo_gasto=TIPO_NO_ES_GASTO,
            nivel=nivel,
            municipio=municipio,
            objeto=OBJETO_NO_APLICA,
            motivo=motivo,
            tipo_gasto_motivo=motivo,
        )

    if _RE_INGRESO.search(text):
        motivo = "plata que entra o que solo se pide: el acto no dispone de dinero publico"
        return GastoClassification(
            is_gasto_publico=False,
            etapa_gasto=ETAPA_NO_APLICA,
            jurisdiccion=jurisdiccion,
            tipo_gasto=TIPO_NO_ES_GASTO,
            nivel=nivel,
            municipio=municipio,
            objeto=OBJETO_NO_APLICA,
            motivo=motivo,
            tipo_gasto_motivo=motivo,
        )

    if sec in _SECCIONES_NO_GASTO:
        motivo = f"seccion {sec} fuera del presupuesto provincial"
        return GastoClassification(
            is_gasto_publico=False,
            etapa_gasto=ETAPA_NO_APLICA,
            jurisdiccion=JURISDICCION_FUERA,
            tipo_gasto=TIPO_NO_ES_GASTO,
            nivel=nivel,
            municipio=municipio,
            objeto=OBJETO_NO_APLICA,
            motivo=motivo,
            tipo_gasto_motivo=motivo,
        )

    etapa, motivo = _classify_etapa(tipo_acto, text)
    is_gasto = etapa != ETAPA_NO_APLICA
    tipo_gasto, tipo_gasto_motivo = _classify_tipo_gasto(tipo_acto, text)
    if not is_gasto and tipo_gasto == TIPO_OTRO:
        # Neither a stage keyword nor a recognizable figure: nothing in the acto
        # says public money moved.  The figure axis and the ledger gate are
        # separate questions — "Contrátase el servicio de limpieza" is a service
        # the citizen should see in the listing, but it carries no stage
        # evidence, so it stays out of the ledger (`is_gasto_publico=False`) and
        # the listing shows both facts instead of merging them.
        tipo_gasto, tipo_gasto_motivo = TIPO_NO_ES_GASTO, motivo
    return GastoClassification(
        is_gasto_publico=is_gasto,
        etapa_gasto=etapa,
        jurisdiccion=jurisdiccion,
        tipo_gasto=tipo_gasto,
        objeto=_classify_objeto(tipo_gasto, text),
        nivel=nivel,
        municipio=municipio,
        motivo=motivo,
        tipo_gasto_motivo=tipo_gasto_motivo,
    )

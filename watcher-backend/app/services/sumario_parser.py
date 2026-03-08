"""
Sumario Parser para Boletines Oficiales de la Provincia de Córdoba.

Parsea el bloque SUMARIO de la primera página de los boletines para extraer
la estructura de organismos/categorías con sus páginas de inicio.

Formatos soportados:
  Tipo A (organismo_jerarquia):
      MINISTERIO DE EDUCACIÓN
      Resolución N° 1813 - Letra:D ............. Pag. 1

  Tipo B (categorias_simples):
      Licitaciones .......... Pag. 1
      Subastas Electrónicas ... Pag. 2

  Tipo C (categorias_judiciales):
      Concursos y Quiebras .... Pag. 1
      Declaratorias de Herederos ... Pag. 1

Nota sobre extracción de PDF:
  pdfplumber lee columnas de izquierda a derecha por fila. En boletines con
  layout de 2 columnas, el texto del cuerpo (columna derecha) puede intercalarse
  con el sumario (columna izquierda). El parser filtra ese ruido a nivel de regex.
"""

import re
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Estructuras de datos
# ---------------------------------------------------------------------------

@dataclass
class SumarioEntry:
    """Entrada individual del sumario."""
    nombre: str
    pagina_inicio: int
    tipo: str                          # "organismo" | "categoria" | "acto"
    organismo: Optional[str] = None    # Solo Tipo A: organismo padre del acto
    tipo_acto: Optional[str] = None    # Solo Tipo A: "decreto" | "resolucion" | "acuerdo"
    numero_acto: Optional[str] = None  # Solo Tipo A: "272" | "2132"
    letra: Optional[str] = None        # Solo Tipo A: "D" | "C" (serie)


@dataclass
class SumarioResult:
    """Resultado del parseo del sumario."""
    found: bool
    format_type: str         # "organismo_jerarquia" | "categorias_simples" | "categorias_judiciales" | "unknown"
    entries: List[SumarioEntry] = field(default_factory=list)
    sumario_page: int = 0    # Estimado: 1 si está en los primeros ~2500 chars
    raw_text: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "found": self.found,
            "format_type": self.format_type,
            "entries": [asdict(e) for e in self.entries],
            "sumario_page": self.sumario_page,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# Palabras clave para clasificación de formato
# ---------------------------------------------------------------------------

_JUDICIAL_KEYWORDS = {
    "concurso", "quiebra", "citacion", "citación",
    "declaratoria", "heredero", "usucapion", "usucapión",
    "sumaria",
}

_ORGANISMO_KEYWORDS = {
    "poder ejecutivo", "ministerio", "secretaria", "secretaría",
    "dirección general", "direccion general", "tribunal superior",
    "ente regulador", "ersep", "epec", "municipalidad",
}


# ---------------------------------------------------------------------------
# Parser principal
# ---------------------------------------------------------------------------

class SumarioParser:
    """
    Parser del bloque SUMARIO para boletines provinciales de Córdoba.

    Uso:
        parser = SumarioParser()
        result = parser.parse_from_text(full_text)
    """

    # Header: acepta variaciones tipográficas / artefactos de OCR
    _RE_HEADER = re.compile(r'\bSUMARIO\b', re.IGNORECASE)

    # Tipo A — acto del sumario (sin requerir indent: en estos PDFs van a columna 0)
    # Ejemplos reales:
    #   "Resolución N° 1813 - Letra:D .....Pag. 1"
    #   "Decreto N° 272 ......Pag. 1"
    #   "Resolución General N° 3 - Letra:D .....Pag. 5"
    _RE_ACTO = re.compile(
        r'^'
        r'(Decreto|Resoluci[oó]n(?:\s+General)?|Acuerdo\s+Reglamentario|Acuerdo|Disposici[oó]n|Ordenanza)'
        r'\s+(?:N[°º.]\s*)?'
        r'(\d[\d/\-\.]*)'
        r'(?:\s*[-–]\s*(?:Serie[:\s]*|Letra[:\s]*)([A-Z]))?'
        r'\s*[.…\u2026]{2,}'
        r'\s*P[aá]g?s?\.?\s*(\d+)',
        re.MULTILINE | re.IGNORECASE
    )

    # Tipo B/C — categoría con puntos y número de página
    # e.g. "Licitaciones .......... Pag. 1"
    # e.g. "CONCURSOS Y QUIEBRAS Concursos y Quiebras ....... Pág. 1"  (merge de columna)
    _RE_CATEGORIA = re.compile(
        r'^([A-ZÁÉÍÓÚÑÜA-Za-záéíóúñü][^.\n]{3,55}?)\s*[.…\u2026]{2,}\s*P[aá]g?s?\.?\s*(\d+)',
        re.MULTILINE
    )

    # ---------------------------------------------------------------------------
    # API pública
    # ---------------------------------------------------------------------------

    def parse_from_text(self, text: str, max_chars: int = 8000) -> SumarioResult:
        """
        Parsea el sumario desde el texto completo del boletín.

        Busca en los primeros `max_chars` caracteres para evitar
        falsos positivos en el cuerpo del documento.
        """
        search_text = text[:max_chars]
        block_info = self._find_sumario_block(search_text)

        if block_info is None:
            logger.debug("Bloque SUMARIO no encontrado en los primeros %d caracteres", max_chars)
            return SumarioResult(found=False, format_type="unknown")

        page_num, block_text = block_info
        format_type = self._detect_format(block_text)

        if format_type == "organismo_jerarquia":
            entries = self._parse_organismo_jerarquia(block_text)
        else:
            entries = self._parse_categorias(block_text)

        confidence = self._calculate_confidence(entries, format_type)

        logger.info(
            "Sumario parseado: formato=%s entries=%d confianza=%.2f",
            format_type, len(entries), confidence
        )

        return SumarioResult(
            found=True,
            format_type=format_type,
            entries=entries,
            sumario_page=page_num,
            raw_text=block_text,
            confidence=confidence,
        )

    # ---------------------------------------------------------------------------
    # Localización del bloque
    # ---------------------------------------------------------------------------

    def _find_sumario_block(self, text: str) -> Optional[Tuple[int, str]]:
        """Localiza el bloque de texto que sigue al header SUMARIO."""
        match = self._RE_HEADER.search(text)
        if not match:
            return None

        remaining = text[match.end():]
        block = self._extract_block(remaining, max_len=3000)

        if len(block.strip()) < 20:
            return None

        page_estimate = 1 if match.start() < 2500 else 2
        return page_estimate, block.strip()

    def _extract_block(self, text: str, max_len: int) -> str:
        """
        Extrae el bloque del sumario.

        Estrategia: escanear líneas y determinar la última línea "válida"
        (tiene referencia a página o es header de organismo en caps).
        Retornar solo hasta ese punto + un pequeño buffer.

        Esto descarta texto del cuerpo del documento que pdfplumber puede
        intercalar por el layout de 2 columnas del PDF.
        """
        lines = text[:max_len].split('\n')
        last_valid_idx = -1

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            has_page_ref = bool(re.search(r'P[aá]g?s?\.?\s*\d+', stripped, re.IGNORECASE))
            is_organismo_header = (
                stripped == stripped.upper()
                and not re.search(r'[\d.…:@]', stripped)
                and 4 <= len(stripped) <= 75
            )

            if has_page_ref or is_organismo_header:
                last_valid_idx = i

        if last_valid_idx < 0:
            return text[:max_len]

        # Tomar hasta la última línea válida + 2 líneas de buffer
        cutoff = min(last_valid_idx + 3, len(lines))
        return '\n'.join(lines[:cutoff])

    # ---------------------------------------------------------------------------
    # Detección de formato
    # ---------------------------------------------------------------------------

    def _detect_format(self, block_text: str) -> str:
        """Clasifica el tipo de sumario."""
        text_lower = block_text.lower()

        # Tipo C: múltiples palabras clave judiciales
        judicial_hits = sum(1 for kw in _JUDICIAL_KEYWORDS if kw in text_lower)
        if judicial_hits >= 2:
            return "categorias_judiciales"

        # Tipo A: hay al menos un acto (Decreto/Resolución + número + página)
        if self._RE_ACTO.search(block_text):
            return "organismo_jerarquia"

        # Tipo A alternativo: hay líneas en caps que son organismos conocidos
        for kw in _ORGANISMO_KEYWORDS:
            if kw in text_lower:
                if re.search(r'^[A-ZÁÉÍÓÚÑ\s\-]+$', block_text, re.MULTILINE):
                    return "organismo_jerarquia"

        return "categorias_simples"

    # ---------------------------------------------------------------------------
    # Parsers por formato
    # ---------------------------------------------------------------------------

    def _parse_organismo_jerarquia(self, text: str) -> List[SumarioEntry]:
        """
        Parsea sumarios con estructura jerárquica:
          MINISTERIO DE EDUCACIÓN         ← organismo header (todo caps)
          Resolución N° 1813 - Letra:D .. Pag. 1  ← acto (sin indent en PDFs reales)
        """
        entries: List[SumarioEntry] = []
        current_organismo: Optional[str] = None
        seen_organismos: set = set()

        for line in text.split('\n'):
            stripped = line.strip()
            if not stripped:
                continue

            # Intento 1: línea de acto (Decreto/Resolución N° ... Pag. N)
            acto_match = self._RE_ACTO.match(line)
            if acto_match:
                tipo_raw, numero, letra, pagina = acto_match.groups()
                tipo_norm = self._normalize_tipo_acto(tipo_raw)
                nombre = f"{tipo_raw.strip()} N° {numero}"
                if letra:
                    nombre += f" - Letra {letra}"
                entries.append(SumarioEntry(
                    nombre=nombre,
                    pagina_inicio=int(pagina),
                    tipo="acto",
                    organismo=current_organismo,
                    tipo_acto=tipo_norm,
                    numero_acto=numero,
                    letra=letra,
                ))
                continue

            # Intento 2: línea de organismo (todo caps, sin números, puntos, @ ni :)
            is_all_caps = stripped == stripped.upper()
            has_noise = bool(re.search(r'[\d.…:@,]', stripped))
            is_valid_len = 4 <= len(stripped) <= 75

            if is_all_caps and not has_noise and is_valid_len:
                if stripped not in seen_organismos:
                    current_organismo = stripped
                    seen_organismos.add(stripped)
                    entries.append(SumarioEntry(
                        nombre=stripped,
                        pagina_inicio=0,
                        tipo="organismo",
                        organismo=stripped,
                    ))

        return entries

    def _parse_categorias(self, text: str) -> List[SumarioEntry]:
        """
        Parsea sumarios con categorías simples:
          Licitaciones .......... Pag. 1

        Filtra:
        - Nombres que empiezan en minúscula (fragmento de cuerpo del documento)
        - Nombres demasiado largos (texto de cuerpo infiltrado)
        - Nombres todo en mayúsculas (headers, no entradas)
        """
        entries: List[SumarioEntry] = []
        seen: set = set()

        for match in self._RE_CATEGORIA.finditer(text):
            nombre_raw = match.group(1).strip()
            pagina = int(match.group(2))

            # Filtro 1: fragmentos de cuerpo que empiezan en minúscula
            if nombre_raw and nombre_raw[0].islower():
                continue

            # Filtro 2: nombre demasiado largo (texto de cuerpo)
            if len(nombre_raw) > 55:
                continue

            # Filtro 3: todo en mayúsculas — header no es entrada válida por sí solo
            if nombre_raw.isupper():
                continue

            # Limpieza: quitar prefijo en MAYÚSCULAS si está seguido del mismo texto
            # en mixed-case (artefacto del merge de columnas PDF)
            # "CONCURSOS Y QUIEBRAS Concursos y Quiebras" → "Concursos y Quiebras"
            nombre = self._strip_caps_prefix(nombre_raw)

            if nombre in seen:
                continue
            seen.add(nombre)

            entries.append(SumarioEntry(
                nombre=nombre,
                pagina_inicio=pagina,
                tipo="categoria",
            ))

        return entries

    # ---------------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------------

    def _strip_caps_prefix(self, nombre: str) -> str:
        """
        Si el nombre empieza con palabras en MAYÚSCULAS seguidas de texto en
        mixed-case, retorna solo la parte en mixed-case.

        "CONCURSOS Y QUIEBRAS Concursos y Quiebras" → "Concursos y Quiebras"
        "LICITACIONES Licitaciones" → "Licitaciones"
        "Subastas Electrónicas" → "Subastas Electrónicas" (sin cambio)
        """
        words = nombre.split()
        first_mixed_idx = None
        for i, word in enumerate(words):
            # Palabra con alguna minúscula y más de 1 letra (excluye "Y", "E", "A")
            if len(word) > 1 and word != word.upper():
                first_mixed_idx = i
                break

        if first_mixed_idx is not None and first_mixed_idx > 0:
            return ' '.join(words[first_mixed_idx:]).strip()

        return nombre

    def _normalize_tipo_acto(self, raw: str) -> str:
        raw_lower = raw.lower().strip()
        if "decreto" in raw_lower:
            return "decreto"
        if "resoluci" in raw_lower:
            return "resolucion"
        if "acuerdo" in raw_lower:
            return "acuerdo"
        if "disposici" in raw_lower:
            return "disposicion"
        if "ordenanza" in raw_lower:
            return "ordenanza"
        return raw_lower

    def _calculate_confidence(self, entries: List[SumarioEntry], format_type: str) -> float:
        """Estima la confianza del parseo según cantidad y calidad de entries."""
        if not entries:
            return 0.0

        entries_con_pagina = [
            e for e in entries
            if e.tipo in ("acto", "categoria") and e.pagina_inicio > 0
        ]
        if not entries_con_pagina:
            return 0.3  # Encontramos algo pero sin páginas claras

        ratio = len(entries_con_pagina) / max(len(entries), 1)
        return min(round(0.5 + 0.45 * ratio, 2), 0.95)

"""
Servicio unificado de extracción y persistencia de entidades
Consolida lógica dispersa en múltiples archivos para un sistema centralizado
"""

import re
import unicodedata
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import EntidadExtraida, MencionEntidad, RelacionEntidad, Boletin

logger = logging.getLogger(__name__)


@dataclass
class EntityResult:
    """Resultado de extracción de una entidad"""
    tipo: str
    nombre: str
    nombre_normalizado: str
    variantes: List[str]
    contexto: str
    posicion: int
    confianza: float
    metadata: Dict[str, Any]


@dataclass
class RelationshipResult:
    """Resultado de detección de una relación"""
    entidad_origen: str
    entidad_destino: str
    tipo_relacion: str
    contexto: str
    confianza: float
    metadata: Dict[str, Any]


@dataclass
class EntityMap:
    """Spatial index: maps char positions to entities for boundary-aware chunking."""
    _entries: List[Tuple[int, int, "EntityResult"]] = field(default_factory=list)

    def add(self, start: int, end: int, entity: "EntityResult") -> None:
        self._entries.append((start, end, entity))

    def get_entities_in_range(self, start: int, end: int) -> List["EntityResult"]:
        return [e for (s, en, e) in self._entries if s >= start and en <= end]

    def entity_crosses_boundary(self, boundary: int, window: int = 50) -> bool:
        """Returns True if any entity spans across boundary ± window chars."""
        for (s, en, _) in self._entries:
            if s < boundary and en > boundary:
                return True
            if (boundary - window) <= s <= boundary <= en <= (boundary + window):
                return True
        return False


class EntityService:
    """Servicio para extracción y persistencia de entidades"""
    
    def __init__(self):
        # Patrones para extracción de personas.
        # Prefijo: (?i:...) → case-insensitive solo en el prefijo (Sr./DR./etc.).
        # Grupo captura: sin IGNORECASE → requiere Proper Case (ej. "Juan García").
        # Los apellidos en ALL-CAPS (ej. "SOSA LANZA") se admiten explícitamente
        # con el grupo alternativo [A-ZÁÉÍÓÚÑ]{2,}  para cada token.
        _NAME = r'(?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|[A-ZÁÉÍÓÚÑ]{2,})(?:\s+(?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|[A-ZÁÉÍÓÚÑ]{2,})){1,3}'
        self.persona_patterns = [
            # Título + nombre (Sr., Dra., LIC., etc.)
            rf'(?i:(?:SR\.|SRA\.|LIC\.|DR\.|DRA\.|ING\.|PROF\.))\s+({_NAME})',
            # DESIGNAR A <nombre>
            rf'(?i:DESIGNAR?\s+(?:EN\s+EL\s+CARGO\s+)?A\s+)({_NAME})',
            # DNI N° número[,] nombre
            rf'(?i:D\.?N\.?I\.?\s*N?[°º]?\s*[\d\.]+[,\s]+)({_NAME})',
            # A FAVOR DE <nombre> (solo ALL-CAPS contexto → sin inline flag)
            rf'A\s+FAVOR\s+DE\s+({_NAME})',
        ]

        # Organismos: patrones anclados a líneas ALL-CAPS (MULTILINE, sin IGNORECASE)
        # group(1) captura el nombre completo (incluye el prefijo MINISTERIO DE / etc.)
        self.organismo_caps_patterns = [
            r'^(MINISTERIO\s+DE\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-\/]{2,50}?)\s*$',
            r'^(SECRETAR[ÍI]A\s+(?:GENERAL\s+)?DE\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-\/]{2,50}?)\s*$',
            r'^(DIRECCI[ÓO]N\s+(?:GENERAL\s+)?DE\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-\/]{2,50}?)\s*$',
            r'^(SUBSECRETAR[ÍI]A\s+DE\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-\/]{2,50}?)\s*$',
            r'^(AGENCIA\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-\/]{2,50}?)\s*$',
            r'^(MUNICIPALIDAD\s+DE\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-\/]{2,30}?)\s*$',
            r'^(GOBIERNO\s+DE\s+(?:LA\s+)?[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{2,30}?)\s*$',
            r'^(PODER\s+(?:EJECUTIVO|JUDICIAL|LEGISLATIVO)[A-ZÁÉÍÓÚÑ\s]{0,30}?)\s*$',
            r'^(TRIBUNAL\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-]{2,50}?)\s*$',
            r'^(ENTE\s+(?:REGULADOR\s+)?[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-]{2,40}?)\s*$',
        ]

        # Empresas: patrones anclados a líneas ALL-CAPS que terminan en sufijo societario
        # group(1) captura el nombre completo (nombre + S.A. / S.R.L. etc.)
        self.empresa_caps_patterns = [
            r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-&\.]{3,55}\s+S\.A\.U?\.)\s*$',
            r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-&\.]{3,55}\s+S\.R\.L\.)\s*$',
            r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-&\.]{3,55}\s+S\.A\.S\.)\s*$',
            r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-&\.]{3,55}\s+S\.A\.)\s*$',
            r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-&\.]{3,55}\s+S\.C\.A\.)\s*$',
            r'^(COOPERATIVA\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-]{3,50}?)\s*$',
            r'^(U\.T\.E\.\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-]{3,50}?)\s*$',
            r'^(FUNDACI[ÓO]N\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-]{3,50}?)\s*$',
            r'^(ASOCIACI[ÓO]N\s+(?:CIVIL\s+)?[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-]{3,50}?)\s*$',
            r'^(CONSORCIO\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-&\.]{3,50}?)\s*$',
        ]

        # Patrones para contratos/licitaciones
        self.contrato_patterns = [
            r'LICITACI[ÓO]N\s+(?:P[ÚU]BLICA\s+)?N[°º]?\s*(\d+/\d{4})',
            r'EXPEDIENTE\s+N[°º]?\s*([\d\-/]+)',
            r'CONTRATO\s+N[°º]?\s*(\d+/\d{4})',
            r'CONCURSO\s+P[ÚU]BLICO\s+N[°º]?\s*(\d+)'
        ]

        # Patrones para montos
        self.monto_patterns = [
            r'\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            r'PESOS\s+(\d{1,3}(?:\.\d{3})*)',
            r'SUMA\s+DE\s+\$?\s*(\d{1,3}(?:\.\d{3})*)',
            r'MONTO\s+(?:TOTAL\s+)?DE\s+\$?\s*(\d{1,3}(?:\.\d{3})*)',
            r'POR\s+UN\s+IMPORTE\s+DE\s+\$?\s*(\d{1,3}(?:\.\d{3})*)'
        ]
    
    def extract_entities(self, text: str) -> List[EntityResult]:
        """
        Extrae todas las entidades del texto
        
        Args:
            text: Texto completo del boletín
            
        Returns:
            Lista de EntityResult con todas las entidades encontradas
        """
        entities = []
        
        # Extraer cada tipo de entidad
        entities.extend(self._extract_personas(text))
        entities.extend(self._extract_organismos(text))
        entities.extend(self._extract_empresas(text))
        entities.extend(self._extract_contratos(text))
        entities.extend(self._extract_montos(text))
        
        return entities
    
    def _extract_personas(self, text: str) -> List[EntityResult]:
        """
        Extrae personas mencionadas.

        Se usa sin IGNORECASE: los prefijos (SR., DNI, DESIGNAR, A FAVOR DE)
        aparecen en MAYÚSCULAS en texto oficial, y los nombres propios tienen
        capitalización Proper Case. Usar IGNORECASE convertiría cualquier palabra
        en minúscula en un falso positivo.
        """
        results = []

        for pattern in self.persona_patterns:
            for match in re.finditer(pattern, text):  # sin re.IGNORECASE
                nombre = self._clean_name(match.group(1).strip(), max_len=60)

                _BLOCKED = {
                    'DNI', 'CUIL', 'CUIT', 'DRA', 'DR', 'SR', 'SRA', 'LIC',
                    'ING', 'PROF', 'MZA', 'ESQ', 'ART', 'INC', 'FDO', 'EXP',
                    'CIV', 'Dra', 'Dr', 'Sr', 'Sra', 'Lic', 'Ing', 'Prof',
                    'Jefa', 'Jefe', 'Juez', 'Jueza', 'Mza', 'Civ',
                }
                words = nombre.split()
                # Mínimo 2 palabras
                if len(words) < 2:
                    continue
                # Cada palabra debe empezar con mayúscula
                if not all(w[0].isupper() for w in words if w):
                    continue
                # Ninguna palabra puede ser un título/abreviatura no-nombre
                if any(w in _BLOCKED for w in words):
                    continue
                # La última palabra no puede ser truncada (mín 3 chars)
                if len(words[-1]) < 3:
                    continue
                # Rechazar nombres muy cortos en total
                if len(nombre) < 8:
                    continue

                contexto = self._get_context(text, match.start(), match.end())
                results.append(EntityResult(
                    tipo='persona',
                    nombre=nombre,
                    nombre_normalizado=self.normalize_entity(nombre, 'persona'),
                    variantes=self._generate_variants(nombre),
                    contexto=contexto,
                    posicion=match.start(),
                    confianza=0.9,
                    metadata={}
                ))

        return self._deduplicate_entities(results)
    
    def _extract_organismos(self, text: str) -> List[EntityResult]:
        """Extrae organismos gubernamentales desde líneas ALL-CAPS (alta precisión)."""
        results = []
        seen_norms: set = set()

        for pattern in self.organismo_caps_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                nombre = match.group(1).strip()
                if len(nombre) < 8:
                    continue
                # Rechazar si contiene letras minúsculas (captura de columna mezclada)
                if re.search(r'[a-z]', nombre):
                    continue
                norm = self.normalize_entity(nombre, 'organismo')
                if norm in seen_norms:
                    continue
                seen_norms.add(norm)
                contexto = self._get_context(text, match.start(), match.end())
                results.append(EntityResult(
                    tipo='organismo',
                    nombre=nombre,
                    nombre_normalizado=norm,
                    variantes=self._generate_variants(nombre),
                    contexto=contexto,
                    posicion=match.start(),
                    confianza=1.0,
                    metadata={}
                ))

        return results
    
    def _extract_empresas(self, text: str) -> List[EntityResult]:
        """Extrae empresas desde líneas ALL-CAPS que terminan con sufijo societario."""
        results = []
        seen_norms: set = set()

        for pattern in self.empresa_caps_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                nombre = match.group(1).strip()
                if len(nombre) < 5:
                    continue
                # Rechazar si contiene letras minúsculas (captura de columna mezclada)
                if re.search(r'[a-z]', nombre):
                    continue
                norm = self.normalize_entity(nombre, 'empresa')
                if norm in seen_norms:
                    continue
                seen_norms.add(norm)
                contexto = self._get_context(text, match.start(), match.end())
                results.append(EntityResult(
                    tipo='empresa',
                    nombre=nombre,
                    nombre_normalizado=norm,
                    variantes=self._generate_variants(nombre),
                    contexto=contexto,
                    posicion=match.start(),
                    confianza=0.95,
                    metadata={}
                ))

        return results
    
    def _extract_contratos(self, text: str) -> List[EntityResult]:
        """Extrae contratos y licitaciones"""
        results = []
        
        for pattern in self.contrato_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                nombre = match.group(0).strip()
                contexto = self._get_context(text, match.start(), match.end())
                
                results.append(EntityResult(
                    tipo='contrato',
                    nombre=nombre,
                    nombre_normalizado=self.normalize_entity(nombre, 'contrato'),
                    variantes=[nombre],
                    contexto=contexto,
                    posicion=match.start(),
                    confianza=1.0,
                    metadata={'numero': match.group(1) if match.groups() else None}
                ))
        
        return results
    
    def _extract_montos(self, text: str) -> List[EntityResult]:
        """Extrae montos mencionados"""
        results = []
        seen_amounts = set()
        
        for pattern in self.monto_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                monto_str = match.group(0).strip()
                monto_numerico = self._parse_amount(match.group(1))
                
                # Evitar duplicados por monto
                if monto_numerico in seen_amounts or monto_numerico < 1000:
                    continue
                
                seen_amounts.add(monto_numerico)
                contexto = self._get_context(text, match.start(), match.end())
                
                results.append(EntityResult(
                    tipo='monto',
                    nombre=monto_str,
                    nombre_normalizado=f"${monto_numerico:,.0f}",
                    variantes=[monto_str],
                    contexto=contexto,
                    posicion=match.start(),
                    confianza=1.0,
                    metadata={'valor_numerico': monto_numerico}
                ))
        
        return sorted(results, key=lambda x: x.metadata.get('valor_numerico', 0), reverse=True)[:50]
    
    def _parse_amount(self, amount_str: str) -> float:
        """Convierte string de monto a número"""
        try:
            clean = amount_str.replace('.', '').replace(',', '.')
            return float(clean)
        except Exception:
            return 0.0
    
    def _clean_name(self, nombre: str, max_len: int = 80) -> str:
        """Limpia un nombre de entidad extraído de PDF: quita saltos de línea y texto basura."""
        # Unir palabras con guion al final de línea: "Huma-\nnidades" → "Humanidades"
        nombre = re.sub(r'-\s*\n\s*', '', nombre)
        # Reemplazar cualquier newline/tab restante por espacio
        nombre = re.sub(r'[\n\r\t]+', ' ', nombre)
        # Normalizar espacios múltiples
        nombre = re.sub(r'\s+', ' ', nombre).strip()
        # Truncar nombres excesivamente largos (probablemente capturas erróneas)
        if len(nombre) > max_len:
            # Cortar en el primer separador natural después del mínimo aceptable
            for sep in (' DE ', ' LA ', ' EL ', ' Y ', ',', ';'):
                idx = nombre.find(sep, 20)
                if 20 <= idx <= max_len:
                    nombre = nombre[:idx].strip()
                    break
            else:
                nombre = nombre[:max_len].strip()
        return nombre

    def _get_context(self, text: str, start: int, end: int, window: int = 150) -> str:
        """Obtiene contexto alrededor de una posición"""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end].strip()
    
    def _generate_variants(self, nombre: str) -> List[str]:
        """Genera variantes de un nombre para matching"""
        variants = [nombre]
        
        # Sin acentos
        variants.append(self._remove_accents(nombre))
        
        # Mayúsculas/minúsculas
        variants.append(nombre.upper())
        variants.append(nombre.title())
        
        # Sin puntos
        variants.append(nombre.replace('.', ''))
        
        return list(set(variants))
    
    def _remove_accents(self, text: str) -> str:
        """Remueve acentos de un texto"""
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
    
    def normalize_entity(self, nombre: str, tipo: str) -> str:
        """Normaliza nombre de entidad para deduplicación"""
        # Remover acentos, convertir a mayúsculas, remover espacios extras
        normalized = self._remove_accents(nombre.upper().strip())
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remover puntos en abreviaturas
        normalized = normalized.replace('.', '')
        
        return normalized
    
    def _deduplicate_entities(self, entities: List[EntityResult]) -> List[EntityResult]:
        """Elimina entidades duplicadas basándose en nombre normalizado"""
        seen = {}
        unique = []
        
        for entity in entities:
            if entity.nombre_normalizado not in seen:
                seen[entity.nombre_normalizado] = entity
                unique.append(entity)
        
        return unique
    
    def detect_relationships(self, entities: List[EntityResult], text: str) -> List[RelationshipResult]:
        """
        Detecta relaciones entre entidades usando bloques anclados a cabeceras ALL-CAPS.

        Estrategia: los PDFs del boletín son 2 columnas, lo que hace que los patrones
        cross-line sean poco fiables. En cambio, usamos los organismos detectados como
        anclas y buscamos relaciones dentro de una ventana de ~2000 chars desde cada uno.
        """
        relationships = []

        # Índice: organismos ordenados por posición
        org_list = sorted(
            [(e.posicion, e.nombre, e.nombre_normalizado) for e in entities if e.tipo == 'organismo'],
            key=lambda x: x[0]
        )

        for i, (org_pos, org_nombre, org_norm) in enumerate(org_list):
            # Bloque: desde este organismo hasta el siguiente (máx 2500 chars)
            next_pos = org_list[i + 1][0] if i + 1 < len(org_list) else org_pos + 2500
            block_end = min(next_pos, org_pos + 2500)
            block = text[org_pos:block_end]

            # --- designa: DESIGNAR A <Persona> ---
            for m in re.finditer(
                r'DESIGNAR?\s+(?:EN\s+EL\s+CARGO\s+)?A\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})',
                block, re.IGNORECASE
            ):
                persona = self._clean_name(m.group(1).strip(), max_len=60)
                if len(persona.split()) >= 2:
                    relationships.append(RelationshipResult(
                        entidad_origen=org_nombre,
                        entidad_destino=persona,
                        tipo_relacion='designa',
                        contexto=block[max(0, m.start() - 100):m.end() + 100],
                        confianza=0.85,
                        metadata={}
                    ))

            # --- contrata: keyword de adjudicación + empresa S.A./S.R.L. cercana ---
            for m in re.finditer(r'ADJUDIC[AÓ][RO]?|CONTRAT[ÓO]', block, re.IGNORECASE):
                sub = block[m.start():min(len(block), m.start() + 500)]
                m2 = re.search(
                    r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-&\.]{3,55}\s+(?:S\.A\.U?\.|S\.R\.L\.|S\.A\.S\.|S\.A\.))',
                    sub
                )
                if m2:
                    empresa = self._clean_name(m2.group(1).strip())
                    if not re.search(r'[a-z]', empresa):  # solo ALL-CAPS
                        relationships.append(RelationshipResult(
                            entidad_origen=org_nombre,
                            entidad_destino=empresa,
                            tipo_relacion='contrata',
                            contexto=sub[:300],
                            confianza=0.75,
                            metadata={}
                        ))
                        break  # una sola empresa por keyword de adjudicación

            # --- adjudica: adjudicación formal con "A FAVOR DE" ---
            for m in re.finditer(
                r'(?:ADJUDIC[AO]\s+(?:LA\s+)?LICITACI[OÓ]N|SE\s+ADJUDICA)[^\n]{0,250}?'
                r'A\s+(?:FAVOR\s+DE\s+)?'
                r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-&\.]{5,60}?'
                r'(?:S\.A\.U?\.|S\.R\.L\.|S\.A\.S\.|S\.A\.|COOPERATIVA|CONSORCIO|UTE))',
                block, re.IGNORECASE
            ):
                empresa = self._clean_name(m.group(1).strip())
                if not re.search(r'[a-z]', empresa):
                    relationships.append(RelationshipResult(
                        entidad_origen=org_nombre,
                        entidad_destino=empresa,
                        tipo_relacion='adjudica',
                        contexto=block[max(0, m.start() - 100):m.end() + 100],
                        confianza=0.85,
                        metadata={}
                    ))

            # --- autoriza: AUTORIZAR A <Persona> ---
            for m in re.finditer(
                r'AUTORIZAR?\s+(?:A\s+)?'
                r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})',
                block, re.IGNORECASE
            ):
                persona = self._clean_name(m.group(1).strip(), max_len=60)
                if len(persona.split()) >= 2:
                    relationships.append(RelationshipResult(
                        entidad_origen=org_nombre,
                        entidad_destino=persona,
                        tipo_relacion='autoriza',
                        contexto=block[max(0, m.start() - 100):m.end() + 100],
                        confianza=0.80,
                        metadata={}
                    ))

            # --- aprueba: APROBAR LA CONTRATACIÓN/LICITACIÓN ... A FAVOR DE ---
            for m in re.finditer(
                r'APROBAR?\s+(?:LA\s+)?(?:CONTRATACI[OÓ]N|LICITACI[OÓ]N|COMPRA)[^\n]{0,300}?'
                r'A\s+(?:FAVOR\s+DE\s+)?([A-ZÁÉÍÓÚÑ][^\n\.]{5,60})',
                block, re.IGNORECASE
            ):
                destino = self._clean_name(m.group(1).strip())
                if len(destino) >= 5:
                    relationships.append(RelationshipResult(
                        entidad_origen=org_nombre,
                        entidad_destino=destino,
                        tipo_relacion='aprueba',
                        contexto=block[max(0, m.start() - 100):m.end() + 100],
                        confianza=0.78,
                        metadata={}
                    ))

            # --- otorga: OTORGAR PERMISO/HABILITACIÓN/CONCESIÓN (no subsidio) ---
            for m in re.finditer(
                r'OTORGAR?\s+(?:UN\s+)?(?!SUBSIDIO)(?:PERMISO|HABILITACI[OÓ]N|CONCESI[OÓ]N)[^\n]{0,200}?'
                r'A\s+(?:FAVOR\s+DE\s+)?([A-ZÁÉÍÓÚÑ][^\n\.]{3,60})',
                block, re.IGNORECASE
            ):
                destino = self._clean_name(m.group(1).strip())
                if len(destino) >= 4:
                    relationships.append(RelationshipResult(
                        entidad_origen=org_nombre,
                        entidad_destino=destino,
                        tipo_relacion='otorga',
                        contexto=block[max(0, m.start() - 100):m.end() + 100],
                        confianza=0.75,
                        metadata={}
                    ))

            # --- firma: SUSCRIBIR/FIRMAR CONTRATO/CONVENIO CON <empresa> ---
            for m in re.finditer(
                r'(?:SUSCRIBIR?|FIRMAR?)\s+(?:EL\s+)?(?:CONTRATO|CONVENIO|ACUERDO)[^\n]{0,200}?'
                r'CON\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-&\.]{5,60}?'
                r'(?:S\.A\.U?\.|S\.R\.L\.|S\.A\.|FUNDACI[OÓ]N|ASOCIACI[OÓ]N))',
                block, re.IGNORECASE
            ):
                empresa = self._clean_name(m.group(1).strip())
                if not re.search(r'[a-z]', empresa):
                    relationships.append(RelationshipResult(
                        entidad_origen=org_nombre,
                        entidad_destino=empresa,
                        tipo_relacion='firma',
                        contexto=block[max(0, m.start() - 100):m.end() + 100],
                        confianza=0.82,
                        metadata={}
                    ))

            # --- recibe_subsidio: dentro del bloque del organismo ---
            for m in re.finditer(
                r'OTORGAR?\s+(?:UN\s+)?SUBSIDIO[^\n]{0,200}?'
                r'A\s+(?:FAVOR\s+DE\s+)?([A-ZÁÉÍÓÚÑ][^\n\.]{3,60})',
                block, re.IGNORECASE
            ):
                beneficiario = self._clean_name(m.group(1).strip())
                if len(beneficiario) > 5:
                    relationships.append(RelationshipResult(
                        entidad_origen=org_nombre,
                        entidad_destino=beneficiario,
                        tipo_relacion='recibe_subsidio',
                        contexto=block[max(0, m.start() - 100):m.end() + 100],
                        confianza=0.75,
                        metadata={}
                    ))

        return relationships
    
    def build_entity_map(self, entities: List[EntityResult], text: str) -> EntityMap:
        """Build a spatial EntityMap by locating each entity's position in text."""
        entity_map = EntityMap()
        text_lower = text.lower()
        for entity in entities:
            name = entity.nombre.lower()
            pos = 0
            while True:
                idx = text_lower.find(name, pos)
                if idx == -1:
                    break
                entity_map.add(idx, idx + len(name), entity)
                pos = idx + 1
        return entity_map

    async def persist_entities(
        self,
        entities: List[EntityResult],
        boletin_id: int,
        db: AsyncSession
    ) -> Dict[str, int]:
        """
        Persiste entidades en la base de datos
        
        Returns:
            Dict con estadísticas de creación/actualización
        """
        stats = {'created': 0, 'updated': 0, 'mentions': 0}
        
        # Obtener fecha del boletín
        boletin_result = await db.execute(
            select(Boletin).where(Boletin.id == boletin_id)
        )
        boletin = boletin_result.scalar_one_or_none()
        if not boletin:
            return stats
        
        fecha_boletin = datetime.strptime(boletin.date, '%Y%m%d').date()
        
        for entity in entities:
            # Buscar o crear entidad
            result = await db.execute(
                select(EntidadExtraida).where(
                    EntidadExtraida.nombre_normalizado == entity.nombre_normalizado
                )
            )
            entidad_db = result.scalar_one_or_none()
            
            if entidad_db:
                # Actualizar existente
                entidad_db.total_menciones += 1
                entidad_db.ultima_aparicion = fecha_boletin
                entidad_db.updated_at = datetime.utcnow()
                stats['updated'] += 1
            else:
                # Crear nueva
                entidad_db = EntidadExtraida(
                    tipo=entity.tipo,
                    nombre_normalizado=entity.nombre_normalizado,
                    nombre_display=entity.nombre,
                    variantes=entity.variantes,
                    primera_aparicion=fecha_boletin,
                    ultima_aparicion=fecha_boletin,
                    total_menciones=1,
                    metadata_extra=entity.metadata
                )
                db.add(entidad_db)
                stats['created'] += 1
            
            await db.flush()
            
            # Crear mención
            mencion = MencionEntidad(
                entidad_id=entidad_db.id,
                boletin_id=boletin_id,
                fragmento=entity.contexto[:500],
                confianza=entity.confianza
            )
            db.add(mencion)
            stats['mentions'] += 1
        
        await db.commit()

        # ---- Neo4j dual-write (no-fatal) ----
        try:
            from app.core.config import settings as _settings
            if _settings.neo4j_enabled:
                from app.db.neo4j_client import get_neo4j_session
                from app.services import graph_service
                async with get_neo4j_session() as neo:
                    await graph_service.upsert_boletin(
                        neo,
                        pg_id=boletin.id,
                        filename=boletin.filename,
                        date=boletin.date,
                    )
                    for entity in entities:
                        res = await db.execute(
                            select(EntidadExtraida).where(
                                EntidadExtraida.nombre_normalizado == entity.nombre_normalizado
                            )
                        )
                        e_db = res.scalar_one_or_none()
                        if e_db:
                            await graph_service.upsert_entity(
                                neo,
                                pg_id=e_db.id,
                                tipo=e_db.tipo,
                                nombre_normalizado=e_db.nombre_normalizado,
                                nombre_display=e_db.nombre_display,
                                variantes=e_db.variantes or [],
                                total_menciones=e_db.total_menciones,
                                primera_aparicion=e_db.primera_aparicion.isoformat() if e_db.primera_aparicion else None,
                                ultima_aparicion=e_db.ultima_aparicion.isoformat() if e_db.ultima_aparicion else None,
                                metadata_extra=e_db.metadata_extra,
                            )
        except Exception as neo_exc:
            logger.warning("Neo4j entity write failed (non-fatal): %s", neo_exc)
        # ---- fin dual-write ----

        return stats

    async def persist_relationships(
        self,
        relationships: List[RelationshipResult],
        boletin_id: int,
        entities: List[EntityResult],
        db: AsyncSession
    ) -> int:
        """
        Persiste relaciones entre entidades
        
        Returns:
            Número de relaciones creadas
        """
        # Obtener fecha del boletín
        boletin_result = await db.execute(
            select(Boletin).where(Boletin.id == boletin_id)
        )
        boletin = boletin_result.scalar_one_or_none()
        if not boletin:
            return 0
        
        fecha_boletin = datetime.strptime(boletin.date, '%Y%m%d').date()
        count = 0
        
        for rel in relationships:
            # Buscar entidades por nombre normalizado
            # Bug fix: origen vacío (ej. recibe_subsidio legacy) → saltar
            if not rel.entidad_origen:
                continue
            origen_norm = self.normalize_entity(rel.entidad_origen, 'organismo')

            origen_result = await db.execute(
                select(EntidadExtraida).where(
                    EntidadExtraida.nombre_normalizado == origen_norm
                )
            )
            origen_db = origen_result.scalar_one_or_none()

            # Bug fix: destino puede ser persona, empresa u organismo según el tipo
            destino_db = None
            destino_norm = None
            for guess_tipo in ('persona', 'empresa', 'organismo'):
                _norm = self.normalize_entity(rel.entidad_destino, guess_tipo)
                _res = await db.execute(
                    select(EntidadExtraida).where(
                        EntidadExtraida.nombre_normalizado == _norm
                    )
                )
                _db = _res.scalar_one_or_none()
                if _db:
                    destino_db = _db
                    destino_norm = _norm
                    break

            if origen_db and destino_db:
                # Crear relación
                relacion = RelacionEntidad(
                    entidad_origen_id=origen_db.id,
                    entidad_destino_id=destino_db.id,
                    tipo_relacion=rel.tipo_relacion,
                    boletin_id=boletin_id,
                    fecha_relacion=fecha_boletin,
                    contexto=rel.contexto[:500],
                    confianza=rel.confianza,
                    metadata_extra=rel.metadata
                )
                db.add(relacion)
                count += 1
        
        await db.commit()

        # ---- Neo4j dual-write (no-fatal) ----
        try:
            from app.core.config import settings as _settings
            if _settings.neo4j_enabled:
                from app.db.neo4j_client import get_neo4j_session
                from app.services import graph_service
                async with get_neo4j_session() as neo:
                    for rel in relationships:
                        if not rel.entidad_origen:
                            continue
                        origen_norm = self.normalize_entity(rel.entidad_origen, 'organismo')
                        # Resolver destino buscando en múltiples tipos (igual que PostgreSQL)
                        _destino_norm = None
                        for _guess in ('persona', 'empresa', 'organismo'):
                            _n = self.normalize_entity(rel.entidad_destino, _guess)
                            _r = await db.execute(
                                select(EntidadExtraida).where(EntidadExtraida.nombre_normalizado == _n)
                            )
                            if _r.scalar_one_or_none():
                                _destino_norm = _n
                                break
                        if not _destino_norm:
                            continue
                        rel_res = await db.execute(
                            select(RelacionEntidad)
                            .join(EntidadExtraida, RelacionEntidad.entidad_origen_id == EntidadExtraida.id)
                            .where(
                                EntidadExtraida.nombre_normalizado == origen_norm,
                                RelacionEntidad.boletin_id == boletin_id,
                                RelacionEntidad.tipo_relacion == rel.tipo_relacion,
                            )
                            .order_by(RelacionEntidad.id.desc())
                            .limit(1)
                        )
                        rel_db = rel_res.scalar_one_or_none()
                        if rel_db:
                            await graph_service.upsert_relationship(
                                neo,
                                origen_nombre_normalizado=origen_norm,
                                destino_nombre_normalizado=_destino_norm,
                                tipo_relacion=rel.tipo_relacion,
                                pg_id=rel_db.id,
                                boletin_pg_id=boletin_id,
                                fecha=fecha_boletin.isoformat(),
                                confianza=rel.confianza,
                                contexto=rel.contexto,
                                metadata_extra=rel.metadata,
                            )
        except Exception as neo_exc:
            logger.warning("Neo4j relationship write failed (non-fatal): %s", neo_exc)
        # ---- fin dual-write ----

        return count


# Instancia global del servicio
_entity_service: Optional[EntityService] = None


def get_entity_service() -> EntityService:
    """Obtiene instancia singleton del servicio"""
    global _entity_service
    if _entity_service is None:
        _entity_service = EntityService()
    return _entity_service

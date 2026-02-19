"""
Chunk Enricher Service - Enriquece chunks con metadata

Este servicio maneja:
- Detección de section_type (decreto, resolución, licitación, etc.)
- Detección de has_amounts (si contiene montos)
- Detección de has_tables (si contiene tablas)
- Extracción básica de entidades
"""

import logging
import re
import hashlib
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ChunkEnricher:
    """
    Servicio para enriquecer chunks con metadata.
    
    Analiza el contenido del chunk y extrae metadata útil para
    búsqueda y filtrado.
    """
    
    # Patrones para detectar section_type
    SECTION_PATTERNS = {
        "licitacion": [
            r"\blicitaci[oó]n\b",
            r"\bconcurso\s+de\s+precios\b",
            r"\badquisi[cz]i[oó]n\b",
            r"\bprovisi[oó]n\b",
        ],
        "decreto": [
            r"\bDECRETO\s+\d+",
            r"\bDecreto\s+N[°º]",
        ],
        "resolucion": [
            r"\bRESOLUCI[OÓ]N\s+\d+",
            r"\bResoluci[oó]n\s+N[°º]",
        ],
        "subsidio": [
            r"\bsubsidio\b",
            r"\bayuda\s+econ[oó]mica\b",
            r"\basistencia\s+financiera\b",
        ],
        "nombramiento": [
            r"\bdesign[aá]",
            r"\bnombramiento\b",
            r"\baprueba\s+la\s+designaci[oó]n\b",
        ],
        "presupuesto": [
            r"\bpresupuesto\b",
            r"\bpartida\s+presupuestaria\b",
            r"\bcr[eé]dito\s+presupuestario\b",
        ],
    }
    
    # Patrones para detectar montos
    AMOUNT_PATTERNS = [
        r"\$\s*\d+",  # $1000
        r"pesos\s+\d+",  # pesos 1000
        r"\d+\s*pesos",  # 1000 pesos
        r"\$\d+[\.,]\d+",  # $1,000.00
        r"ARS\s*\d+",  # ARS 1000
    ]
    
    # Patrones para detectar tablas (tabulación o alineación)
    TABLE_PATTERNS = [
        r"\t",  # Tab character
        r"\n\s{4,}\S",  # Multiple spaces at line start (indentation)
        r"\|\s*\w+\s*\|",  # Pipe-separated columns
    ]
    
    def __init__(self):
        """Inicializar ChunkEnricher."""
        # Compilar patrones para eficiencia
        self._section_patterns_compiled = {
            section: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for section, patterns in self.SECTION_PATTERNS.items()
        }
        
        self._amount_patterns_compiled = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.AMOUNT_PATTERNS
        ]
        
        self._table_patterns_compiled = [
            re.compile(pattern) for pattern in self.TABLE_PATTERNS
        ]
    
    def enrich(
        self,
        chunk_text: str,
        chunk_index: int,
        document_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enriquecer un chunk con metadata.
        
        Args:
            chunk_text: Texto del chunk
            chunk_index: Índice del chunk
            document_id: ID del documento
            context: Contexto adicional (ej: boletin_id, section info)
            
        Returns:
            Dict con metadata enriquecida
        """
        context = context or {}
        
        # Calcular hash del chunk
        chunk_hash = hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()
        
        # Detectar section_type
        section_type = self._detect_section_type(chunk_text)
        
        # Detectar has_amounts
        has_amounts = self._detect_amounts(chunk_text)
        
        # Detectar has_tables
        has_tables = self._detect_tables(chunk_text)
        
        # Extraer entidades básicas
        entities = self._extract_basic_entities(chunk_text)
        
        # Construir metadata
        metadata = {
            "document_id": document_id,
            "chunk_index": chunk_index,
            "chunk_hash": chunk_hash,
            "text": chunk_text,
            "num_chars": len(chunk_text),
            "section_type": section_type,
            "language": "es",  # Por defecto español
            "has_amounts": has_amounts,
            "has_tables": has_tables,
            "entities_json": entities if entities else None,
            # Context adicional
            "boletin_id": context.get("boletin_id"),
            "start_char": context.get("start_char"),
            "end_char": context.get("end_char"),
        }
        
        return metadata
    
    def _detect_section_type(self, text: str) -> str:
        """
        Detectar el tipo de sección basándose en keywords.
        
        Args:
            text: Texto del chunk
            
        Returns:
            Tipo de sección detectado o "general"
        """
        # Contar matches por cada tipo
        scores = {}
        
        for section_type, patterns in self._section_patterns_compiled.items():
            matches = 0
            for pattern in patterns:
                if pattern.search(text):
                    matches += 1
            if matches > 0:
                scores[section_type] = matches
        
        # Retornar el tipo con más matches
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return "general"
    
    def _detect_amounts(self, text: str) -> bool:
        """
        Detectar si el chunk contiene montos.
        
        Args:
            text: Texto del chunk
            
        Returns:
            True si contiene montos
        """
        for pattern in self._amount_patterns_compiled:
            if pattern.search(text):
                return True
        return False
    
    def _detect_tables(self, text: str) -> bool:
        """
        Detectar si el chunk contiene tablas.
        
        Args:
            text: Texto del chunk
            
        Returns:
            True si contiene tablas
        """
        for pattern in self._table_patterns_compiled:
            if pattern.search(text):
                return True
        return False
    
    def _extract_basic_entities(self, text: str) -> Optional[Dict[str, List[str]]]:
        """
        Extraer entidades básicas del chunk.
        
        Extracción simple basada en patrones. Para extracción más
        sofisticada, usar EntityService.
        
        Args:
            text: Texto del chunk
            
        Returns:
            Dict con listas de entidades por tipo, o None si no hay
        """
        entities = {
            "montos": [],
            "organismos": [],
            "personas": [],
        }
        
        # Extraer montos
        for pattern in self._amount_patterns_compiled:
            matches = pattern.findall(text)
            entities["montos"].extend(matches[:5])  # Limitar a 5
        
        # Extraer organismos (simple: palabras capitalizadas seguidas de keywords)
        org_pattern = re.compile(
            r"\b([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+)*)\s+(?:de|del|Provincia|Municipal)",
            re.UNICODE
        )
        org_matches = org_pattern.findall(text)
        entities["organismos"].extend(org_matches[:5])
        
        # Extraer personas (muy básico: patrón de nombre + apellido en mayúsculas)
        person_pattern = re.compile(
            r"\b([A-Z][a-záéíóúñ]+\s+[A-Z][a-záéíóúñ]+)\b",
            re.UNICODE
        )
        person_matches = person_pattern.findall(text)
        # Filtrar comunes que no son nombres
        stop_words = {"Boletín Oficial", "Provincia Córdoba", "Ciudad Córdoba"}
        person_matches = [p for p in person_matches if p not in stop_words]
        entities["personas"].extend(person_matches[:5])
        
        # Si no hay entidades, retornar None
        if not any(entities.values()):
            return None
        
        # Limpiar listas vacías
        entities = {k: v for k, v in entities.items() if v}
        
        return entities if entities else None


# Instancia global
_chunk_enricher: Optional[ChunkEnricher] = None


def get_chunk_enricher() -> ChunkEnricher:
    """
    Obtener instancia global de ChunkEnricher.
    
    Returns:
        Instancia de ChunkEnricher
    """
    global _chunk_enricher
    
    if _chunk_enricher is None:
        _chunk_enricher = ChunkEnricher()
    
    return _chunk_enricher

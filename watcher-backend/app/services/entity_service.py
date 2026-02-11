"""
Servicio unificado de extracción y persistencia de entidades
Consolida lógica dispersa en múltiples archivos para un sistema centralizado
"""

import re
import unicodedata
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date
from dataclasses import dataclass
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.dialects.sqlite import insert

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


class EntityService:
    """Servicio para extracción y persistencia de entidades"""
    
    def __init__(self):
        # Patrones para extracción de personas
        self.persona_patterns = [
            r'(?:SR\.|SRA\.|SE[ÑN]OR|SE[ÑN]ORA)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})',
            r'A\s+FAVOR\s+DE\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})',
            r'DESIGNAR\s+A\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})',
            r'D\.?N\.?I\.?\s+N[°º]?\s*[\d\.]+\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})'
        ]
        
        # Patrones para organismos
        self.organismo_patterns = [
            r'MINISTERIO\s+DE\s+([A-ZÁÉÍÓÚÑ][^\n\.,;]{5,60})',
            r'SECRETAR[ÍI]A\s+DE\s+([A-ZÁÉÍÓÚÑ][^\n\.,;]{5,60})',
            r'DIRECCI[ÓO]N\s+(?:GENERAL\s+)?DE\s+([A-ZÁÉÍÓÚÑ][^\n\.,;]{5,60})',
            r'SUBSECRETAR[ÍI]A\s+DE\s+([A-ZÁÉÍÓÚÑ][^\n\.,;]{5,60})',
            r'AGENCIA\s+([A-ZÁÉÍÓÚÑ][^\n\.,;]{5,60})',
            r'MUNICIPALIDAD\s+DE\s+([A-ZÁÉÍÓÚÑ][^\n\.,;]{3,40})'
        ]
        
        # Patrones para empresas
        self.empresa_patterns = [
            r'([A-ZÁÉÍÓÚÑ][^\n\.,;]{3,50})\s+S\.?A\.?(?:\s|$|\.)',
            r'([A-ZÁÉÍÓÚÑ][^\n\.,;]{3,50})\s+S\.?R\.?L\.?(?:\s|$|\.)',
            r'([A-ZÁÉÍÓÚÑ][^\n\.,;]{3,50})\s+S\.?A\.?S\.?(?:\s|$|\.)',
            r'CONSTRUCTORA\s+([A-ZÁÉÍÓÚÑ][^\n\.,;]{3,40})',
            r'EMPRESA\s+([A-ZÁÉÍÓÚÑ][^\n\.,;]{3,40})',
            r'COOPERATIVA\s+([A-ZÁÉÍÓÚÑ][^\n\.,;]{3,40})',
            r'U\.?T\.?E\.?\s+([A-ZÁÉÍÓÚÑ][^\n\.,;]{3,40})'
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
        
        # Patrones para relaciones
        self.relacion_patterns = {
            'contrata': [
                r'(MINISTERIO\s+DE\s+[^\n\.]{5,60})[^\n]{1,100}((?:[A-Z][^\n\.]{3,50})\s+S\.?[AR]\.?L?\.?)',
                r'(SECRETAR[ÍI]A\s+DE\s+[^\n\.]{5,60})[^\n]{1,100}CONTRAT[ÓO]\s+A\s+([A-Z][^\n\.]{3,50})'
            ],
            'designa': [
                r'(MINISTERIO\s+DE\s+[^\n\.]{5,60})[^\n]{1,100}DESIGNAR?\s+A\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
                r'(SECRETAR[ÍI]A\s+DE\s+[^\n\.]{5,60})[^\n]{1,100}(?:SR\.|SRA\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})'
            ],
            'adjudica': [
                r'ADJUDICAR[^\n]{1,100}((?:[A-Z][^\n\.]{3,50})\s+S\.?[AR]\.?L?\.?)',
                r'(LICITACI[ÓO]N[^\n]{1,100})((?:[A-Z][^\n\.]{3,50})\s+S\.?[AR]\.?L?\.?)'
            ]
        }
    
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
        """Extrae personas mencionadas"""
        results = []
        
        for pattern in self.persona_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                nombre = match.group(1).strip()
                
                # Validar que tenga al menos 2 palabras
                if len(nombre.split()) < 2:
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
        """Extrae organismos gubernamentales"""
        results = []
        
        for pattern in self.organismo_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                nombre = match.group(0).strip()
                contexto = self._get_context(text, match.start(), match.end())
                
                results.append(EntityResult(
                    tipo='organismo',
                    nombre=nombre,
                    nombre_normalizado=self.normalize_entity(nombre, 'organismo'),
                    variantes=self._generate_variants(nombre),
                    contexto=contexto,
                    posicion=match.start(),
                    confianza=1.0,
                    metadata={}
                ))
        
        return self._deduplicate_entities(results)
    
    def _extract_empresas(self, text: str) -> List[EntityResult]:
        """Extrae empresas mencionadas"""
        results = []
        
        for pattern in self.empresa_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                nombre = match.group(0).strip()
                contexto = self._get_context(text, match.start(), match.end())
                
                results.append(EntityResult(
                    tipo='empresa',
                    nombre=nombre,
                    nombre_normalizado=self.normalize_entity(nombre, 'empresa'),
                    variantes=self._generate_variants(nombre),
                    contexto=contexto,
                    posicion=match.start(),
                    confianza=0.95,
                    metadata={}
                ))
        
        return self._deduplicate_entities(results)
    
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
        except:
            return 0.0
    
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
        Detecta relaciones entre entidades basándose en contexto
        
        Args:
            entities: Lista de entidades extraídas
            text: Texto completo
            
        Returns:
            Lista de RelationshipResult con relaciones detectadas
        """
        relationships = []
        
        # Buscar cada tipo de relación
        for tipo_rel, patterns in self.relacion_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
                    if len(match.groups()) >= 2:
                        origen = match.group(1).strip()
                        destino = match.group(2).strip()
                        contexto = self._get_context(text, match.start(), match.end(), 200)
                        
                        relationships.append(RelationshipResult(
                            entidad_origen=origen,
                            entidad_destino=destino,
                            tipo_relacion=tipo_rel,
                            contexto=contexto,
                            confianza=0.8,
                            metadata={}
                        ))
        
        return relationships
    
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
            origen_norm = self.normalize_entity(rel.entidad_origen, 'organismo')
            destino_norm = self.normalize_entity(rel.entidad_destino, 'empresa')
            
            origen_result = await db.execute(
                select(EntidadExtraida).where(
                    EntidadExtraida.nombre_normalizado == origen_norm
                )
            )
            origen_db = origen_result.scalar_one_or_none()
            
            destino_result = await db.execute(
                select(EntidadExtraida).where(
                    EntidadExtraida.nombre_normalizado == destino_norm
                )
            )
            destino_db = destino_result.scalar_one_or_none()
            
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
        return count


# Instancia global del servicio
_entity_service: Optional[EntityService] = None


def get_entity_service() -> EntityService:
    """Obtiene instancia singleton del servicio"""
    global _entity_service
    if _entity_service is None:
        _entity_service = EntityService()
    return _entity_service

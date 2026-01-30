"""
🔍 WATCHER ENTITY EXTRACTOR
Extractor mejorado de entidades para análisis de transparencia gubernamental
Evolución de la clase original del notebook con nuevas features
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import EXTRACTION_CONFIG, TRANSPARENCY_CONFIG

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ExtractedEntity:
    """Clase para representar una entidad extraída"""
    type: str
    value: str
    confidence: float
    position: int
    context: str = ""
    
@dataclass
class ExtractionResult:
    """Resultado completo de extracción"""
    amounts: List[ExtractedEntity]
    entities: List[ExtractedEntity]
    risk_classification: str
    risk_scores: Dict[str, int]
    risk_keywords: Dict[str, List[str]]
    transparency_score: float
    act_type: str
    act_confidence: float
    # Nuevas features
    contexto_transparente: bool
    justificacion_detectada: str
    num_keywords_riesgo: int
    tipo_evento: str

class WatcherEntityExtractor:
    """
    Extractor avanzado de entidades con nuevas capabilities para mayor precisión
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializa el extractor con configuración personalizable
        """
        self.config = config or EXTRACTION_CONFIG
        self.transparency_config = TRANSPARENCY_CONFIG
        
        # Patterns originales
        self.amount_patterns = self.config['amount_patterns']
        self.entity_patterns = self.config['entity_patterns']
        self.risk_keywords = self.config['risk_keywords']
        
        # Nuevos patterns para features mejoradas
        self.transparency_keywords = self.config.get('transparency_keywords', {})
        
        # Compiled regex para performance
        self._compile_patterns()
        
        logger.info("WatcherEntityExtractor inicializado con configuración mejorada")
    
    def _compile_patterns(self):
        """Precompila patterns regex para mejor performance"""
        self.compiled_amount_patterns = [re.compile(pattern, re.IGNORECASE) 
                                       for pattern in self.amount_patterns]
        self.compiled_entity_patterns = [re.compile(pattern, re.IGNORECASE) 
                                       for pattern in self.entity_patterns]
    
    def extract_amounts(self, text: str) -> List[ExtractedEntity]:
        """
        Extrae montos del texto con información adicional
        """
        amounts = []
        
        for i, pattern in enumerate(self.compiled_amount_patterns):
            matches = pattern.finditer(text)
            for match in matches:
                # Extraer contexto alrededor del monto
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                amount = ExtractedEntity(
                    type="amount",
                    value=match.group(1) if match.groups() else match.group(0),
                    confidence=self._calculate_amount_confidence(match.group(0), context),
                    position=match.start(),
                    context=context
                )
                amounts.append(amount)
        
        return amounts
    
    def _calculate_amount_confidence(self, amount_text: str, context: str) -> float:
        """Calcula confianza de extracción de monto basado en contexto"""
        confidence = 0.5  # Base confidence
        
        # Aumentar confianza si está bien formateado
        if re.match(r'\$\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?', amount_text):
            confidence += 0.3
        
        # Aumentar confianza si hay contexto de transacción
        transaction_words = ['pago', 'transferencia', 'subsidio', 'contrato', 'adjudicación']
        for word in transaction_words:
            if word.lower() in context.lower():
                confidence += 0.1
                break
        
        return min(1.0, confidence)
    
    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """
        Extrae entidades (beneficiarios, organizaciones) del texto
        """
        entities = []
        
        for i, pattern in enumerate(self.compiled_entity_patterns):
            matches = pattern.finditer(text)
            for match in matches:
                # Extraer contexto
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end]
                
                entity = ExtractedEntity(
                    type="entity",
                    value=match.group(1).strip() if match.groups() else match.group(0),
                    confidence=self._calculate_entity_confidence(match.group(0), context),
                    position=match.start(),
                    context=context
                )
                entities.append(entity)
        
        return entities
    
    def _calculate_entity_confidence(self, entity_text: str, context: str) -> float:
        """Calcula confianza de extracción de entidad"""
        confidence = 0.6  # Base confidence
        
        # Aumentar confianza si está en mayúsculas (formato oficial)
        if entity_text.isupper():
            confidence += 0.2
        
        # Aumentar confianza si tiene palabras clave organizacionales
        org_words = ['S.A.', 'S.R.L.', 'COOPERATIVA', 'FUNDACIÓN', 'EMPRESA']
        for word in org_words:
            if word in entity_text.upper():
                confidence += 0.1
                break
        
        return min(1.0, confidence)
    
    def classify_risk(self, text: str) -> Tuple[str, Dict[str, int], Dict[str, List[str]]]:
        """
        Clasifica el nivel de riesgo con análisis mejorado
        """
        text_lower = text.lower()
        risk_scores = {'ALTO': 0, 'MEDIO': 0, 'BAJO': 0}
        found_keywords = {'ALTO': [], 'MEDIO': [], 'BAJO': []}
        
        # Análisis por keywords existente
        for risk_level, keywords in self.risk_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    # Verificar contexto para evitar falsos positivos
                    if self._verify_keyword_context(keyword, text_lower):
                        risk_scores[risk_level] += 1
                        found_keywords[risk_level].append(keyword)
        
        # Determinar clasificación final con lógica mejorada
        max_score = max(risk_scores.values())
        if max_score == 0:
            classification = 'MEDIO'  # Default conservador
        else:
            classification = max(risk_scores.keys(), key=lambda k: risk_scores[k])
            
            # Ajustar clasificación si hay evidencia de transparencia
            if self._has_transparency_evidence(text_lower) and classification == 'ALTO':
                classification = 'MEDIO'  # Downgrade por transparencia
        
        return classification, risk_scores, found_keywords
    
    def _verify_keyword_context(self, keyword: str, text: str) -> bool:
        """
        Verifica el contexto alrededor de una keyword para evitar falsos positivos
        """
        # Encontrar todas las posiciones de la keyword
        positions = [m.start() for m in re.finditer(re.escape(keyword.lower()), text)]
        
        for pos in positions:
            # Extraer contexto alrededor
            start = max(0, pos - 100)
            end = min(len(text), pos + len(keyword) + 100)
            context = text[start:end]
            
            # Verificar si el contexto sugiere uso genuino
            if keyword in ['urgencia', 'emergencia']:
                # No es urgencia real si se menciona planificación
                if any(word in context for word in ['planificación', 'programada', 'prevista']):
                    continue
            
            elif keyword in ['excepción', 'directa']:
                # No es excepción problemática si está justificada
                if any(word in context for word in ['justificada', 'fundamentada', 'legal']):
                    continue
            
            return True  # Keyword genuina encontrada
        
        return False  # Todas las instancias son contexto dudoso
    
    def _has_transparency_evidence(self, text: str) -> bool:
        """
        Detecta evidencia de transparencia en el texto
        """
        transparency_evidence = [
            'licitación pública', 'concurso', 'proceso competitivo',
            'registro público', 'transparencia', 'normativa aplicable',
            'decreto', 'resolución', 'marco legal'
        ]
        
        evidence_count = sum(1 for evidence in transparency_evidence 
                           if evidence in text)
        
        return evidence_count >= 2  # Al menos 2 evidencias
    
    def calculate_transparency_score(self, text: str, risk_analysis: Dict, 
                                   amounts: List[ExtractedEntity]) -> float:
        """
        Calcula score de transparencia mejorado
        """
        score = self.transparency_config['base_score']
        
        # Penalizar por riesgo
        risk_level = risk_analysis.get('classification', 'MEDIO')
        score += self.transparency_config['risk_penalties'].get(risk_level, 0)
        
        # Bonificar por montos específicos
        if len(amounts) > 0:
            score += self.transparency_config['amount_bonus']
        
        # Analizar keywords de transparencia vs opacidad
        text_lower = text.lower()
        
        transparency_words = self.transparency_keywords.get('POSITIVE', [])
        opacity_words = self.transparency_keywords.get('NEGATIVE', [])
        
        for word in transparency_words:
            if word.lower() in text_lower:
                score += self.transparency_config['transparency_bonus']
        
        for word in opacity_words:
            if word.lower() in text_lower:
                score += self.transparency_config['opacity_penalty']
        
        # Bonus por estructura legal detectada
        legal_structure_bonus = self._detect_legal_structure(text_lower)
        score += legal_structure_bonus
        
        # Clamp entre min y max
        return max(self.transparency_config['min_score'], 
                  min(self.transparency_config['max_score'], score))
    
    def _detect_legal_structure(self, text: str) -> float:
        """
        Detecta estructura legal formal en el documento
        """
        legal_patterns = [
            r'artículo\s+\d+',
            r'inciso\s+[a-z]\)',
            r'decreto\s+\d+',
            r'resolución\s+\d+',
            r'ley\s+\d+',
            r'considerando\s+que',
            r'por\s+tanto'
        ]
        
        bonus = 0
        for pattern in legal_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                bonus += 3  # 3 puntos por cada estructura legal
        
        return min(15, bonus)  # Max 15 puntos de bonus
    
    def extract_new_features(self, text: str) -> Dict[str, any]:
        """
        Extrae las nuevas features sugeridas en el prompt
        """
        text_lower = text.lower()
        
        # Feature: contexto_transparente
        transparency_mentions = sum(1 for word in ['norma', 'decreto', 'licitación', 'resolución', 'registro']
                                  if word in text_lower)
        contexto_transparente = transparency_mentions >= 1
        
        # Feature: justificacion_detectada
        justificacion = self._detect_justification(text)
        
        # Feature: num_keywords_riesgo
        num_keywords_riesgo = sum(len(keywords) for keywords in 
                                self.classify_risk(text)[2].values())
        
        # Feature: tipo_evento
        tipo_evento = self._classify_event_type(text)
        
        return {
            'contexto_transparente': contexto_transparente,
            'justificacion_detectada': justificacion,
            'num_keywords_riesgo': num_keywords_riesgo,
            'tipo_evento': tipo_evento,
            'transparency_mentions': transparency_mentions
        }
    
    def _detect_justification(self, text: str) -> str:
        """
        Detecta si hay justificación en el documento
        """
        positive_patterns = [
            r"en virtud de", r"considerando", r"por cuanto", 
            r"atento a", r"fundamentado en", r"en base a"
        ]
        
        negative_patterns = [
            r"sin justificación", r"sin fundamento", r"sin explicación"
        ]
        
        text_lower = text.lower()
        
        # Buscar justificaciones positivas
        positive_count = sum(1 for pattern in positive_patterns 
                           if re.search(pattern, text_lower))
        
        # Buscar indicadores negativos
        negative_count = sum(1 for pattern in negative_patterns 
                           if re.search(pattern, text_lower))
        
        if positive_count >= 2:
            return "clara"
        elif positive_count >= 1 and negative_count == 0:
            return "parcial"
        elif negative_count > 0:
            return "ausente"
        else:
            return "ambigua"
    
    def _classify_event_type(self, text: str) -> str:
        """
        Clasifica el tipo de evento administrativo
        """
        event_patterns = {
            'DESIGNACION': ['design', 'nombr', 'cargo', 'función', 'puesto'],
            'SUBSIDIO': ['subsid', 'transfer', 'ayuda', 'apoyo económico'],
            'OBRA_PUBLICA': ['obra', 'construcción', 'infraestructura', 'proyecto'],
            'CONTRATACION': ['contrat', 'licit', 'proveedor', 'servicio'],
            'CONVENIO': ['convenio', 'acuerdo', 'alianza', 'cooperación']
        }
        
        text_lower = text.lower()
        scores = {}
        
        for event_type, keywords in event_patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[event_type] = score
        
        if max(scores.values()) == 0:
            return 'OTROS'
        
        return max(scores.keys(), key=lambda k: scores[k])
    
    def extract_complete(self, text: str) -> ExtractionResult:
        """
        Extracción completa con todas las features
        """
        # Extracciones básicas
        amounts = self.extract_amounts(text)
        entities = self.extract_entities(text)
        
        # Análisis de riesgo
        risk_classification, risk_scores, risk_keywords = self.classify_risk(text)
        
        # Score de transparencia
        transparency_score = self.calculate_transparency_score(
            text, {'classification': risk_classification}, amounts
        )
        
        # Tipo de acto (compatibilidad con código anterior)
        act_type = self._classify_event_type(text)
        act_confidence = max(risk_scores.values()) if risk_scores else 0
        
        # Nuevas features
        new_features = self.extract_new_features(text)
        
        return ExtractionResult(
            amounts=amounts,
            entities=entities,
            risk_classification=risk_classification,
            risk_scores=risk_scores,
            risk_keywords=risk_keywords,
            transparency_score=transparency_score,
            act_type=act_type,
            act_confidence=act_confidence,
            contexto_transparente=new_features['contexto_transparente'],
            justificacion_detectada=new_features['justificacion_detectada'],
            num_keywords_riesgo=new_features['num_keywords_riesgo'],
            tipo_evento=new_features['tipo_evento']
        )

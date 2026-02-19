"""
Servicio para análisis de contenido usando Google Gemini - v2 con structured output y multi-acto
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional
import google.generativeai as genai
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# JSON Schema for Gemini structured output
FRAGMENT_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "actos": {
            "type": "array",
            "description": "Lista de actos administrativos identificados en el fragmento",
            "items": {
                "type": "object",
                "properties": {
                    "tipo_acto": {
                        "type": "string",
                        "enum": ["decreto", "resolucion", "licitacion", "designacion", "subsidio", "transferencia", "otro"],
                        "description": "Tipo de acto administrativo"
                    },
                    "numero": {
                        "type": "string",
                        "description": "Numero o codigo del acto tal como aparece en el documento. Ej: '2025/RSIHG-00000737', 'Resolución N° 1813', 'Decreto 456/2025'"
                    },
                    "organismo": {
                        "type": "string",
                        "description": "Organismo emisor del acto"
                    },
                    "beneficiarios": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Personas, empresas o entidades beneficiarias"
                    },
                    "montos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Montos mencionados en el acto, tal como aparecen en el texto"
                    },
                    "monto_total_numerico": {
                        "type": "number",
                        "description": "Suma total en pesos argentinos (valor numerico) de todos los montos del acto. 0 si no hay montos. Ej: para 'pesos 3.010.523.733,29' devolver 3010523733.29"
                    },
                    "descripcion": {
                        "type": "string",
                        "description": "Resumen breve del acto (max 200 caracteres)"
                    },
                    "texto_original": {
                        "type": "string",
                        "description": "Cita textual de las primeras 2-3 lineas del acto tal como aparecen en el documento original. Maximo 300 caracteres. Debe ser unica para cada acto."
                    },
                    "riesgo": {
                        "type": "string",
                        "enum": ["alto", "medio", "bajo", "informativo"],
                        "description": "Nivel de riesgo segun las reglas de evaluacion del prompt"
                    },
                    "motivo_riesgo": {
                        "type": "string",
                        "description": "Justificacion del nivel de riesgo asignado"
                    },
                    "accion_sugerida": {
                        "type": "string",
                        "description": "Accion recomendada para seguimiento"
                    }
                },
                "required": ["tipo_acto", "organismo", "descripcion", "riesgo", "monto_total_numerico", "texto_original"]
            }
        },
        "resumen_general": {
            "type": "string",
            "description": "Resumen general del fragmento analizado (1-2 oraciones)"
        }
    },
    "required": ["actos", "resumen_general"]
}


class WatcherService:
    """Servicio de análisis de contenido con Google Gemini - v2 structured output."""
    
    def __init__(self):
        """Inicializa el servicio con configuración optimizada."""
        api_key = os.getenv('GOOGLE_API_KEY')
        
        # Inicializar cliente solo si hay API key, sino usar fallback
        self.model = None
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel("gemini-2.0-flash")
                logger.info("Google Gemini client inicializado correctamente")
            except Exception as e:
                logger.error(f"Error inicializando Gemini: {e}")
                self.model = None
        else:
            logger.warning(
                "GOOGLE_API_KEY no encontrada - el servicio funcionará con respuestas fallback. "
                "Para habilitar análisis con Google Gemini, configura GOOGLE_API_KEY en .env"
            )
        
        # Configuración optimizada
        self.model_name = "gemini-2.0-flash"
        self.max_tokens_per_request = 8000  # Chunks más grandes para capturar actos completos
        self.max_tokens_per_minute = 1000000
        self.requests_per_minute = 60
        
        # Control de rate limiting
        self.request_timestamps: List[datetime] = []
        self.tokens_used_this_minute = 0
        self.last_minute_reset = datetime.now()
        
        # System prompt v3: multi-acto, calibración de riesgo por montos, texto_original
        self.system_prompt = """Eres un analista experto en gobierno abierto y transparencia del sector público argentino.
Trabajas para Watcher, una plataforma de monitoreo ciudadano que mapea el gasto público y detecta irregularidades.

Tu tarea es analizar fragmentos de boletines oficiales y extraer TODOS los actos administrativos que encuentres.

Para CADA acto identificado, debes:
1. Clasificar su tipo (decreto, resolución, licitación, designación, subsidio, transferencia, otro)
2. Extraer el número/código del acto exactamente como aparece (ej: "2025/RSIHG-00000737", "Decreto 456/2025")
3. Identificar el organismo emisor
4. Listar beneficiarios (personas, empresas, entidades)
5. Extraer TODOS los montos mencionados como texto Y calcular el monto_total_numerico en pesos
6. Citar el texto_original: las primeras 2-3 líneas del acto tal como aparecen en el documento (max 300 chars, debe ser UNICA para cada acto)
7. Resumir brevemente el contenido

EVALUACION DE RIESGO - Reglas obligatorias:

Nivel "informativo": actos sin montos significativos Y sin indicadores (designaciones estándar, edictos, notificaciones, aprobaciones de planes).

Nivel "bajo": OBLIGATORIO cuando se cumple AL MENOS UNA condición:
- Monto total >= $100.000.000 (cien millones de pesos) aunque el procedimiento sea normal
- Licitaciones públicas con presupuesto oficial declarado
- Adjudicaciones regulares

Nivel "medio": OBLIGATORIO cuando se cumple AL MENOS UNA condición:
- Monto total >= $1.000.000.000 (mil millones de pesos)
- Contratación directa con monto >= $50.000.000
- Plazos inusualmente cortos para la magnitud del monto
- Falta de detalle en la descripción del objeto de contratación respecto al monto
- Modificaciones de contrato que incrementan montos significativamente

Nivel "alto": cuando hay señales claras de posible irregularidad:
- Contratación directa con montos superiores a $500.000.000 sin justificación de urgencia
- Fraccionamiento aparente (múltiples contratos similares para evitar licitación)
- Conflicto de intereses identificable
- Sobrecostos evidentes respecto a valores de mercado

EJEMPLOS de calibración:
- Licitación pública con presupuesto $3.000.000.000 -> "bajo" (procedimiento correcto pero monto alto, merece seguimiento)
- Contratación directa por $200.000.000 -> "medio" (monto alto sin licitación competitiva)
- Designación de cargo sin monto -> "informativo"
- Edicto de notificación -> "informativo"
- Subasta electrónica por $19.000.000 -> "informativo" (monto bajo, procedimiento competitivo)
- Licitación pública con presupuesto $198.000.000 -> "bajo" (supera umbral de $100M)

Siempre incluye motivo_riesgo y accion_sugerida, incluso para riesgo "bajo" (ej: "Verificar ejecución del contrato").
"""

    def count_tokens_estimate(self, text: str) -> int:
        """Estima el número de tokens en un texto."""
        # Estimación: 1 token ≈ 3.5 caracteres en español
        return int(len(text) / 3.5)

    def split_content_by_tokens(self, content: str, max_tokens: Optional[int] = None) -> List[str]:
        """Divide el contenido en fragmentos que no excedan el límite de tokens."""
        if max_tokens is None:
            max_tokens = self.max_tokens_per_request
        
        total_tokens = self.count_tokens_estimate(content)
        
        if total_tokens <= max_tokens:
            return [content]
        
        # Dividir por párrafos primero
        paragraphs = content.split('\n\n')
        fragments: List[str] = []
        current_fragment = ""
        current_tokens = 0
        
        for paragraph in paragraphs:
            paragraph_tokens = self.count_tokens_estimate(paragraph)
            
            if paragraph_tokens > max_tokens:
                # Párrafo excede el límite: dividir por oraciones
                sentences = re.split(r'[.!?]+', paragraph)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    sentence_tokens = self.count_tokens_estimate(sentence)
                    if current_tokens + sentence_tokens > max_tokens:
                        if current_fragment:
                            fragments.append(current_fragment.strip())
                        current_fragment = sentence
                        current_tokens = sentence_tokens
                    else:
                        current_fragment += " " + sentence
                        current_tokens += sentence_tokens
            else:
                if current_tokens + paragraph_tokens > max_tokens:
                    if current_fragment:
                        fragments.append(current_fragment.strip())
                    current_fragment = paragraph
                    current_tokens = paragraph_tokens
                else:
                    current_fragment += "\n\n" + paragraph
                    current_tokens += paragraph_tokens
        
        if current_fragment:
            fragments.append(current_fragment.strip())
        
        return fragments

    async def wait_for_rate_limit(self, estimated_tokens: int):
        """Espera si es necesario para respetar los límites de rate."""
        now = datetime.now()
        
        # Reset contador cada minuto
        if (now - self.last_minute_reset).seconds >= 60:
            self.request_timestamps = []
            self.tokens_used_this_minute = 0
            self.last_minute_reset = now
        
        recent_requests = [ts for ts in self.request_timestamps if (now - ts).seconds < 60]
        
        if len(recent_requests) >= self.requests_per_minute:
            wait_time = 60 - (now - recent_requests[0]).seconds + 1
            logger.info(f"Rate limit alcanzado, esperando {wait_time} segundos...")
            await asyncio.sleep(wait_time)
        
        if self.tokens_used_this_minute + estimated_tokens > self.max_tokens_per_minute:
            wait_time = 60 - (now - self.last_minute_reset).seconds + 1
            logger.info(f"Límite de tokens por minuto alcanzado, esperando {wait_time} segundos...")
            await asyncio.sleep(wait_time)
            self.tokens_used_this_minute = 0
            self.last_minute_reset = datetime.now()
        
        self.request_timestamps.append(now)
        self.tokens_used_this_minute += estimated_tokens

    # Mapping of section numbers to readable names
    SECTION_NAMES = {
        "1": "Legislación y Normativas",
        "2": "Judiciales",
        "3": "Sociedades y Asambleas",
        "4": "Licitaciones y Contrataciones",
        "5": "Normativas Municipales",
    }

    def _build_contextual_prompt(self, content: str, metadata: Dict) -> str:
        """Construye el prompt con contexto de jurisdicción, sección y tipo de boletín."""
        context_parts = []
        
        jurisdiccion = metadata.get("jurisdiccion_nombre") or metadata.get("jurisdiccion", "")
        if jurisdiccion:
            context_parts.append(f"Jurisdicción: {jurisdiccion}")
        
        fuente = metadata.get("fuente", "")
        if fuente:
            context_parts.append(f"Fuente: {fuente}")
        
        # Use seccion_nombre if available, otherwise map from section number
        seccion_nombre = metadata.get("seccion_nombre", "")
        section_type = metadata.get("section_type", "")
        if seccion_nombre:
            context_parts.append(f"Sección: {seccion_nombre}")
        elif section_type:
            readable = self.SECTION_NAMES.get(section_type, f"Sección {section_type}")
            context_parts.append(f"Sección: {readable}")
        
        boletin = metadata.get("boletin", "")
        if boletin:
            context_parts.append(f"Boletín: {boletin}")
        
        context_header = ""
        if context_parts:
            context_header = "Contexto del documento:\n" + "\n".join(f"- {p}" for p in context_parts) + "\n\n"
        
        return f"""{self.system_prompt}

{context_header}Contenido a analizar:
{content}"""

    async def analyze_fragment(self, content: str, metadata: Dict) -> Dict:
        """
        Analiza un fragmento individual de contenido usando structured output.
        
        Returns:
            Dict con formato FragmentAnalysis: {"actos": [...], "resumen_general": "..."}
        """
        # Fallback si no hay modelo Gemini
        if self.model is None:
            logger.warning("Cliente Gemini no disponible, usando respuesta fallback")
            return {
                "actos": [{
                    "tipo_acto": "otro",
                    "organismo": "No analizado (sin API key)",
                    "beneficiarios": [],
                    "montos": [],
                    "descripcion": "Análisis no disponible - configurar GOOGLE_API_KEY",
                    "riesgo": "informativo",
                }],
                "resumen_general": "Análisis no disponible - sin API key configurada",
                "metadata": metadata,
                "fragment_tokens": 0,
                "model_used": "fallback",
            }
        
        estimated_tokens = self.count_tokens_estimate(content) + self.count_tokens_estimate(self.system_prompt)
        await self.wait_for_rate_limit(estimated_tokens)
        
        try:
            prompt = self._build_contextual_prompt(content, metadata)
            
            # Llamar a Gemini con structured output (JSON mode)
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=4000,  # More tokens for multi-acto output
                    response_mime_type="application/json",
                    response_schema=FRAGMENT_ANALYSIS_SCHEMA,
                )
            )
            
            result_text = response.text.strip()
            result = json.loads(result_text)
            
            # Validate basic structure
            if "actos" not in result:
                result["actos"] = []
            if "resumen_general" not in result:
                result["resumen_general"] = "Resumen no disponible"
            
            # Ensure each acto has required fields
            for acto in result["actos"]:
                acto.setdefault("tipo_acto", "otro")
                acto.setdefault("organismo", "No especificado")
                acto.setdefault("descripcion", "Sin descripción")
                acto.setdefault("riesgo", "informativo")
                acto.setdefault("beneficiarios", [])
                acto.setdefault("montos", [])
                acto.setdefault("monto_total_numerico", 0)
                acto.setdefault("texto_original", "")
            
            # Add processing metadata
            result["metadata"] = metadata
            result["fragment_tokens"] = estimated_tokens
            result["model_used"] = self.model_name
            
            return result
                
        except json.JSONDecodeError as e:
            logger.warning(f"Respuesta no es JSON válido: {e}")
            return {
                "actos": [],
                "resumen_general": "Error al parsear respuesta del modelo",
                "metadata": metadata,
                "fragment_tokens": estimated_tokens,
                "model_used": self.model_name,
                "error": f"JSON parsing failed: {e}"
            }
        except Exception as e:
            logger.error(f"Error en análisis de fragmento: {e}")
            return {
                "actos": [],
                "resumen_general": f"Error en análisis: {str(e)[:100]}",
                "metadata": metadata,
                "fragment_tokens": estimated_tokens,
                "model_used": self.model_name,
                "error": str(e)
            }

    async def analyze_content(self, content: str, metadata: Dict) -> List[Dict]:
        """
        Analiza contenido dividiéndolo en fragmentos si es necesario.
        
        Returns:
            Lista de actos extraídos (cada uno es un dict con los campos de ActoExtraido).
            Cada acto incluye metadata adicional del fragmento.
        """
        try:
            total_tokens = self.count_tokens_estimate(content)
            
            if total_tokens <= self.max_tokens_per_request:
                fragments = [content]
            else:
                fragments = self.split_content_by_tokens(content)
                logger.info(f"Dividiendo contenido en {len(fragments)} fragmentos (total: {total_tokens} tokens)")
            
            all_actos: List[Dict] = []
            
            for i, fragment in enumerate(fragments):
                fragment_metadata = metadata.copy()
                fragment_metadata.update({
                    'fragment_number': i + 1,
                    'total_fragments': len(fragments)
                })
                
                result = await self.analyze_fragment(fragment, fragment_metadata)
                
                # Extract individual actos and enrich with fragment info
                for acto in result.get("actos", []):
                    acto["_fragment_index"] = i
                    # Use Gemini's texto_original (per-acto) with fallback to fragment start
                    acto["_fragment_content"] = acto.get("texto_original") or fragment[:500]
                    acto["_resumen_fragmento"] = result.get("resumen_general", "")
                    acto["_model_used"] = result.get("model_used", self.model_name)
                    all_actos.append(acto)
                
                # Small pause between fragments
                if i < len(fragments) - 1:
                    await asyncio.sleep(0.5)
            
            logger.info(f"Análisis completado: {len(all_actos)} actos extraídos de {len(fragments)} fragmentos")
            return all_actos
                
        except Exception as e:
            logger.error(f"Error en analyze_content: {e}")
            return []
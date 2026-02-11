"""
Servicio para análisis de contenido usando Google Gemini - Versión optimizada con manejo de tokens
"""

import asyncio
import logging
import re
from typing import Dict, List
import google.generativeai as genai
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class WatcherService:
    """Servicio optimizado para análisis de contenido con manejo de límites de tokens usando Google Gemini."""
    
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
        self.model_name = "gemini-2.0-flash"  # Modelo rápido y económico
        self.max_tokens_per_request = 4000  # Gemini tiene límites generosos
        self.max_tokens_per_minute = 1000000  # Límite de Gemini Flash
        self.requests_per_minute = 60  # Límite conservador
        
        # Control de rate limiting
        self.request_timestamps = []
        self.tokens_used_this_minute = 0
        self.last_minute_reset = datetime.now()
        
        # Prompt optimizado y más corto
        self.system_prompt = """Eres un auditor experto en análisis de gasto público argentino.

Analiza el texto y responde SOLO con un JSON válido con estos campos:
- categoria: "designaciones políticas" | "gasto excesivo" | "subsidios poco claros" | "obras sin trazabilidad" | "otros"
- entidad_beneficiaria: nombre de la entidad (máximo 50 caracteres)
- monto_estimado: monto si se menciona, sino "No especificado"
- riesgo: "ALTO" | "MEDIO" | "BAJO"
- tipo_curro: descripción breve del tipo de irregularidad (máximo 50 caracteres)
- accion_sugerida: recomendación breve (máximo 100 caracteres)

Responde SOLO el JSON, sin explicaciones adicionales."""

    def count_tokens_estimate(self, text: str) -> int:
        """Estima el número de tokens en un texto."""
        # Estimación más precisa: 1 token ≈ 3.5 caracteres en español
        return int(len(text) / 3.5)

    def split_content_by_tokens(self, content: str, max_tokens: int = None) -> List[str]:
        """Divide el contenido en fragmentos que no excedan el límite de tokens."""
        if max_tokens is None:
            max_tokens = self.max_tokens_per_request
        
        total_tokens = self.count_tokens_estimate(content)
        
        if total_tokens <= max_tokens:
            return [content]
        
        # Dividir por párrafos primero
        paragraphs = content.split('\n\n')
        fragments = []
        current_fragment = ""
        current_tokens = 0
        
        for paragraph in paragraphs:
            paragraph_tokens = self.count_tokens_estimate(paragraph)
            
            # Si un párrafo solo ya excede el límite, dividirlo por oraciones
            if paragraph_tokens > max_tokens:
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
                # Párrafo normal
                if current_tokens + paragraph_tokens > max_tokens:
                    if current_fragment:
                        fragments.append(current_fragment.strip())
                    current_fragment = paragraph
                    current_tokens = paragraph_tokens
                else:
                    current_fragment += "\n\n" + paragraph
                    current_tokens += paragraph_tokens
        
        # Agregar el último fragmento
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
        
        # Verificar límite de requests por minuto
        recent_requests = [ts for ts in self.request_timestamps if (now - ts).seconds < 60]
        
        if len(recent_requests) >= self.requests_per_minute:
            wait_time = 60 - (now - recent_requests[0]).seconds + 1
            logger.info(f"Rate limit alcanzado, esperando {wait_time} segundos...")
            await asyncio.sleep(wait_time)
        
        # Verificar límite de tokens por minuto
        if self.tokens_used_this_minute + estimated_tokens > self.max_tokens_per_minute:
            wait_time = 60 - (now - self.last_minute_reset).seconds + 1
            logger.info(f"Límite de tokens por minuto alcanzado, esperando {wait_time} segundos...")
            await asyncio.sleep(wait_time)
            self.tokens_used_this_minute = 0
            self.last_minute_reset = datetime.now()
        
        # Registrar la petición
        self.request_timestamps.append(now)
        self.tokens_used_this_minute += estimated_tokens

    async def analyze_fragment(self, content: str, metadata: Dict) -> Dict:
        """Analiza un fragmento individual de contenido."""
        # Si no hay modelo Gemini, retornar respuesta fallback
        if self.model is None:
            logger.warning("Cliente Gemini no disponible, usando respuesta fallback")
            return {
                "categoria": "otros",
                "entidad_beneficiaria": "No analizado (sin API key)",
                "monto_estimado": "No especificado",
                "riesgo": "BAJO",
                "tipo_curro": "Análisis no disponible",
                "accion_sugerida": "Configurar GOOGLE_API_KEY para análisis automático",
                "metadata": metadata,
                "fragment_tokens": 0,
                "model_used": "fallback",
                "warning": "Google API key not configured"
            }
        
        estimated_tokens = self.count_tokens_estimate(content) + self.count_tokens_estimate(self.system_prompt)
        
        # Esperar si es necesario por rate limits
        await self.wait_for_rate_limit(estimated_tokens)
        
        try:
            # Crear el prompt completo para Gemini
            prompt = f"""{self.system_prompt}

Contenido a analizar:
{content}"""
            
            # Llamar a Gemini
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=500
                )
            )
            
            result_text = response.text.strip()
            
            # Intentar parsear JSON
            import json
            try:
                result = json.loads(result_text)
                
                # Validar campos requeridos
                required_fields = ['categoria', 'entidad_beneficiaria', 'monto_estimado', 'riesgo', 'tipo_curro', 'accion_sugerida']
                for field in required_fields:
                    if field not in result:
                        result[field] = "No especificado"
                
                # Agregar metadata
                result['metadata'] = metadata
                result['fragment_tokens'] = estimated_tokens
                result['model_used'] = self.model_name
                
                return result
                
            except json.JSONDecodeError:
                logger.warning(f"Respuesta no es JSON válido: {result_text}")
                # Respuesta de fallback
                return {
                    "categoria": "otros",
                    "entidad_beneficiaria": "No especificado",
                    "monto_estimado": "No especificado",
                    "riesgo": "BAJO",
                    "tipo_curro": "Análisis incompleto",
                    "accion_sugerida": "Revisar manualmente",
                    "metadata": metadata,
                    "fragment_tokens": estimated_tokens,
                    "model_used": self.model_name,
                    "error": "JSON parsing failed"
                }
                
        except Exception as e:
            logger.error(f"Error en análisis de fragmento: {e}")
            
            # Respuesta de fallback en caso de error
            return {
                "categoria": "otros",
                "entidad_beneficiaria": "Error en análisis",
                "monto_estimado": "No especificado",
                "riesgo": "BAJO",
                "tipo_curro": "Error de procesamiento",
                "accion_sugerida": "Revisar manualmente",
                "metadata": metadata,
                "fragment_tokens": estimated_tokens,
                "model_used": self.model_name,
                "error": str(e)
            }

    def consolidate_fragment_results(self, results: List[Dict]) -> Dict:
        """Consolida los resultados de múltiples fragmentos en uno solo."""
        if not results:
            return {
                "categoria": "otros",
                "entidad_beneficiaria": "No especificado",
                "monto_estimado": "No especificado",
                "riesgo": "BAJO",
                "tipo_curro": "Sin análisis",
                "accion_sugerida": "Revisar manualmente"
            }
        
        if len(results) == 1:
            return results[0]
        
        # Consolidar múltiples fragmentos
        # Priorizar el riesgo más alto
        risk_priority = {"ALTO": 3, "MEDIO": 2, "BAJO": 1}
        highest_risk = max(results, key=lambda x: risk_priority.get(x.get('riesgo', 'BAJO'), 1))
        
        # Combinar entidades beneficiarias únicas
        entities = set()
        for result in results:
            entity = result.get('entidad_beneficiaria', '')
            if entity and entity != "No especificado":
                entities.add(entity)
        
        # Combinar montos mencionados
        amounts = set()
        for result in results:
            amount = result.get('monto_estimado', '')
            if amount and amount != "No especificado":
                amounts.add(amount)
        
        # Resultado consolidado
        consolidated = {
            "categoria": highest_risk.get('categoria', 'otros'),
            "entidad_beneficiaria": ', '.join(list(entities)[:3]) if entities else "No especificado",  # Max 3 entidades
            "monto_estimado": ', '.join(list(amounts)[:3]) if amounts else "No especificado",  # Max 3 montos
            "riesgo": highest_risk.get('riesgo', 'BAJO'),
            "tipo_curro": highest_risk.get('tipo_curro', 'Análisis múltiple'),
            "accion_sugerida": highest_risk.get('accion_sugerida', 'Revisar consolidado'),
            "fragments_analyzed": len(results),
            "total_tokens": sum(r.get('fragment_tokens', 0) for r in results),
            "model_used": self.model_name
        }
        
        return consolidated

    async def analyze_content(self, content: str, metadata: Dict) -> Dict:
        """
        Analiza contenido dividiéndolo en fragmentos si es necesario.
        
        Args:
            content: Texto a analizar
            metadata: Metadatos del contenido
            
        Returns:
            Diccionario con el análisis consolidado
        """
        try:
            # Verificar si el contenido necesita ser dividido
            total_tokens = self.count_tokens_estimate(content)
            
            if total_tokens <= self.max_tokens_per_request:
                # Contenido pequeño, analizar directamente
                return await self.analyze_fragment(content, metadata)
            else:
                # Contenido grande, dividir en fragmentos
                fragments = self.split_content_by_tokens(content)
                logger.info(f"Dividiendo contenido en {len(fragments)} fragmentos (total: {total_tokens} tokens)")
                
                # Analizar cada fragmento
                fragment_results = []
                for i, fragment in enumerate(fragments):
                    fragment_metadata = metadata.copy()
                    fragment_metadata.update({
                        'fragment_number': i + 1,
                        'total_fragments': len(fragments)
                    })
                    
                    result = await self.analyze_fragment(fragment, fragment_metadata)
                    fragment_results.append(result)
                    
                    # Pequeña pausa entre fragmentos para ser más amigable con la API
                    if i < len(fragments) - 1:  # No esperar después del último
                        await asyncio.sleep(0.5)
                
                # Consolidar resultados
                return self.consolidate_fragment_results(fragment_results)
                
        except Exception as e:
            logger.error(f"Error en analyze_content: {e}")
            return {
                "categoria": "otros",
                "entidad_beneficiaria": "Error en análisis",
                "monto_estimado": "No especificado",
                "riesgo": "BAJO",
                "tipo_curro": "Error de procesamiento",
                "accion_sugerida": "Revisar manualmente",
                "error": str(e)
            }
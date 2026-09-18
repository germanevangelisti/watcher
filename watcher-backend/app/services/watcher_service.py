"""
Servicio para análisis de contenido usando Google Gemini - v2 con structured output y multi-acto

Integra IntelligenceProvider: usa ProProvider cuando GOOGLE_API_KEY está disponible,
FreeProvider (rule-based) como fallback cuando no hay API key.
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Any, cast

try:
    import google.generativeai as genai
except ImportError:
    genai = None  # type: ignore[assignment]

from app.services.analysis_schema import (
    ANALYSIS_SYSTEM_PROMPT,
    FRAGMENT_ANALYSIS_SCHEMA,
)
from app.services.intelligence_provider import (
    IntelligenceProvider,
    get_default_provider,
)
from app.services.reference_firewall import ReferenceFirewallService

logger = logging.getLogger(__name__)


class WatcherService:
    """Servicio de análisis de contenido con Google Gemini - v2 structured output."""

    def __init__(self):
        """Inicializa el servicio con configuración optimizada."""
        api_key = os.getenv('GOOGLE_API_KEY')

        # Inicializar cliente solo si hay API key y el SDK, sino usar fallback
        self.model = None
        if api_key and genai is not None:
            try:
                # genai.configure() is called once at app startup in main.py
                self.model = genai.GenerativeModel("gemini-2.0-flash")
                logger.info("Google Gemini client inicializado correctamente")
            except Exception as e:
                logger.error(f"Error inicializando Gemini: {e}")
                self.model = None
        elif api_key:
            logger.warning(
                "GOOGLE_API_KEY set but google-generativeai is not installed; "
                "using LocalPro/FreeProvider. Install extra [ai] for Gemini."
            )
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
        self.request_timestamps: list[datetime] = []
        self.tokens_used_this_minute = 0
        self.last_minute_reset = datetime.now()

        # Reference Firewall (Fase IV) — set externally via set_firewall()
        self._firewall: ReferenceFirewallService | None = None

        # AIU Decomposition Service (Fase II) — set externally via set_aiu_service()
        self._aiu_service: Any | None = None

        # Intelligence tier: local (Ollama) | pro (Gemini) | free (rules)
        self._provider: IntelligenceProvider = get_default_provider(api_key)
        self.system_prompt = ANALYSIS_SYSTEM_PROMPT

    def set_firewall(self, firewall_service: "ReferenceFirewallService") -> None:
        """
        Attach a ReferenceFirewallService instance.

        The actual async validation must be awaited by the pipeline caller;
        this service only stores the reference so callers can retrieve it.
        """
        self._firewall = firewall_service

    def set_aiu_service(self, aiu_service: Any) -> None:
        """
        Attach an AIUService instance (Fase II).

        Called once at application startup after both services are constructed.
        The AIU decomposition hook in analyze_fragment() is non-blocking and
        will silently skip if this is never called.
        """
        self._aiu_service = aiu_service

    def count_tokens_estimate(self, text: str) -> int:
        """Estima el número de tokens en un texto."""
        # Estimación: 1 token ≈ 3.5 caracteres en español
        return int(len(text) / 3.5)

    def split_content_by_tokens(self, content: str, max_tokens: int | None = None) -> list[str]:
        """Divide el contenido en fragmentos que no excedan el límite de tokens."""
        if max_tokens is None:
            max_tokens = self.max_tokens_per_request

        total_tokens = self.count_tokens_estimate(content)

        if total_tokens <= max_tokens:
            return [content]

        # Dividir por párrafos primero
        paragraphs = content.split('\n\n')
        fragments: list[str] = []
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
        if (now - self.last_minute_reset).total_seconds() >= 60:
            self.request_timestamps = []
            self.tokens_used_this_minute = 0
            self.last_minute_reset = now

        recent_requests = [ts for ts in self.request_timestamps if (now - ts).total_seconds() < 60]

        if len(recent_requests) >= self.requests_per_minute:
            wait_time = 60 - (now - recent_requests[0]).total_seconds() + 1
            logger.info(f"Rate limit alcanzado, esperando {wait_time} segundos...")
            await asyncio.sleep(wait_time)

        if self.tokens_used_this_minute + estimated_tokens > self.max_tokens_per_minute:
            wait_time = 60 - (now - self.last_minute_reset).total_seconds() + 1
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

    def _build_contextual_prompt(self, content: str, metadata: dict) -> str:
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

    async def analyze_fragment(self, content: str, metadata: dict) -> dict:
        """
        Analiza un fragmento individual de contenido usando structured output.
        
        Returns:
            Dict con formato FragmentAnalysis: {"actos": [...], "resumen_general": "..."}
        """
        # LocalPro takes priority even if a Gemini client exists (hardware-local).
        if getattr(self._provider, "tier", None) == "local":
            return await self._provider.analyze_fragment(content, metadata)

        # Delegar a FreeProvider cuando no hay modelo Gemini disponible
        if self.model is None:
            logger.warning(
                "Cliente Gemini no disponible, delegando a %s (tier=%s)",
                type(self._provider).__name__,
                self._provider.tier,
            )
            return await self._provider.analyze_fragment(content, metadata)

        estimated_tokens = self.count_tokens_estimate(content) + self.count_tokens_estimate(self.system_prompt)
        await self.wait_for_rate_limit(estimated_tokens)

        _GEMINI_CALL_TIMEOUT = 120  # seconds before declaring a hung Gemini call dead
        _MAX_FRAGMENT_RETRIES = 3   # attempts per fragment before giving up

        def _empty_result(error_msg: str) -> dict:
            return {
                "actos": [],
                "resumen_general": f"Error en análisis: {error_msg[:100]}",
                "metadata": metadata,
                "fragment_tokens": estimated_tokens,
                "model_used": self.model_name,
                "error": error_msg,
            }

        prompt = self._build_contextual_prompt(content, metadata)
        gen_config = genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=8192,
            response_mime_type="application/json",
            response_schema=FRAGMENT_ANALYSIS_SCHEMA,
        )
        frag_num = metadata.get("fragment_number", "?")

        for attempt in range(_MAX_FRAGMENT_RETRIES):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.model.generate_content,
                        prompt,
                        generation_config=gen_config,
                    ),
                    timeout=_GEMINI_CALL_TIMEOUT,
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
                    acto.setdefault("fecha_acto", None)
                    acto.setdefault("expediente", None)
                    acto.setdefault("referencias_normativas", [])
                    acto.setdefault("fechas_clave", [])
                    acto.setdefault("relacion_principal", None)
                    acto.setdefault("firmante", None)
                    acto.setdefault("imputacion_presupuestaria", None)
                    acto.setdefault("presupuesto_oficial", 0)

                # Add processing metadata
                result["metadata"] = metadata
                result["fragment_tokens"] = estimated_tokens
                result["model_used"] = self.model_name

                # Reference Firewall hook (non-blocking, informative only).
                if self._firewall is not None:
                    try:
                        result['_firewall_pending'] = True
                    except Exception:
                        pass

                # AIU Decomposition hook (Fase II) — non-blocking, never propagates.
                if self._aiu_service is not None:
                    try:
                        actos = result.get('actos', [])
                        if actos:
                            aiu_svc = cast(Any, self._aiu_service)
                            decomposition = aiu_svc.decompose_actos(actos)
                            result['aiu_decomposition'] = {
                                'total_aius': decomposition.total_aius,
                                'by_type': decomposition.by_type,
                                'aius': [aiu.model_dump() for aiu in decomposition.aius]
                            }
                    except Exception as e:
                        logger.debug(f"AIU decomposition skipped: {e}")

                return result

            except TimeoutError:
                logger.warning(
                    f"Gemini timeout en fragmento {frag_num} "
                    f"(intento {attempt + 1}/{_MAX_FRAGMENT_RETRIES}, {_GEMINI_CALL_TIMEOUT}s)"
                )
                if attempt < _MAX_FRAGMENT_RETRIES - 1:
                    await asyncio.sleep(15)
                    continue
                return _empty_result(f"Gemini timeout: sin respuesta en {_GEMINI_CALL_TIMEOUT}s")

            except json.JSONDecodeError as e:
                logger.warning(f"Respuesta no es JSON válido en fragmento {frag_num}: {e}")
                # JSON errors are not transient — don't retry
                return _empty_result(f"JSON parsing failed: {e}")

            except Exception as e:
                err_str = str(e).lower()
                if "429" in str(e) or "resource exhausted" in err_str or "quota" in err_str:
                    backoff = 30 * (2 ** attempt)  # 30s → 60s → 120s
                    logger.warning(
                        f"Rate limit 429 en fragmento {frag_num}, esperando {backoff}s "
                        f"(intento {attempt + 1}/{_MAX_FRAGMENT_RETRIES})"
                    )
                    await asyncio.sleep(backoff)
                    if attempt < _MAX_FRAGMENT_RETRIES - 1:
                        continue
                    return _empty_result("Rate limit: 429 Resource Exhausted")
                else:
                    logger.error(f"Error en análisis de fragmento {frag_num}: {e}")
                    return _empty_result(str(e))

        return _empty_result("Max retries exceeded")

    async def analyze_content(self, content: str, metadata: dict) -> list[dict]:
        """
        Analiza contenido dividiéndolo en fragmentos si es necesario.
        
        Returns:
            Lista de actos extraídos (cada uno es un dict con los campos de ActoExtraido).
            Cada acto incluye metadata adicional del fragmento.
        """
        try:
            total_tokens = self.count_tokens_estimate(content)
            token_budget = self.max_tokens_per_request
            if getattr(self._provider, "tier", None) == "local":
                from app.core.hardware import ollama_num_ctx

                token_budget = max(512, ollama_num_ctx() - 1536)

            if total_tokens <= token_budget:
                fragments = [content]
            else:
                fragments = self.split_content_by_tokens(content, max_tokens=token_budget)
                logger.info(
                    "Dividiendo contenido en %s fragmentos (total: %s tokens)",
                    len(fragments),
                    total_tokens,
                )

            from app.core.fragment_priority import select_prioritized
            from app.core.hardware import max_analysis_fragments

            cap = max_analysis_fragments()
            if cap and len(fragments) > cap:
                logger.info(
                    "Analysis fragment cap %s/%s (priority: decretos/licitaciones over edictos)",
                    cap,
                    len(fragments),
                )
                fragments = select_prioritized(fragments, cap, lambda t: t)

            all_actos: list[dict] = []

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
                if i < len(fragments) - 1 and getattr(self._provider, "tier", None) != "local":
                    await asyncio.sleep(0.5)

            logger.info(f"Análisis completado: {len(all_actos)} actos extraídos de {len(fragments)} fragmentos")
            return all_actos

        except Exception as e:
            logger.error(f"Error en analyze_content: {e}")
            return []

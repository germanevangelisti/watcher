"""
Insight & Reporting Agent

Genera insights accionables, reportes y responde queries en lenguaje natural
"""
import logging
import re
import unicodedata
from datetime import datetime
from typing import Any

from app.core.agent_config import InsightReportingConfig
from app.db.database import AsyncSessionLocal
from app.services.llm_provider import LLMProvider, resolve_llm_provider
from app.services.reference_firewall import ReferenceFirewallService

from agents.orchestrator.state import AgentType, TaskDefinition, WorkflowState
from agents.tools.analysis_tools import AnalysisTools
from agents.tools.database_tools import DatabaseTools
from agents.tools.presupuesto_tools import (
    INTENT_ORGANISMOS,
    PresupuestoTools,
    build_actos_system_block,
    build_corpus_system_block,
    build_presupuesto_system_block,
    detect_presupuesto_intents,
    route_presupuesto,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------- turnos sin pedido
#
# Un "gracias" no es una consulta, y hasta 2026-10-01 corría el pipeline entero:
# el router de presupuesto, la búsqueda sobre el corpus —`search_bm25("gracias")`
# devuelve boletines que contienen esa palabra, así que `fragmentos` quedaba
# lleno y el bloque de ausencia **no** se emitía— y, con los últimos 3 turnos en
# el prompt, el modelo contestaba **la pregunta anterior** sobre un contexto que
# no la cubría.  Medido: el turno *"gracias"* posterior a *"desglosá los actos de
# Caminos de las Sierras de abril de 2026"* devolvió *"No encontré información
# específica sobre actos de Caminos de las Sierras S.A. …"* citando como fuente
# una búsqueda que nunca fue sobre eso.
#
# El corte es determinístico y va **antes** de abrir la base: un turno sin pedido
# no consulta nada, no cita fuentes y no llama al modelo (en local tarda segundos
# y puede reabrir el turno anterior).  El vocabulario es **cerrado**: el turno es
# de cortesía sólo si *todas* sus palabras están acá, así que *"gracias, ¿y el
# total?"* sigue el camino normal.  Es una lista, no un detector semántico: si
# aparece una fórmula nueva, se agrega la palabra.
_MARCADORES_DE_CORTESIA = frozenset([
    "gracias", "hola", "buenas", "buenos", "dia", "dias", "tardes", "noches",
    "tal", "saludos", "chau", "chao", "adios", "ok", "okey", "dale", "listo",
    "perfecto", "genial", "excelente", "joya", "barbaro", "util", "utiles",
    "amable", "favor", "disculpas", "perdon",
])
_SALUDOS = frozenset(["hola", "buenas", "buenos", "dia", "dias", "tardes", "noches", "tal", "saludos"])
_FUNCIONES = frozenset([
    "a", "al", "buen", "bueno", "con", "de", "del", "el", "en", "es", "esta",
    "e", "la", "las", "le", "lo", "los", "mas", "me", "mi", "mil", "muchas",
    "muchisimas", "muchisimo", "muy", "nada", "no", "o", "para", "por", "que",
    "se", "si", "soy", "su", "te", "todo", "todos", "tu", "un", "una", "y", "ya",
])
_PALABRAS_DE_CORTESIA = _MARCADORES_DE_CORTESIA | _FUNCIONES

_RESPUESTA_SALUDO = (
    "¡Hola! Puedo desglosar un organismo, comparar finalidades o buscar un tema "
    "en los boletines. ¿Qué querés ver?"
)
_RESPUESTA_CORTESIA = (
    "De nada. Cuando quieras seguimos: puedo desglosar un organismo, comparar "
    "finalidades o buscar un tema en los boletines."
)


def _palabras(texto: str) -> list[str]:
    """Tokeniza en minúsculas, sin acentos y sin signos: `¿¡Gracias!!` → `gracias`."""
    sin_acentos = unicodedata.normalize("NFKD", texto.lower())
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return re.findall(r"[^\W\d_]+", sin_acentos)


def respuesta_si_es_turno_sin_pedido(query: str) -> str | None:
    """La respuesta corta de un turno de cortesía, o `None` si el turno pide algo.

    `None` es "no es de cortesía", no "no hay respuesta": el llamador sigue con el
    camino normal.  Un turno vacío o de puras palabras funcionales (`"¿y eso?"`)
    tampoco entra — eso suele ser un seguimiento, y adivinar cuesta más que buscar.
    """
    palabras = _palabras(query)
    if not palabras or not all(p in _PALABRAS_DE_CORTESIA for p in palabras):
        return None
    if not any(p in _MARCADORES_DE_CORTESIA for p in palabras):
        return None
    if any(p in _SALUDOS for p in palabras):
        return _RESPUESTA_SALUDO
    return _RESPUESTA_CORTESIA


class InsightReportingAgent:
    """
    Agente especializado en generación de insights y reportes

    Capacidades:
    - Agregación de métricas
    - Generación de narrativas (NLG)
    - Respuestas a queries en lenguaje natural
    - Creación de reportes
    """

    def __init__(self, config: InsightReportingConfig | None = None):
        """
        Inicializa el agente

        Args:
            config: Configuración del agente
        """
        self.config = config or InsightReportingConfig()
        self.agent_type = AgentType.INSIGHT_REPORTING

        # Cliente LLM para generación de texto.  Está detrás de la capa de
        # providers: `resolve_llm_provider()` respeta `LLM_PROVIDER` y cae a
        # Ollama local si lo configurado no se puede construir (falta la API
        # key, falta el SDK).  Construirlo no hace I/O, así que el import del
        # módulo de la API no depende de que el servidor local esté arriba.
        self.provider = resolve_llm_provider()

        # Historial de conversación
        self.conversation_history: list[dict[str, str]] = []

        # Reference Firewall (Fase IV) — set externally via set_firewall()
        self._firewall: ReferenceFirewallService | None = None

        logger.info("InsightReportingAgent inicializado")

    async def _buscar_en_corpus(self, query: str, top_k: int = 5) -> list[Any]:
        """Busca en los boletines: semántica **y** keyword.

        Hasta 2026-10-01 esto era `get_retrieval_service()`, **sin sesión de base**:
        `RetrievalService` dejaba `fts_service = None`, `search_bm25` nunca corría
        (un log de debug, invisible) y `hybrid_search` fusionaba una lista vacía con
        otra.  Se creía híbrida y era semántica sola — y en una máquina sin
        embeddings locales, nada.

        La sesión es por búsqueda: `keyword_search` corre en un hilo y el servicio
        la retiene, así que no puede ser una guardada en este singleton.
        """
        if not self.config.use_vector_db:
            return []
        from app.services.retrieval_service import retrieval_service_con_sesion

        async with retrieval_service_con_sesion() as servicio:
            return await servicio.hybrid_search(query=query, top_k=top_k, rerank=True)

    async def _contexto_de_corpus(self, query: str) -> dict[str, Any]:
        """Los fragmentos del corpus y, cuando no hay, **el hueco declarado**.

        El estado viaja al system prompt (`build_corpus_system_block`): sin él, el
        modelo no puede distinguir *no busqué* de *busqué y no había* y contesta
        *"no se publicó"* — que es lo que pasó con obra pública en septiembre.
        """
        if not self.config.use_vector_db:
            return {
                "ejecutada": False,
                "resultados": 0,
                "motivo": "la búsqueda sobre el corpus está deshabilitada en esta configuración",
            }

        try:
            resultados = await self._buscar_en_corpus(query)
        except Exception as e:
            logger.warning("Búsqueda sobre el corpus falló: %s: %s", type(e).__name__, e)
            return {
                "ejecutada": True,
                "resultados": 0,
                "motivo": f"la búsqueda falló ({type(e).__name__}); no hubo revisión del corpus",
            }

        if resultados:
            logger.info("Contexto del corpus: %d fragmentos", len(resultados))
            return {
                "ejecutada": True,
                "resultados": len(resultados),
                "fragmentos": [
                    {"texto": r.text[:500], "score": r.score, "document_id": r.document_id}
                    for r in resultados
                ],
            }

        logger.warning(
            "Búsqueda sobre el corpus sin resultados para %r: el modelo va a declarar "
            "que no lo encontró (nunca que no se publicó).",
            query,
        )
        return {
            "ejecutada": True,
            "resultados": 0,
            "motivo": "la búsqueda se ejecutó y no devolvió fragmentos",
        }

    async def execute(self, workflow: WorkflowState,
                     task: TaskDefinition) -> dict[str, Any]:
        """
        Ejecuta una tarea del agente

        Args:
            workflow: Estado del workflow
            task: Tarea a ejecutar

        Returns:
            Resultado de la ejecución
        """
        task_type = task.task_type
        parameters = task.parameters

        logger.info(f"Ejecutando tarea: {task_type}")

        if task_type == "generate_report":
            return await self.generate_report(
                parameters.get("data"),
                parameters.get("report_type", "executive")
            )
        elif task_type == "answer_query":
            return await self.answer_query(
                parameters.get("query"),
                parameters.get("context")
            )
        elif task_type == "generate_summary":
            return await self.generate_summary(
                parameters.get("data")
            )
        elif task_type == "monthly_summary":
            return await self.generate_monthly_summary(
                parameters.get("year", 2025),
                parameters.get("month", 8)
            )
        elif task_type == "trend_analysis":
            return await self.generate_trend_analysis(
                parameters.get("start_year", 2025),
                parameters.get("start_month", 1),
                parameters.get("end_year", 2025),
                parameters.get("end_month", 11)
            )
        else:
            raise ValueError(f"Tipo de tarea no soportado: {task_type}")

    async def generate_report(self, data: dict[str, Any],
                             report_type: str = "executive") -> dict[str, Any]:
        """
        Genera un reporte basado en datos

        Args:
            data: Datos para el reporte
            report_type: Tipo de reporte (executive, detailed, comparative)

        Returns:
            Reporte generado
        """
        try:
            if report_type == "executive":
                return await self._generate_executive_summary(data)
            elif report_type == "detailed":
                return await self._generate_detailed_report(data)
            elif report_type == "comparative":
                return await self._generate_comparative_report(data)
            else:
                raise ValueError(f"Tipo de reporte no soportado: {report_type}")

        except Exception as e:
            logger.error(f"Error generando reporte: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def answer_query(self, query: str,
                          context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Responde una query en lenguaje natural

        Args:
            query: Pregunta del usuario
            context: Contexto adicional (datos, documentos, etc.)

        Returns:
            Respuesta generada
        """
        try:
            # Agregar query al historial
            self.conversation_history.append({
                "role": "user",
                "content": query
            })

            self._trim_history()

            # Generar respuesta
            if self.provider:
                response_text, _ = await self._generate_ai_response(query, context)
            else:
                response_text = self._generate_fallback_response(query, context)

            # Agregar respuesta al historial
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })

            result: dict[str, Any] = {
                "success": True,
                "query": query,
                "response": response_text,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Reference Firewall — V1: flag only, never blocks
            if self._firewall is not None:
                try:
                    validation = await self._firewall.validate_references(response_text)
                    if validation.flagged:
                        logger.warning(
                            f"Reference Firewall: {validation.not_found_count} unverified refs in answer"
                        )
                    result['firewall_validation'] = {
                        'flagged': validation.flagged,
                        'score': validation.firewall_score,
                        'not_found': validation.not_found_count,
                    }
                except Exception as e:
                    logger.debug(f"Firewall check skipped: {e}")

            return result

        except Exception as e:
            logger.error(f"Error respondiendo query: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_summary(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Genera un resumen ejecutivo de datos

        Args:
            data: Datos a resumir

        Returns:
            Resumen generado
        """
        return await self._generate_executive_summary(data)

    async def _generate_executive_summary(self, data: dict[str, Any]) -> dict[str, Any]:
        """Genera resumen ejecutivo"""
        # Extraer métricas clave
        metrics = self._extract_key_metrics(data)

        # Generar narrativa
        narrative = await self._create_narrative(metrics)

        return {
            "success": True,
            "report_type": "executive",
            "title": "Resumen Ejecutivo de Análisis",
            "generated_at": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "narrative": narrative,
            "recommendations": self._generate_recommendations(metrics)
        }

    async def _generate_detailed_report(self, data: dict[str, Any]) -> dict[str, Any]:
        """Genera reporte detallado"""
        return {
            "success": True,
            "report_type": "detailed",
            "title": "Reporte Detallado de Análisis",
            "generated_at": datetime.utcnow().isoformat(),
            "data": data,
            "analysis": "Análisis detallado en desarrollo"
        }

    async def _generate_comparative_report(self, data: dict[str, Any]) -> dict[str, Any]:
        """Genera reporte comparativo"""
        return {
            "success": True,
            "report_type": "comparative",
            "title": "Reporte Comparativo",
            "generated_at": datetime.utcnow().isoformat(),
            "comparison": "Comparación en desarrollo"
        }

    def _extract_key_metrics(self, data: dict[str, Any]) -> dict[str, Any]:
        """Extrae métricas clave de los datos"""
        metrics = {
            "total_documents": 0,
            "red_flags_detected": 0,
            "high_risk_cases": 0,
            "medium_risk_cases": 0,
            "low_risk_cases": 0,
            "average_transparency_score": 0.0
        }

        # Extraer de los datos
        if "results" in data:
            results = data["results"]
            metrics["total_documents"] = len(results)

            for result in results:
                if "red_flags" in result:
                    metrics["red_flags_detected"] += len(result["red_flags"])

                risk = result.get("risk_level", "low")
                if risk == "high":
                    metrics["high_risk_cases"] += 1
                elif risk == "medium":
                    metrics["medium_risk_cases"] += 1
                else:
                    metrics["low_risk_cases"] += 1

        return metrics

    async def _create_narrative(self, metrics: dict[str, Any]) -> str:
        """Crea narrativa basada en métricas"""
        if self.provider:
            return await self._generate_ai_narrative(metrics)
        else:
            return self._generate_template_narrative(metrics)

    async def _generate_ai_narrative(self, metrics: dict[str, Any]) -> str:
        """Genera narrativa con IA"""
        prompt = f"""
        Genera un resumen ejecutivo basado en estas métricas de análisis de transparencia:

        - Total de documentos analizados: {metrics.get('total_documents', 0)}
        - Red flags detectadas: {metrics.get('red_flags_detected', 0)}
        - Casos de riesgo alto: {metrics.get('high_risk_cases', 0)}
        - Casos de riesgo medio: {metrics.get('medium_risk_cases', 0)}
        - Casos de riesgo bajo: {metrics.get('low_risk_cases', 0)}

        Genera un párrafo de 3-4 oraciones, profesional y directo.
        """

        try:
            return await self.provider.generate_text(
                prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

        except Exception as e:
            logger.error(f"Error generando narrativa con IA: {e}")
            return self._generate_template_narrative(metrics)

    def _generate_template_narrative(self, metrics: dict[str, Any]) -> str:
        """Genera narrativa con template"""
        total = metrics.get('total_documents', 0)
        flags = metrics.get('red_flags_detected', 0)
        high = metrics.get('high_risk_cases', 0)

        narrative = f"Se analizaron {total} documentos oficiales. "
        narrative += f"Se detectaron {flags} red flags en total. "

        if high > 0:
            narrative += f"Se identificaron {high} casos de riesgo alto que requieren atención inmediata. "
        else:
            narrative += "No se identificaron casos de riesgo alto. "

        narrative += "Se recomienda revisar los casos priorizados por nivel de riesgo."

        return narrative

    def _generate_recommendations(self, metrics: dict[str, Any]) -> list[str]:
        """Genera recomendaciones basadas en métricas"""
        recommendations = []

        high = metrics.get('high_risk_cases', 0)
        flags = metrics.get('red_flags_detected', 0)

        if high > 0:
            recommendations.append(f"Revisar inmediatamente los {high} casos de riesgo alto")

        if flags > 10:
            recommendations.append("Considerar ajustar thresholds de detección para reducir falsos positivos")

        if metrics.get('total_documents', 0) > 0:
            recommendations.append("Continuar con monitoreo regular de boletines oficiales")

        return recommendations if recommendations else ["No hay recomendaciones específicas"]

    async def query_with_data(self, query: str,
                              provider: LLMProvider | None = None) -> dict[str, Any]:
        """
        Responde una query consultando los datos reales de la base de datos

        Args:
            query: Pregunta del usuario
            provider: proveedor con el que redactar **este** turno.  `None` usa
                el del agente (el que resolvió el entorno).  El agente no lo
                construye: quien elige un proveedor explícito es el llamador, y
                sólo él puede fallar con un motivo visible en vez de caer a
                Ollama en silencio.

        Returns:
            Respuesta con datos reales, y `llm` con quién la redactó (`None` si
            la escribió el sistema y no un modelo).
        """
        # Un turno sin pedido se contesta antes de tocar la base: no hay consulta
        # que hacer, y buscar igual —lo que se hacía— llenaba el contexto de
        # fragmentos que no eran de nada y le devolvía el turno anterior al modelo.
        # `data_used` va vacío a propósito: no se consultó ninguna fuente, y la
        # burbuja no tiene que citar ninguna.
        cortesia = respuesta_si_es_turno_sin_pedido(query)
        if cortesia is not None:
            self._remember_turn(query, cortesia)
            return {
                "success": True,
                "query": query,
                "response": cortesia,
                "data_used": [],
                # Texto fijo del agente: no hay modelo que declarar, y decir
                # "Ollama" acá atribuiría a un modelo una frase que no escribió.
                "llm": None,
                "timestamp": datetime.utcnow().isoformat(),
            }

        try:
            async with AsyncSessionLocal() as db:
                # Detectar tipo de consulta y obtener datos relevantes
                query_lower = query.lower()

                data_context = {}

                # Presupuesto: el router declara qué tool sirve cada intent y con qué
                # key entra al contexto (`PRESUPUESTO_TOOLS`).  El resumen se lee
                # siempre —alimenta el bloque fijo del system prompt y, cuando la
                # query lo pide, el data_context—; un fallo acá degrada a "sin datos
                # de ejecución", nunca rompe el chat.
                presupuesto_intents: set[str] = set()
                presupuesto_resumen = None
                try:
                    presupuesto_intents = detect_presupuesto_intents(query)
                    presupuesto_resumen = await PresupuestoTools.get_ejecucion_resumen(db)
                    data_context.update(await route_presupuesto(
                        db, query, presupuesto_resumen, presupuesto_intents,
                    ))
                except Exception as e:
                    logger.warning(f"Contexto de presupuesto no disponible: {e}")

                # Estadísticas generales
                if any(word in query_lower for word in ['estadísticas', 'stats', 'general', 'resumen', 'cuántos']):
                    data_context['statistics'] = await DatabaseTools.get_statistics(db)

                # Documentos de alto riesgo
                if any(word in query_lower for word in ['riesgo', 'alto riesgo', 'crítico', 'peligroso']):
                    data_context['top_risk'] = await AnalysisTools.get_top_risk_documents(db, limit=10)

                # Red flags
                if any(word in query_lower for word in ['red flag', 'alerta', 'problema', 'irregularidad']):
                    data_context['red_flag_distribution'] = await AnalysisTools.get_red_flag_distribution(db)
                    data_context['red_flags'] = await DatabaseTools.get_red_flags(db, severity='high', limit=20)

                # Tendencias
                if any(word in query_lower for word in ['tendencia', 'evolución', 'cambio', 'comparar']):
                    data_context['trends'] = await AnalysisTools.get_transparency_trends(
                        db, 2025, 1, 2025, 11
                    )

                # Entidades
                # `organismo` es ambiguo: en la query (b) de presupuesto significa
                # "quién concentra el gasto", y ahí el contexto de beneficiarios es
                # la respuesta equivocada. Cuando la query trae señal de gasto gana
                # presupuesto; el resto del path de transparencia queda igual.
                if (any(word in query_lower for word in ['beneficiario', 'entidad', 'empresa', 'organismo'])
                        and INTENT_ORGANISMOS not in presupuesto_intents):
                    data_context['entities'] = await AnalysisTools.get_entity_analysis(db, 'beneficiaries')

                # Búsqueda sobre el corpus de boletines.  Los fragmentos entran al
                # contexto con **el nombre de lo que son**: `corpus_boletines`.  La
                # clave se llamó `semantic_context` y el FE la rotulaba "Búsqueda
                # semántica", pero los fragmentos son el resultado de
                # `hybrid_search` —keyword + semántica, fusionadas con RRF— y desde
                # el bloqueo de Smart App Control esta máquina sólo corre la mitad
                # de keyword: el chip afirmaba una búsqueda semántica que no había
                # ocurrido.  **El hueco no entra acá**: va al system prompt
                # (`build_corpus_system_block`), porque no es una fuente consultada
                # sino un estado que el modelo tiene que poder declarar.  Meterlo en
                # `data_used` lo mostraría como si fuera un dato encontrado.
                corpus = await self._contexto_de_corpus(query)
                if corpus.get("fragmentos"):
                    data_context['corpus_boletines'] = corpus['fragmentos']

                # Si no se encontró contexto específico, obtener estadísticas
                if not data_context:
                    data_context['statistics'] = await DatabaseTools.get_statistics(db)

                # Generar respuesta usando IA con el contexto de datos
                system_block = build_presupuesto_system_block(presupuesto_resumen)
                corpus_block = build_corpus_system_block(corpus)
                if corpus_block:
                    system_block = f"{system_block}\n\n{corpus_block}"

                # El proveedor del turno: el elegido para esta consulta si lo
                # hay, y si no el del agente.  `del_modelo` distingue la
                # respuesta redactada por el modelo del texto de fallback, que
                # sale por el mismo camino cuando el modelo no contesta: la
                # burbuja no puede decir "Ollama" sobre un texto que el sistema
                # escribió solo.
                provider_efectivo = provider or self.provider
                llm_del_turno = None
                if provider_efectivo:
                    response_text, del_modelo = await self._generate_ai_response(
                        query, data_context, system_block=system_block,
                        provider=provider_efectivo,
                    )
                    if del_modelo:
                        # `getattr` y no acceso directo: los dobles de test no
                        # implementan el contrato entero, y un turno no puede
                        # caerse porque un provider falso no se sepa nombrar.
                        llm_del_turno = {
                            "provider": getattr(provider_efectivo, "provider_id", None),
                            "model": getattr(provider_efectivo, "model_name", None),
                        }
                else:
                    response_text = self._generate_fallback_response(query, data_context)

                # Memoria de turnos: recién acá, con la respuesta ya generada.
                # Éste es el único path del chat del FE, y hasta ahora no escribía
                # historial (sólo lo hacía `answer_query`), así que
                # `_generate_ai_response` leía siempre una lista vacía.
                self._remember_turn(query, response_text)

                return {
                    "success": True,
                    "query": query,
                    "response": response_text,
                    "data_used": list(data_context.keys()),
                    "llm": llm_del_turno,
                    "timestamp": datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error(f"Error consultando datos: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query": query
            }

    def _build_messages(self, query: str,
                        context: dict[str, Any] | None = None,
                        system_block: str | None = None) -> list[dict[str, str]]:
        """Arma los mensajes que van al modelo.

        `system_block` es contexto estable y viaja en el mensaje `system` —no
        concatenado al user— para que pese igual en cada turno; el `context`
        por query sigue yendo en el user message.
        """
        context_str = ""
        if context:
            context_str = f"\n\nContexto adicional:\n{str(context)}"

        system_content = (
            "Eres un asistente experto en análisis de transparencia gubernamental. "
            "Responde de forma clara y concisa, en español. "
            "La respuesta se lee en una burbuja de chat, no en un documento: prosa "
            "breve y, si enumerás, guiones cortos ('- '); evitá encabezados ('#') y "
            "bloques de cita ('>'). "
            # La regla que faltaba.  El agente afirmaba "0 documentos encontrados"
            # sobre organismos que nunca consultó, y una ausencia inventada se lee
            # como dato verificado.  El hueco se declara, no se rellena.
            #
            # La primera redacción hablaba de "datos, registros o documentos" y del
            # detalle de un organismo: el 2026-10-01 el chat contestó "No se publicó
            # información sobre obra pública en septiembre" — con cinco boletines de
            # septiembre publicando obra, y sin haber buscado— porque *publicar* no
            # es ninguna de esas tres palabras.  Va en general y con el verbo que el
            # ciudadano lee.
            "Nunca afirmes que algo no existe, no se publicó, no se registró o no hay "
            "datos, registros ni documentos sobre algo que no consultaste. Si el "
            "contexto no trae resultados de una búsqueda, decí que no lo encontraste "
            "o que no lo tenés — nunca que no se publicó ni que no existe. Si te "
            "piden el detalle de un organismo y sus datos no están en el contexto, "
            "decí que no los tenés y pedí el nombre del organismo; no lo interpretes "
            "como que no publicó nada."
        )
        if system_block:
            system_content = f"{system_content}\n\n{system_block}"

        # Las reglas de citación sólo aplican a las respuestas que traen actos: el
        # resto del chat no cambia de comportamiento.  Van acá y no en el bloque fijo
        # de presupuesto porque dependen del contexto de esta query, no de la Ley.
        actos_block = build_actos_system_block((context or {}).get("actos"))
        if actos_block:
            system_content = f"{system_content}\n\n{actos_block}"

        return [
            {"role": "system", "content": system_content}
        ] + self.conversation_history[-6:] + [  # Últimos 3 turnos
            {"role": "user", "content": query + context_str}
        ]

    async def _generate_ai_response(self, query: str,
                                   context: dict[str, Any] | None = None,
                                   system_block: str | None = None,
                                   provider: LLMProvider | None = None) -> tuple[str, bool]:
        """Genera respuesta con IA, a través del provider elegido para el turno.

        Los mensajes van **enteros**, con sus roles: cada provider decide cómo
        los aplana (Gemini los une en un texto, Ollama los manda como roles
        reales).  Aplanarlos acá era lo que dejaba el bloque de sistema pegado
        al user message.

        Devuelve `(texto, lo_redactó_el_modelo)`.  El segundo valor existe
        porque el fallo del modelo sale por acá mismo con el texto de fallback:
        sin él, la burbuja declararía el proveedor sobre una respuesta que el
        proveedor nunca escribió — que es la clase de dato falso que esta
        pantalla existe para no mostrar.
        """
        messages = self._build_messages(query, context, system_block)
        usado = provider or self.provider

        try:
            texto = await usado.generate_chat(
                messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return texto, True

        except Exception as e:
            logger.error(f"Error generando respuesta con IA: {e}")
            return self._generate_fallback_response(query, context), False

    def _generate_fallback_response(self, query: str,
                                   context: dict[str, Any] | None = None) -> str:
        """Respuesta sin IA: cuando no hay modelo, o cuando el modelo falló.

        El texto dice exactamente eso.  Antes culpaba a "la API de Google", que
        ya no es la única opción ni la que se usa: un mensaje que manda al
        usuario a arreglar lo que no está roto cuesta más que no decir nada.
        """
        return (
            f"No puedo redactar una respuesta para '{query}': no hay un modelo de "
            "lenguaje disponible (Ollama local no respondió y no hay una API "
            "configurada). Los datos del panel siguen disponibles en el dashboard."
        )

    def set_firewall(self, fw: "ReferenceFirewallService") -> None:
        """Attach a ReferenceFirewallService for answer validation (Fase IV)."""
        self._firewall = fw

    def _trim_history(self) -> None:
        """Recorta el historial a `max_conversation_history` turnos (pares).

        El límite se cuenta en pares user/assistant, de ahí el `* 2`. Los turnos
        se recortan por el principio: lo viejo se va, lo reciente queda —que es lo
        que lee `_build_messages` para resolver referencias del tipo "y el mes
        anterior".
        """
        tope = self.config.max_conversation_history * 2
        if len(self.conversation_history) > tope:
            self.conversation_history = self.conversation_history[-tope:]

    def _remember_turn(self, user_message: str, assistant_message: str) -> None:
        """Cierra un turno: agrega user + assistant al historial y lo recorta.

        Se llama **después** de generar la respuesta, no antes: si el par se
        appendea antes, la query actual entra dos veces al prompt (una en el
        historial y otra como último mensaje user), y un fallo de generación
        dejaría un turno sin respuesta.

        Límite conocido: el historial vive **en memoria del proceso y es del
        proceso**, no de la sesión — `insight_agent` es un singleton del módulo
        `agents.py`, así que dos usuarios del mismo backend comparten memoria y
        un reinicio la borra. Persistencia durable / multi-usuario está fuera del
        alcance de esta historia (ver Won't de `chat-turn-memory`).
        """
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": assistant_message})
        self._trim_history()

    def clear_conversation(self) -> int:
        """Limpia el historial de conversación.

        Devuelve cuántos mensajes se borraron, para que el llamador pueda
        distinguir "limpié 4" de "ya estaba vacío" sin adivinar. Es idempotente:
        sobre un historial vacío no falla, devuelve 0.
        """
        borrados = len(self.conversation_history)
        self.conversation_history.clear()
        logger.info("Historial de conversación limpiado (%d mensajes)", borrados)
        return borrados

    async def generate_monthly_summary(self, year: int = 2025,
                                       month: int = 8) -> dict[str, Any]:
        """
        Genera resumen mensual de análisis

        Args:
            year: Año a analizar
            month: Mes a analizar

        Returns:
            Resumen mensual generado
        """
        try:
            async with AsyncSessionLocal() as db:
                # Obtener resumen mensual
                summary = await AnalysisTools.get_monthly_summary(db, year, month)

                # Generar narrativa
                narrative = f"""
                Resumen del mes {month}/{year}:
                - Documentos analizados: {summary.get('total_documents', 0)}
                - Red flags detectadas: {summary.get('total_red_flags', 0)}
                - Score promedio de transparencia: {summary.get('avg_transparency_score', 0):.1f}
                - Documentos de alto riesgo: {summary.get('high_risk_count', 0)}
                """

                logger.info(f"Resumen mensual generado para {month}/{year}")

                return {
                    "success": True,
                    "task_type": "monthly_summary",
                    "period": f"{month}/{year}",
                    "summary": summary,
                    "narrative": narrative.strip(),
                    "timestamp": datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error(f"Error generando resumen mensual: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_trend_analysis(self, start_year: int, start_month: int,
                                     end_year: int, end_month: int) -> dict[str, Any]:
        """
        Genera análisis de tendencias

        Args:
            start_year: Año inicial
            start_month: Mes inicial
            end_year: Año final
            end_month: Mes final

        Returns:
            Análisis de tendencias
        """
        try:
            async with AsyncSessionLocal() as db:
                # Obtener tendencias
                trends = await AnalysisTools.get_transparency_trends(
                    db, start_year, start_month, end_year, end_month
                )

                # Calcular cambios
                if len(trends) >= 2:
                    first_score = trends[0].get('avg_score', 0)
                    last_score = trends[-1].get('avg_score', 0)
                    change = last_score - first_score
                    change_pct = (change / first_score * 100) if first_score > 0 else 0
                else:
                    change = 0
                    change_pct = 0

                narrative = f"""
                Análisis de tendencias {start_month}/{start_year} - {end_month}/{end_year}:
                - Períodos analizados: {len(trends)}
                - Cambio en transparencia: {change:+.1f} puntos ({change_pct:+.1f}%)
                - Tendencia: {'Mejorando' if change > 0 else 'Empeorando' if change < 0 else 'Estable'}
                """

                logger.info(f"Análisis de tendencias generado: {len(trends)} períodos")

                return {
                    "success": True,
                    "task_type": "trend_analysis",
                    "period_range": f"{start_month}/{start_year} - {end_month}/{end_year}",
                    "trends": trends,
                    "change": change,
                    "change_percentage": change_pct,
                    "narrative": narrative.strip(),
                    "timestamp": datetime.utcnow().isoformat()
                }


        except Exception as e:
            logger.error(f"Error generando análisis de tendencias: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


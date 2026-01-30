"""
Insight & Reporting Agent

Genera insights accionables, reportes y responde queries en lenguaje natural
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

from app.core.agent_config import InsightReportingConfig
from agents.orchestrator.state import WorkflowState, TaskDefinition, AgentType
from agents.tools.database_tools import DatabaseTools
from agents.tools.analysis_tools import AnalysisTools

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class InsightReportingAgent:
    """
    Agente especializado en generación de insights y reportes
    
    Capacidades:
    - Agregación de métricas
    - Generación de narrativas (NLG)
    - Respuestas a queries en lenguaje natural
    - Creación de reportes
    """
    
    def __init__(self, config: Optional[InsightReportingConfig] = None):
        """
        Inicializa el agente
        
        Args:
            config: Configuración del agente
        """
        self.config = config or InsightReportingConfig()
        self.agent_type = AgentType.INSIGHT_REPORTING
        
        # Cliente OpenAI para generación de texto
        self.client = None
        if OPENAI_AVAILABLE:
            # Intentar obtener API key del config, luego de env, luego de agent_config
            api_key = os.getenv('OPENAI_API_KEY')
            
            # Si no está en env, intentar desde DEFAULT_AGENT_CONFIG
            if not api_key:
                from app.core.agent_config import DEFAULT_AGENT_CONFIG
                api_key = DEFAULT_AGENT_CONFIG.openai_api_key
            
            if api_key and api_key != "":
                self.client = AsyncOpenAI(api_key=api_key)
                logger.info("OpenAI client inicializado correctamente")
            else:
                logger.warning("OpenAI API key no encontrada - chat funcionará con fallback")
        
        # Historial de conversación
        self.conversation_history: List[Dict[str, str]] = []
        
        logger.info("InsightReportingAgent inicializado")
    
    async def execute(self, workflow: WorkflowState, 
                     task: TaskDefinition) -> Dict[str, Any]:
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
    
    async def generate_report(self, data: Dict[str, Any],
                             report_type: str = "executive") -> Dict[str, Any]:
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
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
            
            # Limitar historial
            if len(self.conversation_history) > self.config.max_conversation_history * 2:
                self.conversation_history = self.conversation_history[-self.config.max_conversation_history * 2:]
            
            # Generar respuesta
            if self.client:
                response_text = await self._generate_ai_response(query, context)
            else:
                response_text = self._generate_fallback_response(query, context)
            
            # Agregar respuesta al historial
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })
            
            return {
                "success": True,
                "query": query,
                "response": response_text,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error respondiendo query: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera un resumen ejecutivo de datos
        
        Args:
            data: Datos a resumir
        
        Returns:
            Resumen generado
        """
        return await self._generate_executive_summary(data)
    
    async def _generate_executive_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
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
    
    async def _generate_detailed_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Genera reporte detallado"""
        return {
            "success": True,
            "report_type": "detailed",
            "title": "Reporte Detallado de Análisis",
            "generated_at": datetime.utcnow().isoformat(),
            "data": data,
            "analysis": "Análisis detallado en desarrollo"
        }
    
    async def _generate_comparative_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Genera reporte comparativo"""
        return {
            "success": True,
            "report_type": "comparative",
            "title": "Reporte Comparativo",
            "generated_at": datetime.utcnow().isoformat(),
            "comparison": "Comparación en desarrollo"
        }
    
    def _extract_key_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
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
    
    async def _create_narrative(self, metrics: Dict[str, Any]) -> str:
        """Crea narrativa basada en métricas"""
        if self.client:
            return await self._generate_ai_narrative(metrics)
        else:
            return self._generate_template_narrative(metrics)
    
    async def _generate_ai_narrative(self, metrics: Dict[str, Any]) -> str:
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
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generando narrativa con IA: {e}")
            return self._generate_template_narrative(metrics)
    
    def _generate_template_narrative(self, metrics: Dict[str, Any]) -> str:
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
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
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
    
    async def query_with_data(self, query: str) -> Dict[str, Any]:
        """
        Responde una query consultando los datos reales de la base de datos
        
        Args:
            query: Pregunta del usuario
        
        Returns:
            Respuesta con datos reales
        """
        try:
            db = DatabaseTools.get_db()
            try:
                # Detectar tipo de consulta y obtener datos relevantes
                query_lower = query.lower()
                
                data_context = {}
                
                # Estadísticas generales
                if any(word in query_lower for word in ['estadísticas', 'stats', 'general', 'resumen', 'cuántos']):
                    data_context['statistics'] = DatabaseTools.get_statistics(db)
                
                # Documentos de alto riesgo
                if any(word in query_lower for word in ['riesgo', 'alto riesgo', 'crítico', 'peligroso']):
                    data_context['top_risk'] = AnalysisTools.get_top_risk_documents(db, limit=10)
                
                # Red flags
                if any(word in query_lower for word in ['red flag', 'alerta', 'problema', 'irregularidad']):
                    data_context['red_flag_distribution'] = AnalysisTools.get_red_flag_distribution(db)
                    data_context['red_flags'] = DatabaseTools.get_red_flags(db, severity='high', limit=20)
                
                # Tendencias
                if any(word in query_lower for word in ['tendencia', 'evolución', 'cambio', 'comparar']):
                    data_context['trends'] = AnalysisTools.get_transparency_trends(
                        db, 2025, 1, 2025, 11
                    )
                
                # Entidades
                if any(word in query_lower for word in ['beneficiario', 'entidad', 'empresa', 'organismo']):
                    data_context['entities'] = AnalysisTools.get_entity_analysis(db, 'beneficiaries')
                
                # Si no se encontró contexto específico, obtener estadísticas
                if not data_context:
                    data_context['statistics'] = DatabaseTools.get_statistics(db)
                
                # Generar respuesta usando IA con el contexto de datos
                response_text = await self._generate_ai_response(query, data_context)
                
                return {
                    "success": True,
                    "query": query,
                    "response": response_text,
                    "data_used": list(data_context.keys()),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error consultando datos: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    async def _generate_ai_response(self, query: str, 
                                   context: Optional[Dict[str, Any]] = None) -> str:
        """Genera respuesta con IA"""
        context_str = ""
        if context:
            context_str = f"\n\nContexto adicional:\n{str(context)}"
        
        messages = [
            {"role": "system", "content": "Eres un asistente experto en análisis de transparencia gubernamental. Responde de forma clara y concisa."}
        ] + self.conversation_history[-6:] + [  # Últimos 3 turnos
            {"role": "user", "content": query + context_str}
        ]
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generando respuesta con IA: {e}")
            return self._generate_fallback_response(query, context)
    
    def _generate_fallback_response(self, query: str, 
                                   context: Optional[Dict[str, Any]] = None) -> str:
        """Genera respuesta fallback sin IA"""
        return f"He recibido tu consulta: '{query}'. En este momento, la funcionalidad de chat requiere configurar la API de OpenAI. Por favor, consulta los datos directamente en el dashboard."
    
    def clear_conversation(self) -> None:
        """Limpia el historial de conversación"""
        self.conversation_history.clear()
        logger.info("Historial de conversación limpiado")
    
    async def generate_monthly_summary(self, year: int = 2025, 
                                       month: int = 8) -> Dict[str, Any]:
        """
        Genera resumen mensual de análisis
        
        Args:
            year: Año a analizar
            month: Mes a analizar
        
        Returns:
            Resumen mensual generado
        """
        try:
            db = DatabaseTools.get_db()
            try:
                # Obtener resumen mensual
                summary = AnalysisTools.get_monthly_summary(db, year, month)
                
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
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error generando resumen mensual: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_trend_analysis(self, start_year: int, start_month: int,
                                     end_year: int, end_month: int) -> Dict[str, Any]:
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
            db = DatabaseTools.get_db()
            try:
                # Obtener tendencias
                trends = AnalysisTools.get_transparency_trends(
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
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error generando análisis de tendencias: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


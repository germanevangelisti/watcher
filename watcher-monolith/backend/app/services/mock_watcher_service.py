"""
Servicio mock para testing sin usar la API de OpenAI
"""

import logging
from typing import Dict
import json
import random

logger = logging.getLogger(__name__)

class MockWatcherService:
    """Servicio mock que simula el análisis sin usar OpenAI."""
    
    def __init__(self):
        """Inicializa el servicio mock."""
        self.mock_responses = [
            {
                "categoria": "designaciones políticas",
                "entidad_beneficiaria": "Ministerio de Educación",
                "monto_estimado": "No especificado",
                "riesgo": "BAJO",
                "tipo_curro": "Designación administrativa estándar",
                "accion_sugerida": "Verificar antecedentes del designado y justificación del cargo"
            },
            {
                "categoria": "otros",
                "entidad_beneficiaria": "Ministerio de Ambiente",
                "monto_estimado": "No especificado",
                "riesgo": "BAJO",
                "tipo_curro": "Programa ambiental legítimo",
                "accion_sugerida": "Monitorear implementación y resultados del programa"
            },
            {
                "categoria": "gasto excesivo",
                "entidad_beneficiaria": "Organismo no especificado",
                "monto_estimado": "$50,000,000",
                "riesgo": "MEDIO",
                "tipo_curro": "Contratación sin licitación pública",
                "accion_sugerida": "Solicitar documentación completa del proceso de contratación"
            }
        ]
    
    async def analyze_content(self, content: str, metadata: Dict) -> Dict:
        """
        Simula el análisis de contenido devolviendo respuestas mock.
        
        Args:
            content: Texto a analizar
            metadata: Información contextual sobre la sección
            
        Returns:
            Resultado simulado del análisis
        """
        logger.info(f"Mock analysis for {metadata.get('boletin', 'unknown')} - {len(content)} chars")
        
        # Simular un pequeño delay
        import asyncio
        await asyncio.sleep(0.1)
        
        # Seleccionar una respuesta mock aleatoria
        response = random.choice(self.mock_responses)
        
        # Personalizar según el contenido
        if "decreto" in content.lower():
            response["categoria"] = "designaciones políticas"
        elif "programa" in content.lower():
            response["categoria"] = "otros"
        elif "licitación" in content.lower():
            response["categoria"] = "contrataciones masivas"
        
        return response

"""
Document Intelligence Agent

Extrae información estructurada de PDFs y clasifica contenido
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import re
from app.db.database import AsyncSessionLocal

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    
from app.core.agent_config import DocumentIntelligenceConfig
from agents.orchestrator.state import WorkflowState, TaskDefinition, AgentType

logger = logging.getLogger(__name__)


class DocumentIntelligenceAgent:
    """
    Agente especializado en extracción y clasificación de documentos
    
    Capacidades:
    - Extracción de texto multi-modal
    - Clasificación automática de secciones
    - Detección de entidades (NER)
    - Construcción de knowledge graph
    """
    
    def __init__(self, config: Optional[DocumentIntelligenceConfig] = None):
        """
        Inicializa el agente
        
        Args:
            config: Configuración del agente
        """
        self.config = config or DocumentIntelligenceConfig()
        self.agent_type = AgentType.DOCUMENT_INTELLIGENCE
        
        if not PDF_AVAILABLE:
            logger.warning("pdfplumber no disponible - funcionalidad limitada")
        
        logger.info("DocumentIntelligenceAgent inicializado")
    
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
        
        if task_type == "extract_document":
            return await self.extract_document(
                parameters.get("file_path"),
                parameters.get("document_id")
            )
        elif task_type == "classify_content":
            return await self.classify_content(
                parameters.get("text"),
                parameters.get("metadata", {})
            )
        elif task_type == "extract_entities":
            return await self.extract_entities(
                parameters.get("text")
            )
        elif task_type == "entity_search":
            return await self.search_entities(
                parameters.get("entity_type", "beneficiaries"),
                parameters.get("entity_value", "")
            )
        else:
            raise ValueError(f"Tipo de tarea no soportado: {task_type}")
    
    async def extract_document(self, file_path: str, 
                              document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Extrae texto y metadata de un documento PDF
        
        Args:
            file_path: Ruta al archivo PDF
            document_id: ID del documento (opcional)
        
        Returns:
            Diccionario con texto extraído y metadata
        """
        if not PDF_AVAILABLE:
            return {
                "success": False,
                "error": "pdfplumber no disponible"
            }
        
        try:
            text, num_pages = await self._extract_text_from_pdf(file_path)
            
            if not text:
                return {
                    "success": False,
                    "error": "No se pudo extraer texto del PDF"
                }
            
            # Extraer entidades
            entities = self._extract_entities(text)
            
            # Clasificar tipo de documento
            doc_type = self._classify_document_type(text)
            
            result = {
                "success": True,
                "document_id": document_id,
                "file_path": file_path,
                "text": text,
                "text_length": len(text),
                "num_pages": num_pages,
                "document_type": doc_type,
                "entities": entities,
                "metadata": {
                    "has_amounts": len(entities.get("amounts", [])) > 0,
                    "has_beneficiaries": len(entities.get("beneficiaries", [])) > 0,
                    "has_organisms": len(entities.get("organisms", [])) > 0
                }
            }
            
            logger.info(f"Documento extraído: {num_pages} páginas, {len(text)} caracteres")
            return result
            
        except Exception as e:
            logger.error(f"Error extrayendo documento {file_path}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def classify_content(self, text: str, 
                              metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Clasifica el contenido del texto
        
        Args:
            text: Texto a clasificar
            metadata: Metadata adicional
        
        Returns:
            Clasificación del contenido
        """
        doc_type = self._classify_document_type(text)
        categories = self._identify_categories(text)
        
        return {
            "document_type": doc_type,
            "categories": categories,
            "confidence": 0.8  # Placeholder - mejorar con ML
        }
    
    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extrae entidades del texto
        
        Args:
            text: Texto del que extraer entidades
        
        Returns:
            Entidades extraídas
        """
        return self._extract_entities(text)
    
    async def _extract_text_from_pdf(self, file_path: str) -> Tuple[str, int]:
        """Extrae texto completo de un PDF usando ExtractorRegistry"""
        try:
            import sys
            sys.path.insert(0, '/Users/germanevangelisti/watcher-agent/watcher-monolith/backend')
            from app.services.extractors import ExtractorRegistry
            from pathlib import Path
            
            result = await ExtractorRegistry.extract(Path(file_path))
            
            if not result.success:
                logger.error(f"Error extrayendo PDF {file_path}: {result.error}")
                return ("", 0)
            
            return (result.full_text, result.stats.total_pages)
            
        except Exception as e:
            logger.error(f"Error extrayendo PDF {file_path}: {e}")
            return ("", 0)
    
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extrae entidades del texto"""
        entities = {
            "amounts": [],
            "beneficiaries": [],
            "organisms": [],
            "dates": [],
            "contracts": []
        }
        
        # Extraer montos
        if self.config.extract_amounts:
            amounts = self._extract_amounts(text)
            entities["amounts"] = amounts
        
        # Extraer beneficiarios
        if self.config.extract_beneficiaries:
            beneficiaries = self._extract_beneficiaries(text)
            entities["beneficiaries"] = beneficiaries
        
        # Extraer organismos
        if self.config.extract_organisms:
            organisms = self._extract_organisms(text)
            entities["organisms"] = organisms
        
        # Extraer fechas
        if self.config.extract_dates:
            dates = self._extract_dates(text)
            entities["dates"] = dates
        
        return entities
    
    def _extract_amounts(self, text: str) -> List[Dict[str, Any]]:
        """Extrae montos del texto"""
        amounts = []
        
        for pattern in self.config.amount_regex_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amount_str = match.group(0)
                numeric_value = self._parse_amount_to_number(amount_str)
                
                if numeric_value and numeric_value > 0:
                    amounts.append({
                        "raw_text": amount_str,
                        "numeric_value": numeric_value,
                        "position": match.start()
                    })
        
        # Ordenar por valor y eliminar duplicados
        amounts = sorted(amounts, key=lambda x: x['numeric_value'], reverse=True)
        return amounts[:20]  # Top 20
    
    def _parse_amount_to_number(self, amount_str: str) -> Optional[float]:
        """Convierte string de monto a número"""
        try:
            clean = amount_str.replace('$', '').replace('pesos', '').replace('PESOS', '').replace('ARS', '')
            clean = clean.strip()
            
            # Manejar millones
            if 'millon' in clean.lower():
                num_part = re.search(r'[\d\.,]+', clean)
                if num_part:
                    value = float(num_part.group(0).replace('.', '').replace(',', '.'))
                    return value * 1000000
            
            # Manejar miles
            if 'mil' in clean.lower():
                num_part = re.search(r'[\d\.,]+', clean)
                if num_part:
                    value = float(num_part.group(0).replace('.', '').replace(',', '.'))
                    return value * 1000
            
            # Número directo
            clean = clean.replace('.', '').replace(',', '.')
            num_part = re.search(r'[\d\.]+', clean)
            if num_part:
                return float(num_part.group(0))
            
            return None
        except:
            return None
    
    def _extract_beneficiaries(self, text: str) -> List[str]:
        """Extrae beneficiarios/empresas"""
        beneficiaries = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            for keyword in self.config.beneficiary_keywords:
                if keyword.lower() in line.lower():
                    potential_names = self._extract_names_near(lines, i)
                    beneficiaries.extend(potential_names)
        
        # Eliminar duplicados
        beneficiaries = list(set(beneficiaries))
        return beneficiaries[:30]
    
    def _extract_names_near(self, lines: List[str], index: int) -> List[str]:
        """Extrae nombres cerca de una línea"""
        names = []
        for i in range(index, min(index + 3, len(lines))):
            line = lines[i]
            matches = re.findall(r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+', line)
            names.extend(matches)
        return names
    
    def _extract_organisms(self, text: str) -> List[str]:
        """Extrae organismos gubernamentales"""
        organisms = []
        common_organisms = [
            'Ministerio', 'Secretaría', 'Subsecretaría', 'Dirección',
            'Municipalidad', 'Gobierno', 'Legislatura', 'Tribunal'
        ]
        
        lines = text.split('\n')
        for line in lines:
            for org in common_organisms:
                if org in line:
                    organisms.append(line.strip())
                    break
        
        return list(set(organisms))[:20]
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extrae fechas"""
        dates = []
        patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}',
            r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            dates.extend(matches)
        
        return list(set(dates))[:10]
    
    def _classify_document_type(self, text: str) -> str:
        """Clasifica el tipo de documento"""
        text_lower = text.lower()
        
        # Palabras clave por tipo
        keywords = {
            "decreto": ["decreto", "decreta"],
            "resolucion": ["resolución", "resuelve"],
            "licitacion": ["licitación", "adjudicación", "oferta"],
            "designacion": ["designa", "designación", "nombra"],
            "subsidio": ["subsidio", "subvención", "ayuda económica"],
            "concurso": ["concurso", "llamado"],
            "contrato": ["contrato", "contratación"]
        }
        
        scores = {}
        for doc_type, words in keywords.items():
            score = sum(1 for word in words if word in text_lower)
            scores[doc_type] = score
        
        # Retornar tipo con mayor score
        if scores:
            best_type = max(scores, key=scores.get)
            if scores[best_type] > 0:
                return best_type
        
        return "generico"
    
    def _identify_categories(self, text: str) -> List[str]:
        """Identifica categorías del contenido"""
        categories = []
        text_lower = text.lower()
        
        category_keywords = {
            "gasto_excesivo": ["millones", "contratación", "compra"],
            "contrataciones_masivas": ["personal", "designa", "planta"],
            "subsidios": ["subsidio", "ayuda", "asistencia"],
            "obras": ["obra", "construcción", "infraestructura"],
            "transferencias": ["transferencia", "asignación"],
            "designaciones": ["designa", "nombra", "designación"]
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                categories.append(category)
        
        return categories if categories else ["otros"]
    
    async def search_entities(self, entity_type: str = "beneficiaries",
                             entity_value: str = "") -> Dict[str, Any]:
        """
        Busca entidades específicas en los documentos
        
        Args:
            entity_type: Tipo de entidad (beneficiaries, amounts, contracts)
            entity_value: Valor a buscar (opcional)
        
        Returns:
            Resultados de búsqueda
        """
        try:
            from agents.tools.analysis_tools import AnalysisTools
            
            async with AsyncSessionLocal() as db:
                # Obtener análisis de entidades
                entity_data = await AnalysisTools.get_entity_analysis(db, entity_type)
                
                # Filtrar si hay un valor de búsqueda
                if entity_value:
                    filtered = [
                        e for e in entity_data 
                        if entity_value.lower() in str(e).lower()
                    ]
                else:
                    filtered = entity_data
                
                logger.info(f"Búsqueda de entidades completada: {len(filtered)} resultados")
                
                return {
                    "success": True,
                    "task_type": "entity_search",
                    "entity_type": entity_type,
                    "search_value": entity_value,
                    "results_count": len(filtered),
                    "results": filtered[:50],  # Top 50
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error en búsqueda de entidades: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }




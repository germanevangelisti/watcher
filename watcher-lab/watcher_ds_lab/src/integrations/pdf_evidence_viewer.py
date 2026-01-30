"""
📄 PDF EVIDENCE VIEWER
Herramienta para extraer y visualizar evidencia de red flags directamente en PDFs
"""

import re
import logging
import pdfplumber
from pathlib import Path
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
import json
import sys

# Imports locales
sys.path.append(str(Path(__file__).parent.parent.parent))
from agents.detection_agent import RedFlag

logger = logging.getLogger(__name__)

@dataclass
class EvidenceCoordinate:
    """Coordenada de evidencia en PDF"""
    page: int
    x: float
    y: float
    width: float
    height: float
    text: str
    context: str

@dataclass 
class PDFEvidenceData:
    """Datos completos de evidencia en PDF"""
    red_flag_id: str
    document_path: str
    coordinates: List[EvidenceCoordinate]
    highlighted_text: List[str]
    total_pages: int
    extraction_confidence: float

class PDFEvidenceViewer:
    """
    Extractor y visualizador de evidencia en PDFs para red flags
    """
    
    def __init__(self):
        logger.info("PDFEvidenceViewer inicializado")
    
    def extract_evidence_coordinates(self, file_path: Path, red_flag: RedFlag) -> PDFEvidenceData:
        """
        Extrae coordenadas exactas de evidencia para una red flag específica
        """
        try:
            if not file_path.exists():
                logger.warning(f"PDF no encontrado: {file_path}")
                return self._create_empty_evidence(red_flag.id, str(file_path))
            
            coordinates = []
            highlighted_text = []
            total_pages = 0
            
            # Extraer keywords de búsqueda basadas en el tipo de red flag
            search_keywords = self._extract_search_keywords(red_flag)
            
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text() or ""
                    
                    # Buscar evidencia en esta página
                    page_coordinates = self._find_evidence_in_page(
                        page, page_text, search_keywords, page_num
                    )
                    
                    coordinates.extend(page_coordinates)
                    
                    # Extraer texto destacado
                    page_highlights = self._extract_highlighted_text(
                        page_text, search_keywords
                    )
                    highlighted_text.extend(page_highlights)
            
            # Calcular confianza de extracción
            confidence = self._calculate_extraction_confidence(
                coordinates, highlighted_text, red_flag
            )
            
            return PDFEvidenceData(
                red_flag_id=red_flag.id,
                document_path=str(file_path),
                coordinates=coordinates,
                highlighted_text=highlighted_text,
                total_pages=total_pages,
                extraction_confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error extrayendo evidencia de {file_path}: {e}")
            return self._create_empty_evidence(red_flag.id, str(file_path))
    
    def _extract_search_keywords(self, red_flag: RedFlag) -> List[str]:
        """
        Extrae keywords de búsqueda basadas en el tipo de red flag
        """
        keywords = []
        
        # Keywords por tipo de red flag
        flag_keywords = {
            'TRANSPARENCIA_CRITICA': [
                'urgencia', 'emergencia', 'excepcional', 'directa',
                'sin licitación', 'contratación directa'
            ],
            'MONTO_SOSPECHOSO': [
                '$', 'pesos', 'monto', 'valor', 'precio', 'costo',
                'adjudicación', 'subsidio', 'transferencia'
            ],
            'ANOMALIA_ML': [
                'irregular', 'inusual', 'excepcional', 'atípico'
            ],
            'PATRON_SECCION_INUSUAL': [
                'notificación', 'convocatoria', 'citación'
            ],
            'PATRON_ENTIDADES_OPACO': [
                'cooperativa', 'empresa', 'sociedad', 'fundación',
                'asociación', 'beneficiario', 'contratista'
            ],
            'INCONSISTENCIA_CLASIFICACION': [
                'licitación pública', 'concurso', 'transparencia',
                'proceso regular', 'marco legal'
            ]
        }
        
        # Agregar keywords específicas del tipo
        flag_type = red_flag.flag_type
        if flag_type in flag_keywords:
            keywords.extend(flag_keywords[flag_type])
        
        # Agregar evidencia de la red flag
        for evidence in red_flag.evidence:
            # Extraer números (montos, fechas, etc.)
            numbers = re.findall(r'\d+(?:\.\d{3})*(?:,\d{2})?', evidence)
            keywords.extend(numbers)
            
            # Extraer palabras clave (palabras en mayúsculas o entre comillas)
            caps_words = re.findall(r'\b[A-Z]{2,}\b', evidence)
            keywords.extend(caps_words)
        
        # Limpiar y deduplicar
        keywords = list(set([k.strip().lower() for k in keywords if len(k) > 2]))
        
        return keywords
    
    def _find_evidence_in_page(self, page, page_text: str, keywords: List[str], 
                              page_num: int) -> List[EvidenceCoordinate]:
        """
        Encuentra coordenadas de evidencia en una página específica
        """
        coordinates = []
        
        try:
            # Extraer palabras con sus coordenadas
            words = page.extract_words()
            
            for word_info in words:
                word_text = word_info.get('text', '').lower()
                
                # Verificar si la palabra coincide con alguna keyword
                for keyword in keywords:
                    if keyword in word_text or word_text in keyword:
                        # Extraer contexto alrededor de la palabra
                        context = self._extract_context(page_text, word_text, 100)
                        
                        coord = EvidenceCoordinate(
                            page=page_num,
                            x=float(word_info['x0']),
                            y=float(word_info['top']),
                            width=float(word_info['x1'] - word_info['x0']),
                            height=float(word_info['bottom'] - word_info['top']),
                            text=word_info['text'],
                            context=context
                        )
                        
                        coordinates.append(coord)
                        break  # Evitar duplicados para la misma palabra
        
        except Exception as e:
            logger.warning(f"Error extrayendo coordenadas de página {page_num}: {e}")
        
        return coordinates
    
    def _extract_highlighted_text(self, page_text: str, keywords: List[str]) -> List[str]:
        """
        Extrae fragmentos de texto que contienen keywords relevantes
        """
        highlighted = []
        
        for keyword in keywords:
            # Buscar keyword en el texto
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            matches = pattern.finditer(page_text)
            
            for match in matches:
                # Extraer contexto alrededor del match
                start = max(0, match.start() - 50)
                end = min(len(page_text), match.end() + 50)
                context = page_text[start:end].strip()
                
                # Limpiar el contexto
                context = re.sub(r'\s+', ' ', context)
                
                if len(context) > 10 and context not in highlighted:
                    highlighted.append(context)
        
        return highlighted[:5]  # Limitar a 5 fragmentos más relevantes
    
    def _extract_context(self, full_text: str, target_word: str, context_length: int = 100) -> str:
        """
        Extrae contexto alrededor de una palabra específica
        """
        try:
            # Buscar la palabra en el texto
            pattern = re.compile(re.escape(target_word), re.IGNORECASE)
            match = pattern.search(full_text)
            
            if match:
                start = max(0, match.start() - context_length)
                end = min(len(full_text), match.end() + context_length)
                context = full_text[start:end].strip()
                
                # Limpiar espacios múltiples
                context = re.sub(r'\s+', ' ', context)
                return context
            
        except Exception:
            pass
        
        return target_word
    
    def _calculate_extraction_confidence(self, coordinates: List[EvidenceCoordinate], 
                                       highlighted_text: List[str], 
                                       red_flag: RedFlag) -> float:
        """
        Calcula la confianza de la extracción de evidencia
        """
        confidence = 0.0
        
        # Base: hay coordenadas encontradas
        if coordinates:
            confidence += 0.4
        
        # Bonus: hay texto destacado
        if highlighted_text:
            confidence += 0.3
        
        # Bonus: número de evidencias encontradas
        evidence_count = len(coordinates) + len(highlighted_text)
        if evidence_count >= 3:
            confidence += 0.2
        elif evidence_count >= 1:
            confidence += 0.1
        
        # Bonus: coincidencia con evidencia de la red flag
        evidence_text = ' '.join(red_flag.evidence).lower()
        highlighted_lower = [h.lower() for h in highlighted_text]
        
        matches = sum(1 for h in highlighted_lower if any(word in h for word in evidence_text.split()))
        if matches > 0:
            confidence += min(0.2, matches * 0.05)
        
        return min(1.0, confidence)
    
    def _create_empty_evidence(self, red_flag_id: str, document_path: str) -> PDFEvidenceData:
        """
        Crea estructura de evidencia vacía
        """
        return PDFEvidenceData(
            red_flag_id=red_flag_id,
            document_path=document_path,
            coordinates=[],
            highlighted_text=[],
            total_pages=0,
            extraction_confidence=0.0
        )
    
    def generate_pdf_viewer_url(self, evidence_data: PDFEvidenceData, 
                               base_url: str = "http://localhost:8000") -> str:
        """
        Genera URL para abrir PDF con evidencia destacada
        """
        if not evidence_data.coordinates:
            return f"{base_url}/documents/{Path(evidence_data.document_path).name}"
        
        # Usar la primera coordenada como referencia
        first_coord = evidence_data.coordinates[0]
        
        # Crear parámetros para el visor PDF
        params = {
            'page': first_coord.page,
            'zoom': 150,  # Zoom al 150%
            'highlight': json.dumps([
                {
                    'x': coord.x,
                    'y': coord.y,
                    'width': coord.width,
                    'height': coord.height
                }
                for coord in evidence_data.coordinates[:5]  # Limitar a 5 destacados
            ])
        }
        
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        
        return f"{base_url}/documents/{Path(evidence_data.document_path).name}?{param_string}"
    
    def create_evidence_report(self, evidence_data: PDFEvidenceData) -> str:
        """
        Crea reporte textual de la evidencia encontrada
        """
        report = f"""
📄 REPORTE DE EVIDENCIA - {Path(evidence_data.document_path).name}
{'='*60}

Red Flag ID: {evidence_data.red_flag_id}
Confianza de extracción: {evidence_data.extraction_confidence:.1%}
Total de páginas: {evidence_data.total_pages}
Coordenadas encontradas: {len(evidence_data.coordinates)}
Texto destacado: {len(evidence_data.highlighted_text)}

📍 UBICACIONES EN PDF:
"""
        
        for i, coord in enumerate(evidence_data.coordinates[:10], 1):
            report += f"""
{i}. Página {coord.page}
   Posición: x={coord.x:.1f}, y={coord.y:.1f}
   Dimensiones: {coord.width:.1f} x {coord.height:.1f}
   Texto: "{coord.text}"
   Contexto: {coord.context[:100]}...
"""
        
        if evidence_data.highlighted_text:
            report += f"\n💡 TEXTO DESTACADO:\n"
            for i, text in enumerate(evidence_data.highlighted_text, 1):
                report += f"\n{i}. {text}\n"
        
        return report
    
    def batch_extract_evidence(self, pdf_directory: Path, 
                              red_flags: List[RedFlag]) -> Dict[str, PDFEvidenceData]:
        """
        Extrae evidencia para múltiples red flags de un directorio de PDFs
        """
        evidence_results = {}
        
        logger.info(f"Procesando evidencia para {len(red_flags)} red flags")
        
        for red_flag in red_flags:
            # Buscar PDF correspondiente
            pdf_file = pdf_directory / red_flag.document_id
            
            if not pdf_file.exists():
                # Intentar con extensión .pdf
                pdf_file = pdf_directory / f"{red_flag.document_id}"
                if not pdf_file.exists():
                    logger.warning(f"PDF no encontrado para {red_flag.document_id}")
                    continue
            
            # Extraer evidencia
            evidence_data = self.extract_evidence_coordinates(pdf_file, red_flag)
            evidence_results[red_flag.id] = evidence_data
            
            logger.info(f"Evidencia extraída para {red_flag.document_id}: "
                       f"{len(evidence_data.coordinates)} coordenadas, "
                       f"confianza: {evidence_data.extraction_confidence:.1%}")
        
        return evidence_results

def main():
    """
    Script de prueba para el visualizador de evidencia
    """
    print("📄 Probando PDFEvidenceViewer...")
    
    viewer = PDFEvidenceViewer()
    
    # Crear red flag de ejemplo
    from agents.detection_agent import RedFlag
    import datetime
    
    test_flag = RedFlag(
        id="TEST_001",
        timestamp=datetime.datetime.now(),
        document_id="20250801_2_Secc.pdf",
        flag_type="TRANSPARENCIA_CRITICA",
        severity="CRITICO",
        confidence=0.9,
        description="Score de transparencia crítico: 16.0/100",
        evidence=["Score transparencia: 16.0", "Montos: 220", "Entidades: 169"],
        recommendation="Auditoría manual inmediata requerida",
        transparency_score=16.0,
        risk_factors={"transparency_score": 16.0},
        metadata={"test": True}
    )
    
    # Ruta de ejemplo (ajustar según ubicación real)
    pdf_path = Path("/Users/germanevangelisti/watcher-agent/watcher-monolith/backend/data/raw/20250801_2_Secc.pdf")
    
    if pdf_path.exists():
        evidence = viewer.extract_evidence_coordinates(pdf_path, test_flag)
        
        print(f"\n✅ Evidencia extraída:")
        print(f"  • Coordenadas: {len(evidence.coordinates)}")
        print(f"  • Texto destacado: {len(evidence.highlighted_text)}")
        print(f"  • Confianza: {evidence.extraction_confidence:.1%}")
        
        # Generar URL del visor
        url = viewer.generate_pdf_viewer_url(evidence)
        print(f"  • URL del visor: {url}")
        
        # Crear reporte
        report = viewer.create_evidence_report(evidence)
        print(f"\n📄 Reporte de evidencia:\n{report[:500]}...")
        
    else:
        print(f"⚠️ PDF de prueba no encontrado: {pdf_path}")
        print("   Ajustar la ruta en el script para probar con un PDF real")

if __name__ == "__main__":
    main()

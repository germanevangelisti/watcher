"""
Servicio de Extracción de Menciones Jurisdiccionales
Identifica referencias a municipalidades y comunas en el texto de boletines.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Jurisdiccion

logger = logging.getLogger(__name__)


class MencionExtractor:
    """
    Extractor de menciones jurisdiccionales en texto.
    
    Identifica referencias a municipalidades, comunas y otras jurisdicciones
    en el texto de boletines oficiales usando patrones de regex y NLP básico.
    """
    
    def __init__(self):
        """Inicializa el extractor."""
        self.jurisdicciones_cache: List[Dict] = []
        self.patrones_tipo: Dict[str, re.Pattern] = {}
        self._compilar_patrones()
    
    def _compilar_patrones(self):
        """Compila patrones regex para detección de tipo de mención."""
        self.patrones_tipo = {
            "decreto": re.compile(
                r'\b(DECRETO|Dec\.?|D\.?)\s*N[°º]?\s*\d+',
                re.IGNORECASE
            ),
            "resolucion": re.compile(
                r'\b(RESOLUCIÓN|RESOLUCION|Res\.?|R\.?)\s*N[°º]?\s*\d+',
                re.IGNORECASE
            ),
            "ordenanza": re.compile(
                r'\b(ORDENANZA|Ord\.?|O\.?)\s*N[°º]?\s*\d+',
                re.IGNORECASE
            ),
            "licitacion": re.compile(
                r'\b(LICITACI[ÓO]N|Lic\.?|L\.P\.?)\s*(P[ÚU]BLICA|PRIVADA)?',
                re.IGNORECASE
            ),
            "contratacion": re.compile(
                r'\b(CONTRATACI[ÓO]N|ADQUISICI[ÓO]N)',
                re.IGNORECASE
            ),
            "convenio": re.compile(
                r'\b(CONVENIO|ACUERDO)',
                re.IGNORECASE
            ),
            "subsidio": re.compile(
                r'\b(SUBSIDIO|AYUDA|TRANSFERENCIA)',
                re.IGNORECASE
            ),
            "designacion": re.compile(
                r'\b(DESIGNA[RN]|NOMBRAMIENTO|DESIGNACI[ÓO]N)',
                re.IGNORECASE
            ),
        }
    
    async def load_jurisdicciones(self, db: AsyncSession):
        """
        Carga jurisdicciones desde la base de datos para búsqueda.
        
        Args:
            db: Sesión de base de datos
        """
        try:
            query = select(Jurisdiccion)
            result = await db.execute(query)
            jurisdicciones = result.scalars().all()
            
            self.jurisdicciones_cache = [
                {
                    "id": j.id,
                    "nombre": j.nombre,
                    "tipo": j.tipo,
                    "variantes": self._generar_variantes_nombre(j.nombre)
                }
                for j in jurisdicciones
                if j.tipo in ["municipalidad", "comuna", "capital"]  # Excluir provincia
            ]
            
            logger.info(f"Cargadas {len(self.jurisdicciones_cache)} jurisdicciones para extracción")
            
        except Exception as e:
            logger.error(f"Error cargando jurisdicciones: {e}")
            self.jurisdicciones_cache = []
    
    def _generar_variantes_nombre(self, nombre: str) -> List[str]:
        """
        Genera variantes del nombre de una jurisdicción para búsqueda.
        
        Args:
            nombre: Nombre original de la jurisdicción
            
        Returns:
            Lista de variantes del nombre
        """
        variantes = [nombre]
        
        # Variante sin "Ciudad de" o "Municipalidad de"
        nombre_limpio = re.sub(
            r'^(Ciudad de|Municipalidad de|Comuna de)\s+',
            '',
            nombre,
            flags=re.IGNORECASE
        )
        if nombre_limpio != nombre:
            variantes.append(nombre_limpio)
        
        # Variante con "Municipalidad de" o "Ciudad de"
        if not nombre.lower().startswith(("ciudad de", "municipalidad de", "comuna de")):
            variantes.extend([
                f"Municipalidad de {nombre}",
                f"Ciudad de {nombre}",
                f"Comuna de {nombre}"
            ])
        
        # Variante sin acentos
        nombre_sin_acentos = self._remover_acentos(nombre)
        if nombre_sin_acentos != nombre:
            variantes.append(nombre_sin_acentos)
        
        return list(set(variantes))  # Eliminar duplicados
    
    def _remover_acentos(self, texto: str) -> str:
        """Remueve acentos de un texto."""
        reemplazos = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'ñ': 'n', 'Ñ': 'N'
        }
        for acento, sin_acento in reemplazos.items():
            texto = texto.replace(acento, sin_acento)
        return texto
    
    def extraer_menciones(
        self,
        texto: str,
        contexto_chars: int = 200
    ) -> List[Dict]:
        """
        Extrae menciones de jurisdicciones en un texto.
        
        Args:
            texto: Texto donde buscar menciones
            contexto_chars: Caracteres de contexto alrededor de la mención
            
        Returns:
            Lista de menciones encontradas con metadatos
        """
        if not self.jurisdicciones_cache:
            logger.warning("No hay jurisdicciones cargadas. Llamar load_jurisdicciones() primero.")
            return []
        
        menciones = []
        
        # Normalizar texto
        texto_normalizado = self._normalizar_texto(texto)
        
        for jurisdiccion in self.jurisdicciones_cache:
            for variante in jurisdiccion["variantes"]:
                # Buscar todas las ocurrencias de esta variante
                ocurrencias = self._buscar_ocurrencias(
                    texto_normalizado,
                    variante,
                    contexto_chars
                )
                
                for posicion, fragmento in ocurrencias:
                    # Determinar tipo de mención
                    tipo_mencion = self._clasificar_tipo_mencion(fragmento)
                    
                    # Evitar duplicados (misma jurisdicción en posiciones cercanas)
                    if not self._es_duplicado(menciones, jurisdiccion["id"], posicion):
                        menciones.append({
                            "jurisdiccion_id": jurisdiccion["id"],
                            "jurisdiccion_nombre": jurisdiccion["nombre"],
                            "tipo_jurisdiccion": jurisdiccion["tipo"],
                            "tipo_mencion": tipo_mencion,
                            "fragmento_texto": fragmento.strip(),
                            "posicion": posicion,
                            "variante_encontrada": variante
                        })
        
        # Ordenar por posición en el texto
        menciones.sort(key=lambda x: x["posicion"])
        
        logger.info(f"Encontradas {len(menciones)} menciones en el texto")
        return menciones
    
    def _normalizar_texto(self, texto: str) -> str:
        """Normaliza el texto para búsqueda."""
        # Remover múltiples espacios
        texto = re.sub(r'\s+', ' ', texto)
        # Remover caracteres especiales que puedan interferir
        texto = texto.replace('\n', ' ').replace('\r', ' ')
        return texto
    
    def _buscar_ocurrencias(
        self,
        texto: str,
        patron: str,
        contexto_chars: int
    ) -> List[Tuple[int, str]]:
        """
        Busca todas las ocurrencias de un patrón en el texto.
        
        Args:
            texto: Texto donde buscar
            patron: Patrón a buscar
            contexto_chars: Caracteres de contexto
            
        Returns:
            Lista de tuplas (posicion, fragmento_con_contexto)
        """
        ocurrencias = []
        
        # Búsqueda case-insensitive
        patron_regex = re.compile(re.escape(patron), re.IGNORECASE)
        
        for match in patron_regex.finditer(texto):
            posicion = match.start()
            
            # Extraer contexto alrededor
            inicio = max(0, posicion - contexto_chars)
            fin = min(len(texto), posicion + len(patron) + contexto_chars)
            
            fragmento = texto[inicio:fin]
            
            ocurrencias.append((posicion, fragmento))
        
        return ocurrencias
    
    def _clasificar_tipo_mencion(self, fragmento: str) -> str:
        """
        Clasifica el tipo de mención según el contexto.
        
        Args:
            fragmento: Fragmento de texto con la mención
            
        Returns:
            Tipo de mención identificado
        """
        # Buscar patrones de tipo en el fragmento
        for tipo, patron in self.patrones_tipo.items():
            if patron.search(fragmento):
                return tipo
        
        # Si no se encuentra patrón específico, clasificar como "referencia_general"
        return "referencia_general"
    
    def _es_duplicado(
        self,
        menciones: List[Dict],
        jurisdiccion_id: int,
        posicion: int,
        threshold: int = 50
    ) -> bool:
        """
        Verifica si una mención es duplicada (misma jurisdicción muy cercana).
        
        Args:
            menciones: Lista de menciones ya encontradas
            jurisdiccion_id: ID de la jurisdicción actual
            posicion: Posición en el texto
            threshold: Umbral de distancia para considerar duplicado
            
        Returns:
            True si es duplicado, False en caso contrario
        """
        for mencion in menciones:
            if mencion["jurisdiccion_id"] == jurisdiccion_id:
                if abs(mencion["posicion"] - posicion) < threshold:
                    return True
        return False
    
    def generar_resumen_menciones(self, menciones: List[Dict]) -> Dict:
        """
        Genera un resumen estadístico de las menciones encontradas.
        
        Args:
            menciones: Lista de menciones
            
        Returns:
            Diccionario con resumen estadístico
        """
        if not menciones:
            return {
                "total_menciones": 0,
                "jurisdicciones_mencionadas": 0,
                "por_tipo_mencion": {},
                "por_tipo_jurisdiccion": {},
                "jurisdicciones_destacadas": []
            }
        
        # Contar por tipo de mención
        por_tipo_mencion = {}
        for mencion in menciones:
            tipo = mencion["tipo_mencion"]
            por_tipo_mencion[tipo] = por_tipo_mencion.get(tipo, 0) + 1
        
        # Contar por tipo de jurisdicción
        por_tipo_jurisdiccion = {}
        for mencion in menciones:
            tipo = mencion["tipo_jurisdiccion"]
            por_tipo_jurisdiccion[tipo] = por_tipo_jurisdiccion.get(tipo, 0) + 1
        
        # Identificar jurisdicciones más mencionadas
        conteo_jurisdicciones = {}
        for mencion in menciones:
            jid = mencion["jurisdiccion_id"]
            if jid not in conteo_jurisdicciones:
                conteo_jurisdicciones[jid] = {
                    "id": jid,
                    "nombre": mencion["jurisdiccion_nombre"],
                    "count": 0
                }
            conteo_jurisdicciones[jid]["count"] += 1
        
        jurisdicciones_destacadas = sorted(
            conteo_jurisdicciones.values(),
            key=lambda x: x["count"],
            reverse=True
        )[:5]  # Top 5
        
        return {
            "total_menciones": len(menciones),
            "jurisdicciones_mencionadas": len(conteo_jurisdicciones),
            "por_tipo_mencion": por_tipo_mencion,
            "por_tipo_jurisdiccion": por_tipo_jurisdiccion,
            "jurisdicciones_destacadas": jurisdicciones_destacadas
        }


# Singleton global
_extractor_instance: Optional[MencionExtractor] = None


def get_mencion_extractor() -> MencionExtractor:
    """Obtiene la instancia global del extractor de menciones."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = MencionExtractor()
    return _extractor_instance

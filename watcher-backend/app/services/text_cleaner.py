"""
Text Cleaning Service - Normaliza y limpia texto extraído de PDFs

Este servicio maneja:
- Corrección de encoding con ftfy (mojibake)
- Normalización Unicode (NFKC)
- Limpieza de whitespace
- Remoción de artifacts comunes de PDFs
- Normalización específica para boletines oficiales
"""

import logging
import re
import unicodedata
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    import ftfy
    FTFY_AVAILABLE = True
except ImportError:
    logger.warning("ftfy not installed. Install with: pip install ftfy")
    FTFY_AVAILABLE = False


class CleaningConfig(BaseModel):
    """Configuración de limpieza de texto."""
    fix_encoding: bool = True
    normalize_unicode: bool = True
    normalize_whitespace: bool = True
    remove_artifacts: bool = True
    normalize_legal_text: bool = True


class TextCleaner:
    """
    Servicio para limpieza y normalización de texto extraído de PDFs.
    
    Aplica múltiples pasos de limpieza configurables para mejorar
    la calidad del texto antes del chunking y embedding.
    """
    
    def __init__(self, config: Optional[CleaningConfig] = None):
        """
        Inicializar TextCleaner.
        
        Args:
            config: Configuración de limpieza (usa defaults si no se proporciona)
        """
        self.config = config or CleaningConfig()
        
        if self.config.fix_encoding and not FTFY_AVAILABLE:
            logger.warning("ftfy no disponible, fix_encoding será ignorado")
            self.config.fix_encoding = False
    
    def clean(self, text: str) -> str:
        """
        Pipeline completo de limpieza de texto.
        
        Args:
            text: Texto a limpiar
            
        Returns:
            Texto limpio
        """
        if not text:
            return text
        
        cleaned = text
        
        # 1. Corregir encoding (mojibake)
        if self.config.fix_encoding:
            cleaned = self.fix_encoding(cleaned)
        
        # 2. Normalizar Unicode
        if self.config.normalize_unicode:
            cleaned = self.normalize_unicode(cleaned)
        
        # 3. Remover artifacts de PDF
        if self.config.remove_artifacts:
            cleaned = self.remove_artifacts(cleaned)
        
        # 4. Normalizar whitespace
        if self.config.normalize_whitespace:
            cleaned = self.normalize_whitespace(cleaned)
        
        # 5. Normalización específica de boletines
        if self.config.normalize_legal_text:
            cleaned = self.normalize_legal_text(cleaned)
        
        return cleaned
    
    def fix_encoding(self, text: str) -> str:
        """
        Corregir problemas de encoding (mojibake) usando ftfy.
        
        Args:
            text: Texto con posibles problemas de encoding
            
        Returns:
            Texto con encoding corregido
        """
        if not FTFY_AVAILABLE:
            return text
        
        try:
            # ftfy.fix_text corrige múltiples problemas de encoding
            fixed = ftfy.fix_text(text)
            return fixed
        except Exception as e:
            logger.warning(f"Error corrigiendo encoding: {e}")
            return text
    
    def normalize_unicode(self, text: str) -> str:
        """
        Normalizar Unicode a forma NFKC (compatibilidad).
        
        NFKC combina caracteres compuestos y normaliza variantes.
        Ejemplo: "ñ" (dos caracteres) -> "ñ" (un caracter)
        
        Args:
            text: Texto a normalizar
            
        Returns:
            Texto normalizado
        """
        try:
            # NFKC: Compatibility Decomposition + Canonical Composition
            normalized = unicodedata.normalize('NFKC', text)
            return normalized
        except Exception as e:
            logger.warning(f"Error normalizando unicode: {e}")
            return text
    
    def normalize_whitespace(self, text: str) -> str:
        """
        Normalizar espacios en blanco y saltos de línea.
        
        - Colapsa múltiples espacios en uno
        - Normaliza diferentes tipos de espacios a espacio estándar
        - Colapsa múltiples saltos de línea (más de 3) a 2
        - Remueve espacios al inicio/fin de líneas
        
        Args:
            text: Texto a normalizar
            
        Returns:
            Texto con whitespace normalizado
        """
        # Reemplazar diferentes tipos de espacios con espacio estándar
        # \u00a0 = non-breaking space, \u2003 = em space, etc.
        text = re.sub(r'[\u00a0\u2003\u2002\u2009]', ' ', text)
        
        # Colapsar múltiples espacios en uno (pero no newlines)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Remover espacios al inicio/fin de cada línea
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        text = '\n'.join(lines)
        
        # Colapsar más de 3 newlines consecutivos a 2
        text = re.sub(r'\n{4,}', '\n\n', text)
        
        # Remover espacios/tabs antes de newlines
        text = re.sub(r'[ \t]+\n', '\n', text)
        
        return text.strip()
    
    def remove_artifacts(self, text: str) -> str:
        """
        Remover artifacts comunes de PDFs.
        
        - Números de página sueltos
        - Headers/footers repetidos
        - Líneas de guiones o underscores repetidos
        - Marcas de agua comunes
        
        Args:
            text: Texto con posibles artifacts
            
        Returns:
            Texto sin artifacts
        """
        # Remover líneas que son solo números (números de página)
        # Pero solo si están solas en una línea
        text = re.sub(r'^\s*\d{1,4}\s*$', '', text, flags=re.MULTILINE)
        
        # Remover líneas de solo guiones/underscores (separadores visuales)
        text = re.sub(r'^[\-_=]{3,}\s*$', '', text, flags=re.MULTILINE)
        
        # Remover patrones comunes de headers/footers
        # Ejemplo: "Página 5 de 100" o "Boletín Oficial - 2025"
        text = re.sub(
            r'^\s*(página|pág\.?|page)\s+\d+\s*(de|of|/)?\s*\d*\s*$',
            '',
            text,
            flags=re.MULTILINE | re.IGNORECASE
        )
        
        # Remover marcas de agua comunes
        text = re.sub(
            r'^\s*(COPIA\s+)?CONTROLADA\s*$',
            '',
            text,
            flags=re.MULTILINE | re.IGNORECASE
        )
        
        text = re.sub(
            r'^\s*DOCUMENTO\s+OFICIAL\s*$',
            '',
            text,
            flags=re.MULTILINE | re.IGNORECASE
        )
        
        return text
    
    def normalize_legal_text(self, text: str) -> str:
        """
        Normalización específica para boletines oficiales.
        
        - Normaliza abreviaturas comunes (Art., Inc., etc.)
        - Normaliza formato de artículos y decretos
        - Normaliza símbolos de moneda
        
        Args:
            text: Texto legal a normalizar
            
        Returns:
            Texto normalizado
        """
        # Normalizar abreviaturas comunes
        # Art. -> ARTICULO (para facilitar chunking por artículo)
        text = re.sub(r'\bArt\.\s+', 'ARTICULO ', text, flags=re.IGNORECASE)
        text = re.sub(r'\bArtículo\b', 'ARTICULO', text, flags=re.IGNORECASE)
        
        # Inc. -> INCISO
        text = re.sub(r'\bInc\.\s+', 'INCISO ', text, flags=re.IGNORECASE)
        
        # Normalizar "Decreto N°" o "Decreto Nº" a "DECRETO"
        text = re.sub(
            r'\bDecreto\s+N[°º]\s*',
            'DECRETO ',
            text,
            flags=re.IGNORECASE
        )
        
        # Normalizar "Resolución N°" a "RESOLUCION"
        text = re.sub(
            r'\bResolución\s+N[°º]\s*',
            'RESOLUCION ',
            text,
            flags=re.IGNORECASE
        )
        
        # Normalizar símbolos de moneda
        # Convertir $ a "pesos" para mejor procesamiento
        # Pero solo si está seguido de números
        text = re.sub(r'\$\s*(\d)', r'pesos \1', text)
        
        return text


# Instancia global por defecto
_text_cleaner: Optional[TextCleaner] = None


def get_text_cleaner(config: Optional[CleaningConfig] = None) -> TextCleaner:
    """
    Obtener instancia global de TextCleaner.
    
    Args:
        config: Configuración opcional (solo se usa en primera llamada)
        
    Returns:
        Instancia de TextCleaner
    """
    global _text_cleaner
    
    if _text_cleaner is None:
        _text_cleaner = TextCleaner(config)
    
    return _text_cleaner

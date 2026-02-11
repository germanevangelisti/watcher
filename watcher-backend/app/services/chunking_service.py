"""
Chunking Service - Divide texto en chunks con estrategia recursiva

Este servicio maneja:
- Chunking recursivo con separadores jerárquicos
- Separadores específicos para boletines oficiales
- Metadata de chunks (índice, posición, tamaño)
- Configuración flexible de tamaño y overlap
"""

import logging
import re
from typing import List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ChunkingConfig(BaseModel):
    """Configuración de chunking."""
    chunk_size: int = Field(default=1000, gt=0, description="Tamaño del chunk en caracteres")
    chunk_overlap: int = Field(default=200, ge=0, description="Overlap entre chunks")
    min_chunk_size: int = Field(default=100, gt=0, description="Tamaño mínimo de chunk")
    strategy: str = Field(default="recursive", description="Estrategia de chunking")
    
    # Separadores jerárquicos (de mayor a menor prioridad)
    separators: List[str] = Field(
        default=[
            # Separadores estructurales de boletines oficiales
            "\nARTICULO ",
            "\nDECRETO ",
            "\nRESOLUCION ",
            "\n---\n",
            # Separadores de párrafos
            "\n\n\n",
            "\n\n",
            # Separadores de línea
            "\n",
            # Separadores de oración
            ". ",
            # Separador de última instancia
            " ",
        ],
        description="Separadores jerárquicos"
    )


class ChunkResult(BaseModel):
    """Resultado de chunking con metadata."""
    text: str = Field(description="Texto del chunk")
    chunk_index: int = Field(description="Índice del chunk (0-based)")
    start_char: int = Field(description="Posición inicial en el texto original")
    end_char: int = Field(description="Posición final en el texto original")
    num_chars: int = Field(description="Número de caracteres en el chunk")
    
    class Config:
        frozen = False  # Allow modification


class ChunkingService:
    """
    Servicio para dividir texto en chunks con estrategia recursiva.
    
    Implementa una estrategia similar a RecursiveCharacterTextSplitter
    de langchain, pero adaptada a boletines oficiales argentinos.
    """
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        """
        Inicializar ChunkingService.
        
        Args:
            config: Configuración de chunking (usa defaults si no se proporciona)
        """
        self.config = config or ChunkingConfig()
    
    def chunk(self, text: str, config: Optional[ChunkingConfig] = None) -> List[ChunkResult]:
        """
        Dividir texto en chunks usando estrategia recursiva.
        
        Args:
            text: Texto a dividir
            config: Configuración opcional (override del constructor)
            
        Returns:
            Lista de ChunkResult con metadata
        """
        if not text:
            return []
        
        cfg = config or self.config
        
        # Dividir usando estrategia recursiva
        chunks_text = self._recursive_split(text, cfg)
        
        # Crear ChunkResult con metadata
        results = []
        current_pos = 0
        
        for i, chunk_text in enumerate(chunks_text):
            # Encontrar la posición del chunk en el texto original
            # (necesario porque hay overlap)
            start_pos = text.find(chunk_text, current_pos)
            
            if start_pos == -1:
                # Fallback: usar posición actual
                start_pos = current_pos
            
            end_pos = start_pos + len(chunk_text)
            
            result = ChunkResult(
                text=chunk_text,
                chunk_index=i,
                start_char=start_pos,
                end_char=end_pos,
                num_chars=len(chunk_text)
            )
            results.append(result)
            
            # Actualizar posición para el próximo chunk
            # Restar el overlap para que la búsqueda empiece en el área correcta
            current_pos = end_pos - cfg.chunk_overlap
            if current_pos < 0:
                current_pos = 0
        
        logger.info(f"Texto dividido en {len(results)} chunks")
        return results
    
    def _recursive_split(self, text: str, config: ChunkingConfig) -> List[str]:
        """
        Divide texto recursivamente usando separadores jerárquicos.
        
        Args:
            text: Texto a dividir
            config: Configuración de chunking
            
        Returns:
            Lista de chunks como strings
        """
        chunks = []
        
        # Si el texto es suficientemente pequeño, retornarlo directamente
        if len(text) <= config.chunk_size:
            if len(text) >= config.min_chunk_size:
                return [text]
            else:
                return []
        
        # Intentar con cada separador en orden
        for separator in config.separators:
            if separator in text:
                splits = self._split_text_by_separator(text, separator)
                
                # Procesar cada split
                temp_chunks = []
                current_chunk = []
                current_size = 0
                
                for split in splits:
                    split_size = len(split)
                    
                    # Si un solo split es muy grande, dividirlo recursivamente
                    if split_size > config.chunk_size:
                        # Primero, guardar el chunk actual si existe
                        if current_chunk:
                            temp_chunks.append(separator.join(current_chunk))
                            current_chunk = []
                            current_size = 0
                        
                        # Dividir recursivamente con el siguiente separador
                        remaining_seps = config.separators[config.separators.index(separator) + 1:]
                        if remaining_seps:
                            sub_config = ChunkingConfig(
                                chunk_size=config.chunk_size,
                                chunk_overlap=config.chunk_overlap,
                                min_chunk_size=config.min_chunk_size,
                                strategy=config.strategy,
                                separators=remaining_seps
                            )
                            sub_chunks = self._recursive_split(split, sub_config)
                            temp_chunks.extend(sub_chunks)
                        else:
                            # Último separador: dividir por tamaño fijo
                            temp_chunks.extend(self._split_by_size(split, config.chunk_size))
                        
                        continue
                    
                    # Si agregar este split excede el tamaño, guardar chunk actual
                    if current_chunk and current_size + split_size > config.chunk_size:
                        temp_chunks.append(separator.join(current_chunk))
                        
                        # Mantener overlap: incluir el último split del chunk anterior
                        if config.chunk_overlap > 0 and current_chunk:
                            current_chunk = [current_chunk[-1], split]
                            current_size = len(current_chunk[-2]) + split_size
                        else:
                            current_chunk = [split]
                            current_size = split_size
                    else:
                        # Agregar split al chunk actual
                        current_chunk.append(split)
                        current_size += split_size
                
                # Agregar el último chunk
                if current_chunk:
                    temp_chunks.append(separator.join(current_chunk))
                
                # Filtrar chunks muy pequeños
                chunks = [c for c in temp_chunks if len(c) >= config.min_chunk_size]
                
                if chunks:
                    return chunks
        
        # Si no se pudo dividir con separadores, dividir por tamaño fijo
        return self._split_by_size(text, config.chunk_size)
    
    def _split_text_by_separator(self, text: str, separator: str) -> List[str]:
        """
        Divide texto por separador, manteniendo el separador.
        
        Args:
            text: Texto a dividir
            separator: Separador
            
        Returns:
            Lista de partes
        """
        if separator == " ":
            # Caso especial: dividir por espacio es simplemente split
            return text.split(separator)
        
        # Dividir manteniendo el separador
        parts = text.split(separator)
        
        # Re-agregar el separador excepto en la primera parte
        result = []
        for i, part in enumerate(parts):
            if i == 0:
                result.append(part)
            else:
                result.append(part)  # El separador se agregará al hacer join
        
        return [p for p in result if p]  # Filtrar vacíos
    
    def _split_by_size(self, text: str, chunk_size: int) -> List[str]:
        """
        Divide texto por tamaño fijo (último recurso).
        
        Args:
            text: Texto a dividir
            chunk_size: Tamaño de cada chunk
            
        Returns:
            Lista de chunks
        """
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            if chunk:
                chunks.append(chunk)
        return chunks


# Instancia global por defecto
_chunking_service: Optional[ChunkingService] = None


def get_chunking_service(config: Optional[ChunkingConfig] = None) -> ChunkingService:
    """
    Obtener instancia global de ChunkingService.
    
    Args:
        config: Configuración opcional (solo se usa en primera llamada)
        
    Returns:
        Instancia de ChunkingService
    """
    global _chunking_service
    
    if _chunking_service is None:
        _chunking_service = ChunkingService(config)
    
    return _chunking_service

"""
Document Processor - Procesa documentos subidos paso a paso

Pipeline: Upload → Extract Text → Generate Embeddings → Mark as Processed

DEPRECADO: Este módulo se mantiene por compatibilidad.
Usar ExtractorRegistry para extracción de texto.
"""

from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import warnings

from ..db.models import RequiredDocument

# Deprecation warning
warnings.warn(
    "document_processor.DocumentProcessor está deprecado para extracción. "
    "Usar ExtractorRegistry de app.services.extractors en su lugar.",
    DeprecationWarning,
    stacklevel=2
)


class DocumentProcessor:
    """Procesador de documentos con pipeline paso a paso"""
    
    def __init__(self):
        try:
            import tiktoken
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            self.encoding = None
    
    def extract_text_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Extrae texto de un PDF usando ExtractorRegistry (wrapper de compatibilidad).
        DEPRECADO: Usar ExtractorRegistry directamente.
        
        NOTA: En notebooks, usar extract_text_from_pdf_async()
        
        Retorna diccionario con texto, páginas, y estadísticas.
        """
        import asyncio
        from app.services.extractors import ExtractorRegistry
        
        try:
            # Ejecutar extracción async
            try:
                _loop = asyncio.get_running_loop()
                # Si llegamos aquí, hay un loop activo (ej. Jupyter)
                raise RuntimeError(
                    "Este método no puede ejecutarse en un event loop activo. "
                    "Usar 'await processor.extract_text_from_pdf_async(path)' en su lugar."
                )
            except RuntimeError as e:
                if "no running event loop" in str(e).lower() or "no current event loop" in str(e).lower():
                    result = asyncio.run(ExtractorRegistry.extract(Path(file_path)))
                else:
                    raise
            
            if not result.success:
                return {
                    "success": False,
                    "error": result.error,
                    "file_path": file_path
                }
            
            # Convertir ExtractedContent al formato legacy
            pages_text = []
            for page in result.pages:
                pages_text.append({
                    "page_number": page.page_number,
                    "text": page.text,
                    "char_count": page.char_count
                })
            
            return {
                "success": True,
                "file_path": file_path,
                "num_pages": result.stats.total_pages,
                "total_chars": result.stats.total_chars,
                "total_tokens": result.stats.total_tokens,
                "pages": pages_text,
                "full_text": result.full_text,
                "preview": result.full_text[:1000] + "..." if len(result.full_text) > 1000 else result.full_text,
                "extracted_at": result.extracted_at.isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    async def extract_text_from_pdf_async(self, file_path: str) -> Dict[str, Any]:
        """
        Versión async del extractor de texto.
        Usar esta versión en notebooks y código async.
        """
        from app.services.extractors import ExtractorRegistry
        
        try:
            result = await ExtractorRegistry.extract(Path(file_path))
            
            if not result.success:
                return {
                    "success": False,
                    "error": result.error,
                    "file_path": file_path
                }
            
            # Convertir ExtractedContent al formato legacy
            pages_text = []
            for page in result.pages:
                pages_text.append({
                    "page_number": page.page_number,
                    "text": page.text,
                    "char_count": page.char_count
                })
            
            return {
                "success": True,
                "file_path": file_path,
                "num_pages": result.stats.total_pages,
                "total_chars": result.stats.total_chars,
                "total_tokens": result.stats.total_tokens,
                "pages": pages_text,
                "full_text": result.full_text,
                "preview": result.full_text[:1000] + "..." if len(result.full_text) > 1000 else result.full_text,
                "extracted_at": result.extracted_at.isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """
        Divide texto en chunks con overlap para embeddings.
        
        DEPRECATED: This method is deprecated. Use ChunkingService instead.
        Kept for backward compatibility only.
        """
        import warnings
        warnings.warn(
            "DocumentProcessor.chunk_text() is deprecated. Use ChunkingService instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Try to use ChunkingService
        try:
            from .chunking_service import ChunkingService, ChunkingConfig
            service = ChunkingService()
            config = ChunkingConfig(chunk_size=chunk_size, chunk_overlap=overlap)
            chunk_results = service.chunk(text, config)
            
            # Convert to old format for compatibility
            return [
                {
                    "chunk_id": cr.chunk_index,
                    "text": cr.text,
                    "start_token": cr.start_char // 4,  # Approximation
                    "end_token": cr.end_char // 4,
                    "num_tokens": cr.num_chars // 4
                }
                for cr in chunk_results
            ]
        except ImportError:
            pass
        
        # Fallback to legacy implementation
        if not self.encoding:
            # Sin tiktoken, hacer chunking por caracteres
            chunks = []
            chunk_id = 0
            start = 0
            text_len = len(text)
            
            while start < text_len:
                end = min(start + chunk_size * 4, text_len)  # Aproximación: 1 token ~ 4 chars
                chunk_text = text[start:end]
                
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "start_token": start // 4,
                    "end_token": end // 4,
                    "num_tokens": len(chunk_text) // 4
                })
                
                chunk_id += 1
                start = end - (overlap * 4)
            
            return chunks
        
        tokens = self.encoding.encode(text)
        chunks = []
        
        start = 0
        chunk_id = 0
        
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "start_token": start,
                "end_token": end,
                "num_tokens": len(chunk_tokens)
            })
            
            chunk_id += 1
            start = end - overlap  # Overlap para mantener contexto
        
        return chunks
    
    async def generate_embeddings(
        self, 
        text: str, 
        google_client=None,
        model: str = "models/gemini-embedding-001"
    ) -> Dict[str, Any]:
        """
        Genera embeddings para el texto usando Google AI.
        Divide en chunks y genera embedding por cada uno.
        """
        try:
            import google.generativeai as genai
            import os
            import logging
            
            logger = logging.getLogger(__name__)
            logger.info(f"🔄 Iniciando generate_embeddings con modelo: {model}")
            
            # Asegurar que Google AI esté configurado
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                logger.error("❌ GOOGLE_API_KEY no encontrada en environment")
                return {
                    "success": False,
                    "error": "GOOGLE_API_KEY no configurada"
                }
            
            genai.configure(api_key=api_key)
            logger.info("✅ Google AI configurado")
            
            # Dividir en chunks
            logger.info("📝 Dividiendo texto en chunks...")
            chunks = self.chunk_text(text)
            logger.info(f"✅ Texto dividido en {len(chunks)} chunks")
            
            # Generar embeddings
            embeddings_data = []
            
            logger.info(f"🔄 Generando {len(chunks)} embeddings...")
            for i, chunk in enumerate(chunks):
                try:
                    logger.info(f"  → Chunk {i+1}/{len(chunks)} ({chunk['num_tokens']} tokens)...")
                    
                    result = genai.embed_content(
                        model=model,
                        content=chunk["text"],
                        task_type="retrieval_document"
                    )
                    
                    embedding = result['embedding']
                    
                    embeddings_data.append({
                        "chunk_id": chunk["chunk_id"],
                        "text": chunk["text"],
                        "num_tokens": chunk["num_tokens"],
                        "embedding": embedding,
                        "embedding_dim": len(embedding)
                    })
                    
                    logger.info(f"  ✅ Chunk {i+1}/{len(chunks)} procesado (dim: {len(embedding)})")
                except Exception as chunk_error:
                    logger.error(f"  ❌ Error en chunk {i+1}: {chunk_error}")
                    raise
            
            logger.info(f"✅ Todos los embeddings generados: {len(embeddings_data)} chunks")
            
            return {
                "success": True,
                "model": model,
                "num_chunks": len(chunks),
                "total_tokens": sum(c["num_tokens"] for c in chunks),
                "embeddings": embeddings_data,
                "indexed_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error crítico en generate_embeddings: {e}")
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_processing_summary(self, doc: RequiredDocument) -> Dict[str, Any]:
        """
        Obtiene resumen del estado de procesamiento de un documento.
        """
        return {
            "document_id": doc.id,
            "document_name": doc.document_name,
            "status": doc.status,
            "local_path": doc.local_path,
            "file_hash": doc.file_hash,
            "file_size_bytes": doc.file_size_bytes,
            "downloaded_at": doc.downloaded_at.isoformat() if doc.downloaded_at else None,
            "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
            "indexed_in_rag": doc.indexed_in_rag,
            "embedding_model": doc.embedding_model,
            "num_chunks": doc.num_chunks,
            "metadata": doc.metadata_json,
            "can_extract": doc.status in ["downloaded", "processed"] and doc.local_path,
            "can_index": doc.status in ["downloaded", "processed"],
        }

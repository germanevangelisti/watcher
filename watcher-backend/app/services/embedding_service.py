"""
Embedding Service - Vector embeddings for semantic search

This service handles:
- Text cleaning and normalization
- Text chunking and preprocessing
- Generating embeddings using Google gemini-embedding-001 (3072 dims)
- Integration with ChromaDB for vector storage
- Semantic search capabilities
"""

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Import TextCleaner
try:
    from .text_cleaner import TextCleaner
    TEXT_CLEANER_AVAILABLE = True
except ImportError:
    logger.warning("TextCleaner not available")
    TEXT_CLEANER_AVAILABLE = False

# Import ChunkingService
try:
    from .chunking_service import ChunkingConfig, ChunkingService
    CHUNKING_SERVICE_AVAILABLE = True
except ImportError:
    logger.warning("ChunkingService not available")
    CHUNKING_SERVICE_AVAILABLE = False

# Try to import ChromaDB
try:
    import chromadb
    from chromadb.api.types import EmbeddingFunction as ChromaEmbeddingFunction
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    logger.warning("ChromaDB not installed. Install with: pip install chromadb")
    CHROMADB_AVAILABLE = False

    class ChromaEmbeddingFunction:  # type: ignore[no-redef]
        """Base vacía: sin ChromaDB no hay protocolo que cumplir.

        Las dos funciones de embedding heredan de esta base para que las clases se
        definan igual; con ChromaDB instalado la base real aporta `embed_query`.
        """

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    logger.warning("Google Generative AI not installed. Install with: pip install google-generativeai")
    GOOGLE_AI_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    SENTENCE_TRANSFORMERS_ERROR: str | None = None
except ImportError as exc:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    # El motivo se guarda entero a propósito.  En la máquina de desarrollo el
    # paquete está instalado y lo que falla es un DLL bloqueado por la política
    # de control de aplicaciones: "no está instalado" manda a instalar algo que
    # ya está, y el problema real —que no hay embeddings locales— queda tapado.
    SENTENCE_TRANSFORMERS_ERROR = f"{type(exc).__name__}: {exc}"
    SentenceTransformer = None  # type: ignore[misc, assignment]


EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIM = 3072
LOCAL_COLLECTION_NAME = "watcher_documents_local"


class GoogleEmbeddingFunction(ChromaEmbeddingFunction):
    """ChromaDB-compatible embedding function using Google gemini-embedding-001."""

    def __init__(self, api_key: str, model: str = EMBEDDING_MODEL):
        # genai.configure() is called once at app startup in main.py
        self.model = model

    def name(self) -> str:
        """Required by ChromaDB 1.x."""
        return "google-gemini-embedding"

    def _embed(self, input: list[str], task_type: str) -> list[list[float]]:
        """Embeddea con el `task_type` que corresponda a la operación."""
        embeddings = []
        batch_size = 100

        for i in range(0, len(input), batch_size):
            batch = input[i:i + batch_size]
            for text in batch:
                try:
                    result = genai.embed_content(
                        model=self.model,
                        content=text,
                        task_type=task_type
                    )
                    embeddings.append(result['embedding'])
                except Exception as e:
                    logger.error(f"Error generating embedding: {e}")
                    embeddings.append([0.0] * EMBEDDING_DIM)

        return embeddings

    def __call__(self, input: list[str]) -> list[list[float]]:
        """Indexar: el texto entra como documento."""
        return self._embed(input, "retrieval_document")

    def embed_query(self, input: list[str]) -> list[list[float]]:
        """Buscar: ChromaDB llama esto, no `__call__`.

        Y la consulta no es un documento: `retrieval_query` es el `task_type` que
        Gemini espera acá. Heredar el default del `__call__` habría embeddeado cada
        query como documento — no rompe, degrada en silencio, que es peor.
        """
        return self._embed(input, "retrieval_query")


class LocalEmbeddingFunction(ChromaEmbeddingFunction):
    """ChromaDB-compatible embedding function using sentence-transformers."""

    def __init__(self, model_name: str):
        if not SENTENCE_TRANSFORMERS_AVAILABLE or SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install 'watcher-backend[local]'"
            )
        from app.core.hardware import local_device

        self.model_name = model_name
        device = local_device()
        self.model = SentenceTransformer(model_name, device=device)
        dim_fn = getattr(self.model, "get_embedding_dimension", None) or self.model.get_sentence_embedding_dimension
        self.dim = int(dim_fn())
        logger.info("Local embeddings on %s (%s, %s dims)", device, model_name, self.dim)

    def name(self) -> str:
        return f"local-{self.model_name}"

    def __call__(self, input: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            list(input),
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return vectors.tolist()

    def embed_query(self, input: list[str]) -> list[list[float]]:
        """Buscar: ChromaDB llama esto, no `__call__`.

        El modelo es simétrico, así que la consulta se embeddea igual que el
        documento — pero el método tiene que existir igual, porque `query()` falla
        con AttributeError si no está.
        """
        return self.__call__(input)


class EmbeddingService:
    """
    Service for generating and managing document embeddings.

    Supports multiple embedding providers:
    - Google AI (gemini-embedding-001, 3072 dims) - default
    - Local models (sentence-transformers)
    """

    def __init__(
        self,
        persist_directory: str | None = None,
        collection_name: str = "watcher_documents",
        embedding_provider: str = "google",  # "google" or "local"
        google_api_key: str | None = None,
        enable_text_cleaning: bool = True
    ):
        """
        Initialize embedding service.

        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of the collection
            embedding_provider: "google" or "local"
            google_api_key: Optional Google API key
            enable_text_cleaning: Whether to enable text cleaning (default: True)
        """
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider
        self.enable_text_cleaning = enable_text_cleaning

        # Initialize TextCleaner
        self.text_cleaner = None
        if enable_text_cleaning and TEXT_CLEANER_AVAILABLE:
            self.text_cleaner = TextCleaner()
            logger.info("Text cleaning enabled")
        elif enable_text_cleaning:
            logger.warning("Text cleaning requested but TextCleaner not available")

        # Initialize ChunkingService
        if not CHUNKING_SERVICE_AVAILABLE:
            raise ImportError("ChunkingService is required. Ensure chunking_service.py is available.")

        self.chunking_service = ChunkingService()
        logger.info("ChunkingService initialized")

        # Set up persist directory
        if persist_directory is None:
            persist_directory = str(Path.home() / ".watcher" / "chromadb")

        self.persist_directory = persist_directory
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize embedding function
        self.embedding_fn = None
        self.google_model = EMBEDDING_MODEL
        self.local_model_name = None
        self.embedding_dim = EMBEDDING_DIM

        if embedding_provider == "google":
            api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
            if api_key and GOOGLE_AI_AVAILABLE:
                self.embedding_fn = GoogleEmbeddingFunction(api_key, self.google_model)
                logger.info(f"Google AI embeddings enabled with model {self.google_model}")
            else:
                logger.warning("Google API key not found. Falling back to local embeddings.")
                self.embedding_provider = "local"

        if self.embedding_provider == "local":
            from app.core.hardware import local_embedding_model

            model_name = local_embedding_model()
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                try:
                    self.embedding_fn = LocalEmbeddingFunction(model_name)
                    self.local_model_name = model_name
                    self.embedding_dim = self.embedding_fn.dim
                    if collection_name == "watcher_documents":
                        collection_name = LOCAL_COLLECTION_NAME
                        self.collection_name = collection_name
                    logger.info("Local embeddings enabled with model %s", model_name)
                except Exception as exc:
                    logger.warning("Local embedding model failed to load: %s", exc)
                    self.embedding_fn = None
            else:
                logger.error(
                    "Embeddings locales NO disponibles: sentence-transformers no se pudo "
                    "importar (%s). Con esto no se pueden vectorizar las consultas, así "
                    "que la búsqueda semántica queda apagada — y la colección '%s', que "
                    "sí tiene los documentos indexados, no se va a consultar.",
                    SENTENCE_TRANSFORMERS_ERROR,
                    LOCAL_COLLECTION_NAME,
                )

        # Sin función de embedding no hay forma de vectorizar una consulta: ni
        # indexar ni buscar.  Se declara acá para que `search()` lo diga en vez de
        # devolver [] como si el corpus estuviera vacío.
        self.degraded_reason: str | None = None
        if self.embedding_fn is None:
            self.degraded_reason = (
                f"no hay función de embedding disponible (provider="
                f"'{self.embedding_provider}'; sentence-transformers: "
                f"{SENTENCE_TRANSFORMERS_ERROR or 'importado'}): las consultas no se "
                "pueden vectorizar"
            )

        # Initialize ChromaDB client
        self.client = None
        self.collection = None

        if CHROMADB_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )

                # Get or create collection WITH embedding function
                collection_kwargs = {
                    "name": collection_name,
                    "metadata": {
                        "description": f"Watcher Agent - {self.embedding_provider}",
                        "model": self.local_model_name or self.google_model,
                        "dimensions": self.embedding_dim,
                    },
                }
                if self.embedding_fn:
                    collection_kwargs["embedding_function"] = self.embedding_fn

                try:
                    self.collection = self.client.get_or_create_collection(**collection_kwargs)
                except Exception as conflict_err:
                    if "embedding function" in str(conflict_err).lower():
                        # Persisted collection has a different embedding config — reset it
                        logger.warning(f"Embedding function conflict, resetting collection '{collection_name}'")
                        self.client.delete_collection(collection_name)
                        self.collection = self.client.create_collection(**collection_kwargs)
                    else:
                        raise

                logger.info(f"ChromaDB initialized at {self.persist_directory}")
                logger.info(f"Collection '{collection_name}' ready with {self.collection.count()} documents")

                # La degradación que dejó el chat sin corpus (2026-10-01): sin EF
                # local la colección NO se renombra, así que este servicio abre la
                # `watcher_documents` vacía mientras los documentos reales están en
                # la `*_local`.  Se creía una búsqueda sin coincidencias y era una
                # búsqueda contra una colección vacía.
                if self.collection.count() == 0:
                    self._avisar_si_hay_documentos_en_otra_coleccion()

            except Exception as e:
                logger.error(f"Error initializing ChromaDB: {e}")
                self.client = None
        else:
            logger.warning("ChromaDB not available. Vector search features disabled.")

        self.stats = {
            "embeddings_created": 0,
            "documents_added": 0,
            "searches_performed": 0,
            "errors": 0,
        }

    def _avisar_si_hay_documentos_en_otra_coleccion(self) -> None:
        """Si esta colección está vacía pero el disco no lo está, decirlo **fuerte**.

        Es el caso que dejó el chat sin corpus el 2026-10-01: el servicio abría
        `watcher_documents` (0 documentos) mientras `watcher_documents_local` tenía
        983 chunks, y cada búsqueda devolvía 0 resultados con un log de INFO.  Un
        `0 results` que puede ser "no hay coincidencias" **o** "estoy mirando una
        colección vacía" no sirve para decidir nada.

        No cambia la colección elegida: sin función de embedding no habría con qué
        vectorizar la consulta igual.  Sólo deja de mentir sobre la causa.
        """
        if self.client is None:
            return
        try:
            otras = self.client.list_collections()
        except Exception as e:  # pragma: no cover - depende del cliente
            logger.warning("No se pudieron listar las colecciones: %s", e)
            return

        for otra in otras:
            nombre = getattr(otra, "name", otra)
            if nombre == self.collection_name:
                continue
            try:
                total = (otra.count() if hasattr(otra, "count")
                         else self.client.get_collection(nombre).count())
            except Exception:  # pragma: no cover
                continue
            if not total:
                continue
            logger.error(
                "La colección '%s' (la que consulta este servicio) está VACÍA, y '%s' "
                "tiene %d documentos. Toda búsqueda va a devolver 0 resultados que no "
                "significan 'sin coincidencias'. Causa: %s",
                self.collection_name,
                nombre,
                total,
                self.degraded_reason or "colección configurada distinta de la que tiene los datos",
            )

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> list[str]:
        """
        Split text into overlapping chunks using ChunkingService.

        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if not text:
            return []

        config = ChunkingConfig(
            chunk_size=chunk_size,
            chunk_overlap=overlap
        )
        chunk_results = self.chunking_service.chunk(text, config)
        return [cr.text for cr in chunk_results]

    async def generate_embedding(
        self,
        text: str
    ) -> list[float] | None:
        """
        Generate embedding for a text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if failed
        """
        if not text or not text.strip():
            return None

        try:
            if self.embedding_provider == "google" and GOOGLE_AI_AVAILABLE:
                # Google's gemini-embedding-001 produces 3072-dimensional vectors
                result = genai.embed_content(
                    model=self.google_model,
                    content=text,
                    task_type="retrieval_document"
                )
                embedding = result['embedding']
                self.stats["embeddings_created"] += 1
                return embedding

            if self.embedding_provider == "local" and self.embedding_fn is not None:
                vectors = self.embedding_fn([text])
                self.stats["embeddings_created"] += 1
                return vectors[0]

            logger.warning("No embedding function available for provider %s", self.embedding_provider)
            return None

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            self.stats["errors"] += 1
            return None

    async def add_document(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        chunk: bool = True,
        db_session = None,
        persist_chunks: bool = True,
        use_triple_indexing: bool = True
    ) -> dict[str, Any]:
        """
        Add a document to the vector store.

        Args:
            document_id: Unique document identifier
            content: Document content
            metadata: Optional metadata
            chunk: Whether to chunk the document
            db_session: Optional SQLAlchemy session for persisting ChunkRecords
            persist_chunks: Whether to persist chunks to database (requires db_session)
            use_triple_indexing: Use new IndexingService for atomic triple indexing (recommended)

        Returns:
            Result dict with success status
        """
        if not self.collection:
            return {
                "success": False,
                "error": "ChromaDB not initialized"
            }

        if not content:
            return {
                "success": False,
                "error": "No content provided"
            }

        # Use new triple indexing service if available and requested
        if use_triple_indexing and persist_chunks and db_session:
            try:
                from .indexing_service import get_indexing_service

                # Clean text before chunking
                cleaned_content = content
                if self.text_cleaner and self.enable_text_cleaning:
                    logger.info(f"Cleaning text for document {document_id}")
                    cleaned_content = self.text_cleaner.clean(content)
                    logger.info(f"Text cleaned: {len(content)} -> {len(cleaned_content)} chars")

                # Chunk the content
                chunk_results = []
                if chunk:
                    chunk_results = self.chunking_service.chunk(cleaned_content)
                else:
                    from .chunking_service import ChunkResult
                    chunk_results = [ChunkResult(
                        text=cleaned_content,
                        chunk_index=0,
                        start_char=0,
                        end_char=len(cleaned_content),
                        num_chars=len(cleaned_content)
                    )]

                # Use IndexingService for triple indexing
                indexing_service = get_indexing_service(db_session)
                boletin_id = metadata.get("boletin_id") if metadata else None

                result = await indexing_service.index_document(
                    document_id,
                    chunk_results,
                    metadata,
                    boletin_id
                )

                if result.success:
                    self.stats["documents_added"] += 1
                    self.stats["embeddings_created"] += result.chunks_indexed
                    logger.info(f"✓ Triple-indexed document {document_id} with {result.chunks_indexed} chunks")
                else:
                    logger.error(f"Error triple-indexing document {document_id}: {result.error}")

                return {
                    "success": result.success,
                    "document_id": document_id,
                    "chunks_created": result.chunks_indexed,
                    "error": result.error,
                    "triple_indexed": True
                }

            except Exception as e:
                logger.error(f"Error using triple indexing: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                    "triple_indexed": False
                }

        # Fallback: simple direct indexing without db persistence
        logger.info(f"Adding document {document_id} without triple indexing")

        try:
            # Clean text if enabled
            cleaned_content = content
            if self.text_cleaner and self.enable_text_cleaning:
                cleaned_content = self.text_cleaner.clean(content)

            # Generate chunks
            chunks_to_add = []
            chunks_to_add = self.chunk_text(cleaned_content) if chunk else [cleaned_content]

            if not chunks_to_add:
                return {
                    "success": False,
                    "error": "No chunks generated (text may be too short)"
                }

            # Add to ChromaDB
            chunk_ids = [f"{document_id}_{i}" for i in range(len(chunks_to_add))]
            chunk_metadatas = []
            for i in range(len(chunks_to_add)):
                chunk_meta = {
                    "document_id": document_id,
                    "chunk_index": i,
                    **(metadata or {})
                }
                chunk_metadatas.append(chunk_meta)

            self.collection.add(
                ids=chunk_ids,
                documents=chunks_to_add,
                metadatas=chunk_metadatas
            )

            self.stats["documents_added"] += 1
            self.stats["embeddings_created"] += len(chunks_to_add)

            logger.info(f"✓ Added document {document_id} with {len(chunks_to_add)} chunks (simple mode)")

            return {
                "success": True,
                "document_id": document_id,
                "chunks_created": len(chunks_to_add),
                "triple_indexed": False
            }

        except Exception as e:
            logger.error(f"Error adding document: {e}", exc_info=True)
            self.stats["errors"] += 1
            return {
                "success": False,
                "error": str(e),
                "triple_indexed": False
            }

    async def search(
        self,
        query: str,
        n_results: int = 10,
        filter: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Perform semantic search.

        Args:
            query: Search query
            n_results: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of matching documents with scores
        """
        if not self.collection:
            logger.warning("ChromaDB not initialized")
            return []

        if not query:
            return []

        try:
            # Perform search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter
            )

            self.stats["searches_performed"] += 1

            # Format results
            formatted_results = []

            if results and 'ids' in results and results['ids']:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        "id": results['ids'][0][i],
                        "document": results['documents'][0][i] if 'documents' in results else None,
                        "metadata": results['metadatas'][0][i] if 'metadatas' in results else None,
                        "distance": results['distances'][0][i] if 'distances' in results else None,
                    })

            if not formatted_results and getattr(self, "degraded_reason", None):
                logger.error(
                    "Búsqueda sin resultados y el servicio de embeddings está degradado: "
                    "%s. El corpus puede no estar vacío: no se pudo consultar. Un 0 acá "
                    "no significa 'sin coincidencias'.",
                    self.degraded_reason,
                )
            logger.info(f"Search for '{query}' returned {len(formatted_results)} results")

            return formatted_results

        except Exception as e:
            logger.error(f"Error performing search: {e}", exc_info=True)
            self.stats["errors"] += 1
            return []

    async def delete_document(
        self,
        document_id: str
    ) -> dict[str, Any]:
        """
        Delete a document and all its chunks from vector store.

        Args:
            document_id: Document identifier

        Returns:
            Result dict
        """
        if not self.collection:
            return {
                "success": False,
                "error": "ChromaDB not initialized"
            }

        try:
            # Find all chunks for this document
            results = self.collection.get(
                where={"document_id": document_id}
            )

            if results and 'ids' in results and results['ids']:
                self.collection.delete(ids=results['ids'])

                logger.info(f"Deleted document {document_id} with {len(results['ids'])} chunks")

                return {
                    "success": True,
                    "document_id": document_id,
                    "chunks_deleted": len(results['ids'])
                }
            else:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found"
                }

        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            self.stats["errors"] += 1
            return {
                "success": False,
                "error": str(e)
            }

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        stats = self.stats.copy()

        if self.collection:
            stats["total_documents"] = self.collection.count()

        return stats

    def reset_collection(self):
        """Reset the collection (delete all data)."""
        if self.client and self.collection:
            self.client.delete_collection(self.collection_name)
            collection_kwargs = {
                "name": self.collection_name,
                "metadata": {
                    "description": f"Watcher Agent - {self.embedding_provider}",
                    "model": self.local_model_name or self.google_model,
                    "dimensions": self.embedding_dim,
                },
            }
            if self.embedding_fn:
                collection_kwargs["embedding_function"] = self.embedding_fn

            self.collection = self.client.create_collection(**collection_kwargs)
            logger.info(f"Collection '{self.collection_name}' reset")


# Global instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service instance."""
    global _embedding_service

    if _embedding_service is None:
        from app.core.hardware import embedding_provider_default

        _embedding_service = EmbeddingService(
            embedding_provider=embedding_provider_default(),
        )

    return _embedding_service

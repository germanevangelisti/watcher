"""
Tests para el script de re-indexación de ChromaDB (`scripts/reindex_google_embeddings.py`).

Verifican, de forma hermética (sin llamadas reales a la API de Google), que la
re-indexación:
- Unifica la dimensión de los embeddings al modelo canónico.
- Preserva los chunks (ids/documentos) y crea un backup.
- Maneja casos borde (colección inexistente, dry-run).
"""

import sys
from pathlib import Path
from typing import List

import pytest

# El paquete `app` y el módulo de scripts viven en watcher-backend/.
BACKEND_DIR = Path(__file__).resolve().parents[2]
for p in (str(BACKEND_DIR), str(BACKEND_DIR / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import chromadb
from chromadb.config import Settings

from app.services.embedding_service import EMBEDDING_DIM
import reindex_google_embeddings as reindexer


class _FakeEmbeddingFunction:
    """Embedding function determinista compatible con ChromaDB (sin red)."""

    def __init__(self, dim: int, label: str):
        self._dim = dim
        self._label = label

    def name(self) -> str:
        return f"fake-{self._label}"

    def __call__(self, input: List[str]) -> List[List[float]]:
        # Vector determinista dependiente del texto para que la búsqueda sea estable.
        out = []
        for text in input:
            seed = (len(text) % 7) + 1
            out.append([float(seed) / 10.0] * self._dim)
        return out


def _client(persist_dir: Path):
    return chromadb.PersistentClient(
        path=str(persist_dir),
        settings=Settings(anonymized_telemetry=False, allow_reset=True),
    )


def _seed_collection(persist_dir: Path, dim: int, n: int = 5):
    """Crea una colección 'watcher_documents' con embeddings de dimensión `dim`."""
    client = _client(persist_dir)
    coll = client.create_collection(
        name="watcher_documents",
        metadata={"dimensions": dim},
        embedding_function=_FakeEmbeddingFunction(dim, "old"),
    )
    coll.add(
        ids=[f"doc_{i}_0" for i in range(n)],
        documents=[f"Boletín oficial número {i} con texto de prueba" for i in range(n)],
        metadatas=[{"document_id": f"doc_{i}", "chunk_index": 0} for i in range(n)],
    )
    return n


@pytest.mark.asyncio
async def test_reindex_unifies_dimensions(tmp_path):
    """Seed con dim 768 → reindex deja la colección en dim canónica (3072)."""
    n = _seed_collection(tmp_path, dim=768, n=5)

    result = await reindexer.reindex(
        persist_dir=tmp_path,
        collection_name="watcher_documents",
        embedding_fn=_FakeEmbeddingFunction(EMBEDDING_DIM, "new"),
        backup=True,
        sleep_between_batches=0,
        verbose=False,
    )

    assert result["status"] == "ok"
    assert result["reindexed"] == n
    assert result["dimensions"] == EMBEDDING_DIM
    assert result["dimensions"] != 768

    # La colección persistida quedó con la dimensión canónica.
    client = _client(tmp_path)
    coll = client.get_collection("watcher_documents")
    assert coll.count() == n
    sample = coll.get(ids=["doc_0_0"], include=["embeddings"])
    assert len(sample["embeddings"][0]) == EMBEDDING_DIM


@pytest.mark.asyncio
async def test_reindex_creates_backup_and_preserves_docs(tmp_path):
    n = _seed_collection(tmp_path, dim=768, n=4)

    result = await reindexer.reindex(
        persist_dir=tmp_path,
        collection_name="watcher_documents",
        embedding_fn=_FakeEmbeddingFunction(EMBEDDING_DIM, "new"),
        backup=True,
        sleep_between_batches=0,
        verbose=False,
    )

    client = _client(tmp_path)
    # El backup existe y conserva los embeddings originales (dim 768).
    assert result["backup"] is not None
    backup = client.get_collection(result["backup"])
    assert backup.count() == n
    backup_sample = backup.get(ids=["doc_0_0"], include=["embeddings"])
    assert len(backup_sample["embeddings"][0]) == 768

    # Los documentos se preservan en la colección re-indexada.
    coll = client.get_collection("watcher_documents")
    docs = coll.get(ids=[f"doc_{i}_0" for i in range(n)])
    assert sorted(docs["ids"]) == sorted([f"doc_{i}_0" for i in range(n)])


@pytest.mark.asyncio
async def test_reindex_noop_when_collection_missing(tmp_path):
    result = await reindexer.reindex(
        persist_dir=tmp_path,
        collection_name="watcher_documents",
        embedding_fn=_FakeEmbeddingFunction(EMBEDDING_DIM, "new"),
        backup=True,
        sleep_between_batches=0,
        verbose=False,
    )
    assert result["status"] == "noop"
    assert result["reindexed"] == 0


@pytest.mark.asyncio
async def test_reindex_dry_run_makes_no_changes(tmp_path):
    n = _seed_collection(tmp_path, dim=768, n=3)

    result = await reindexer.reindex(
        persist_dir=tmp_path,
        collection_name="watcher_documents",
        embedding_fn=_FakeEmbeddingFunction(EMBEDDING_DIM, "new"),
        dry_run=True,
        sleep_between_batches=0,
        verbose=False,
    )

    assert result["status"] == "dry_run"
    assert result["found"] == n

    # No se crearon colecciones de backup ni cambió la dimensión.
    client = _client(tmp_path)
    names = [c.name for c in client.list_collections()]
    assert names == ["watcher_documents"]
    coll = client.get_collection("watcher_documents")
    sample = coll.get(ids=["doc_0_0"], include=["embeddings"])
    assert len(sample["embeddings"][0]) == 768

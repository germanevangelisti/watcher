"""
Re-indexación de ChromaDB con el modelo de embeddings canónico de Watcher.

Re-genera todos los embeddings de la colección `watcher_documents` usando el
modelo configurado en `app.services.embedding_service`
(``gemini-embedding-001``, 3072 dimensiones), garantizando consistencia con el
resto del backend (``EmbeddingService``, ``DocumentProcessor``,
``IndexingService``).

Proceso:
  1. Lee todos los chunks (documentos + metadatos + embeddings) de la colección.
  2. Crea un backup con los embeddings originales (salvo ``--no-backup``).
  3. Recrea la colección canónica con la embedding function correcta.
  4. Re-agrega todos los chunks; ChromaDB regenera los embeddings vía la API.

Uso:
    cd watcher-backend
    python scripts/reindex_google_embeddings.py [--dry-run] [--no-backup] \
        [--persist-dir PATH] [--collection NAME]
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# El backend (paquete `app`) vive en el directorio padre de `scripts/`.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    pass

try:
    import chromadb
    from chromadb.config import Settings
    import google.generativeai as genai
except ImportError as e:  # pragma: no cover - entorno sin dependencias
    print(f"❌ Error importando dependencias: {e}")
    print("\n📦 Instala las dependencias:")
    print("   pip install chromadb google-generativeai")
    sys.exit(1)

from app.services.embedding_service import (  # noqa: E402
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    GoogleEmbeddingFunction,
)

DEFAULT_COLLECTION = "watcher_documents"
DEFAULT_PERSIST_DIR = Path.home() / ".watcher" / "chromadb"
DEFAULT_BATCH_SIZE = 50


async def reindex(
    persist_dir: Path = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
    embedding_fn=None,
    backup: bool = True,
    dry_run: bool = False,
    batch_size: int = DEFAULT_BATCH_SIZE,
    sleep_between_batches: float = 0.2,
    verbose: bool = True,
) -> dict:
    """Re-indexa una colección de ChromaDB con el modelo canónico.

    Args:
        persist_dir: Directorio de persistencia de ChromaDB.
        collection_name: Nombre de la colección a re-indexar.
        embedding_fn: Embedding function a usar. Si es ``None`` se construye una
            ``GoogleEmbeddingFunction`` a partir de ``GOOGLE_API_KEY``.
        backup: Si se crea un backup con los embeddings originales.
        dry_run: Si es ``True`` no realiza cambios, sólo reporta.
        batch_size: Tamaño de lote para re-agregar chunks.
        sleep_between_batches: Pausa entre lotes (respetar rate limits).
        verbose: Si imprime el progreso.

    Returns:
        Dict con ``status`` y métricas de la operación.
    """

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    log("\n" + "=" * 80)
    log("RE-INDEXACIÓN DE CHROMADB — MODELO CANÓNICO")
    log("=" * 80)
    log(f"📅 Fecha:        {datetime.now():%Y-%m-%d %H:%M:%S}")
    log(f"📁 ChromaDB:     {persist_dir}")
    log(f"🤖 Modelo:       {EMBEDDING_MODEL}")
    log(f"📏 Dimensiones:  {EMBEDDING_DIM}")
    log(f"🗂️  Colección:    {collection_name}")
    log(f"🧪 Dry-run:      {dry_run}")
    log("=" * 80)

    # Paso 1: embedding function
    if embedding_fn is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            log("\n❌ GOOGLE_API_KEY no encontrada. Configúrala en el entorno o en .env")
            return {"status": "error", "error": "GOOGLE_API_KEY no configurada"}
        genai.configure(api_key=api_key)
        embedding_fn = GoogleEmbeddingFunction(api_key)
    log(f"\n[1/4] ✅ Embedding function lista ({EMBEDDING_MODEL})")

    # Paso 2: conectar a ChromaDB
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(persist_dir),
        settings=Settings(anonymized_telemetry=False, allow_reset=True),
    )
    log(f"[2/4] ✅ Conectado a ChromaDB ({persist_dir})")

    # Paso 3: leer colección actual
    try:
        old_collection = client.get_collection(collection_name)
    except Exception:
        log(f"\n⚠️  La colección '{collection_name}' no existe. Nada para re-indexar.")
        return {"status": "noop", "reason": "collection_not_found", "reindexed": 0}

    data = old_collection.get(include=["documents", "metadatas", "embeddings"])

    # ChromaDB puede devolver numpy arrays para `embeddings`; evitar evaluar
    # su valor de verdad (`or []`) y convertir explícitamente a listas.
    def _as_list(value):
        return list(value) if value is not None else []

    ids = _as_list(data.get("ids"))
    documents = _as_list(data.get("documents"))
    metadatas = _as_list(data.get("metadatas"))
    embeddings = _as_list(data.get("embeddings"))
    total = len(ids)
    log(f"[3/4] 📊 {total} chunks encontrados en '{collection_name}'")

    if total == 0:
        log("   ⚠️  Colección vacía, nada que re-indexar.")
        return {"status": "noop", "reason": "empty_collection", "reindexed": 0}

    if dry_run:
        log("\n🧪 Dry-run: no se realizarán cambios.")
        return {
            "status": "dry_run",
            "reindexed": 0,
            "found": total,
            "collection": collection_name,
        }

    # Metadatos seguros: ChromaDB rechaza dicts vacíos / None.
    def _safe_meta(m: Optional[dict]) -> dict:
        return m if m else {"reindexed": True}

    safe_metadatas = [_safe_meta(m) for m in metadatas]

    collection_metadata = {
        "description": f"Watcher Agent - Google {EMBEDDING_MODEL}",
        "model": EMBEDDING_MODEL,
        "dimensions": EMBEDDING_DIM,
        "reindexed_at": datetime.now().isoformat(),
    }

    # Backup con los embeddings originales (preserva el estado previo).
    backup_name = None
    if backup:
        backup_name = f"{collection_name}_backup_{datetime.now():%Y%m%d_%H%M%S}"
        backup_collection = client.create_collection(name=backup_name)
        for i in range(0, total, batch_size):
            end = min(i + batch_size, total)
            backup_collection.add(
                ids=ids[i:end],
                documents=documents[i:end],
                metadatas=safe_metadatas[i:end],
                embeddings=embeddings[i:end] if embeddings else None,
            )
        log(f"   💾 Backup creado: '{backup_name}' ({total} chunks)")

    # Paso 4: recrear colección canónica y re-indexar.
    log("\n[4/4] 🔄 Re-indexando colección canónica...")
    client.delete_collection(collection_name)
    new_collection = client.create_collection(
        name=collection_name,
        metadata=collection_metadata,
        embedding_function=embedding_fn,
    )

    for i in range(0, total, batch_size):
        end = min(i + batch_size, total)
        # Sin `embeddings`: ChromaDB los regenera vía la embedding function.
        new_collection.add(
            ids=ids[i:end],
            documents=documents[i:end],
            metadatas=safe_metadatas[i:end],
        )
        if verbose:
            pct = end / total * 100
            print(f"   [{end}/{total}] {pct:.1f}% completado", end="\r")
        if sleep_between_batches:
            await asyncio.sleep(sleep_between_batches)

    final_count = new_collection.count()
    # Verificar dimensión del primer embedding regenerado.
    sample = new_collection.get(ids=ids[:1], include=["embeddings"])
    sample_embeddings = _as_list(sample.get("embeddings"))
    sample_dim = len(sample_embeddings[0]) if sample_embeddings else None

    log("\n" + "=" * 80)
    log("RESUMEN")
    log("=" * 80)
    log(f"✅ Re-indexación completada: {final_count} chunks")
    log(f"🤖 Modelo:       {EMBEDDING_MODEL}")
    log(f"📏 Dimensiones:  {sample_dim} (esperado {EMBEDDING_DIM})")
    if backup_name:
        log(f"💾 Backup:       {backup_name}")
    log("=" * 80)

    return {
        "status": "ok",
        "reindexed": final_count,
        "dimensions": sample_dim,
        "expected_dimensions": EMBEDDING_DIM,
        "collection": collection_name,
        "backup": backup_name,
    }


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Re-indexa ChromaDB con el modelo canónico de Watcher")
    parser.add_argument("--persist-dir", type=Path, default=DEFAULT_PERSIST_DIR)
    parser.add_argument("--collection", type=str, default=DEFAULT_COLLECTION)
    parser.add_argument("--no-backup", action="store_true", help="No crear backup")
    parser.add_argument("--dry-run", action="store_true", help="No realizar cambios")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    return parser.parse_args(argv)


async def main(argv=None) -> int:
    args = _parse_args(argv)
    result = await reindex(
        persist_dir=args.persist_dir,
        collection_name=args.collection,
        backup=not args.no_backup,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
    )
    return 0 if result.get("status") in {"ok", "noop", "dry_run"} else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

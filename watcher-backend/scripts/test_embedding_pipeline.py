"""
Test del pipeline de embeddings end-to-end.

Valida:
1. GOOGLE_API_KEY está configurada
2. Google AI genera embeddings correctamente
3. ChromaDB almacena y recupera embeddings
4. EmbeddingService funciona end-to-end
5. El endpoint /index-embeddings funciona contra los docs subidos

Uso:
    cd watcher-monolith/backend
    python ../../scripts/test_embedding_pipeline.py
"""

import os
import sys
import asyncio
from pathlib import Path

# Asegurar que el backend esté en el path
BACKEND_DIR = Path(__file__).parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Cargar .env ANTES de cualquier import del backend
from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

PASS = "✅ PASS"
FAIL = "❌ FAIL"
SKIP = "⏭️  SKIP"

results = []


def report(name: str, passed: bool, detail: str = ""):
    status = PASS if passed else FAIL
    results.append((name, passed, detail))
    msg = f"  {status} {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return passed


def test_1_google_api_key():
    """Test 1: GOOGLE_API_KEY está configurada."""
    print("\n[1/5] GOOGLE_API_KEY")
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        report("GOOGLE_API_KEY en env", False, "No encontrada. Verificar .env")
        return False
    report("GOOGLE_API_KEY en env", True, f"{key[:8]}...{key[-4:]}")
    return True


def test_2_google_embed_single():
    """Test 2: Google AI puede generar un embedding."""
    print("\n[2/5] Google AI — embedding simple")
    try:
        import google.generativeai as genai

        api_key = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)

        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content="Texto de prueba para generar embedding",
            task_type="retrieval_document",
        )
        embedding = result["embedding"]
        dim = len(embedding)

        report("genai.embed_content()", True, f"dim={dim}")
        report("Dimensiones correctas (3072)", dim == 3072, f"got {dim}")
        return True
    except Exception as e:
        report("genai.embed_content()", False, str(e))
        return False


def test_3_chromadb_basic():
    """Test 3: ChromaDB puede crear colección y almacenar datos."""
    print("\n[3/5] ChromaDB — almacenamiento básico")
    try:
        import chromadb
        from chromadb.config import Settings

        client = chromadb.PersistentClient(
            path=str(Path.home() / ".watcher" / "chromadb"),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        report("ChromaDB PersistentClient", True)

        # Crear colección de test
        test_col_name = "test-embedding-pipeline"
        try:
            client.delete_collection(test_col_name)
        except Exception:
            pass

        # Importar la embedding function del servicio
        from app.services.embedding_service import GoogleEmbeddingFunction

        api_key = os.getenv("GOOGLE_API_KEY")
        embedding_fn = GoogleEmbeddingFunction(api_key)

        col = client.create_collection(
            name=test_col_name,
            embedding_function=embedding_fn,
            metadata={"description": "test"},
        )
        report("Crear colección con GoogleEmbeddingFunction", True)

        # Agregar documento
        col.add(
            documents=["Este es un texto de prueba para verificar embeddings"],
            ids=["test_doc_1"],
            metadatas=[{"source": "test"}],
        )
        report("add() con texto (embedding generado por Google)", True, f"count={col.count()}")

        # Buscar
        results_query = col.query(
            query_texts=["texto de prueba"],
            n_results=1,
        )
        found = len(results_query["ids"][0]) > 0
        distance = results_query["distances"][0][0] if found else None
        report("query() semántica", found, f"distance={distance:.4f}" if distance else "sin resultados")

        # Limpiar
        client.delete_collection(test_col_name)
        report("Limpieza colección de test", True)

        return True
    except Exception as e:
        report("ChromaDB básico", False, str(e))
        import traceback
        traceback.print_exc()
        return False


def test_4_embedding_service():
    """Test 4: EmbeddingService end-to-end."""
    print("\n[4/5] EmbeddingService — end-to-end")
    try:
        from app.services.embedding_service import EmbeddingService

        svc = EmbeddingService(
            collection_name="test-embedding-service",
            embedding_provider="google",
        )
        report("EmbeddingService init", svc.collection is not None, f"provider={svc.embedding_provider}")
        report("GoogleEmbeddingFunction activa", svc.embedding_fn is not None)

        if not svc.collection or not svc.embedding_fn:
            report("EmbeddingService end-to-end", False, "colección o embedding_fn es None")
            return False

        # Agregar documento
        texto = (
            "ARTÍCULO 1°.- Fíjase en la suma de PESOS CIENTO CINCUENTA MIL MILLONES "
            "($150.000.000.000) el total de erogaciones del Presupuesto General de la "
            "Administración Provincial para el ejercicio 2025. "
            "ARTÍCULO 2°.- El monto total de recursos se estima en la suma de PESOS "
            "CIENTO CUARENTA MIL MILLONES ($140.000.000.000)."
        )

        result = asyncio.get_event_loop().run_until_complete(
            svc.add_document(
                document_id="test_presupuesto",
                content=texto,
                metadata={"source": "test", "tipo": "ley_presupuesto"},
            )
        )
        report(
            "add_document()",
            result["success"],
            f"chunks={result.get('chunks_created', 0)}"
        )

        # Buscar
        search_results = asyncio.get_event_loop().run_until_complete(
            svc.search("presupuesto provincial 2025")
        )
        found = len(search_results) > 0
        top_dist = search_results[0]["distance"] if found else None
        report(
            "search() semántica",
            found,
            f"results={len(search_results)}, top_distance={top_dist:.4f}" if found else "sin resultados"
        )

        # Limpiar
        svc.reset_collection()
        svc.client.delete_collection("test-embedding-service")
        report("Limpieza", True)

        return True
    except Exception as e:
        report("EmbeddingService end-to-end", False, str(e))
        import traceback
        traceback.print_exc()
        return False


def test_5_document_processor():
    """Test 5: DocumentProcessor genera embeddings."""
    print("\n[5/5] DocumentProcessor — generate_embeddings()")
    try:
        from app.services.document_processor import DocumentProcessor

        processor = DocumentProcessor()
        report("DocumentProcessor init", True)

        texto_corto = "ARTÍCULO 1°.- Apruébase el Presupuesto General para el ejercicio 2025."

        result = asyncio.get_event_loop().run_until_complete(
            processor.generate_embeddings(texto_corto)
        )

        success = result.get("success", False)
        report(
            "generate_embeddings()",
            success,
            f"chunks={result.get('num_chunks')}, model={result.get('model')}"
            if success
            else result.get("error", "unknown error"),
        )

        if success and result.get("embeddings"):
            emb = result["embeddings"][0]
            dim = emb.get("embedding_dim", 0)
            report("Embedding dimension", dim == 3072, f"dim={dim}")

        return success
    except Exception as e:
        report("DocumentProcessor", False, str(e))
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 70)
    print("TEST: Pipeline de Embeddings end-to-end")
    print("=" * 70)

    # Cambiar al directorio del backend para que los imports funcionen
    os.chdir(str(BACKEND_DIR))

    ok = True
    ok = test_1_google_api_key() and ok
    ok = test_2_google_embed_single() and ok if ok else False
    ok = test_3_chromadb_basic() and ok if ok else False
    ok = test_4_embedding_service() and ok if ok else False
    ok = test_5_document_processor() and ok if ok else False

    # Resumen
    total = len(results)
    passed = sum(1 for _, p, _ in results if p)
    failed = total - passed

    print("\n" + "=" * 70)
    print(f"RESULTADO: {passed}/{total} tests pasaron")
    if failed:
        print(f"\n❌ {failed} test(s) fallaron:")
        for name, p, detail in results:
            if not p:
                print(f"   - {name}: {detail}")
    else:
        print("\n✅ Todos los tests pasaron. El pipeline de embeddings funciona correctamente.")
    print("=" * 70)

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())

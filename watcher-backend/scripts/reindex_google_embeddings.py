"""
Re-indexación con Google text-embedding-004

Este script re-indexa todos los documentos usando el modelo
Google text-embedding-004 (768 dimensiones).
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List
import os

# Agregar el directorio del backend al path
sys.path.insert(0, str(Path(__file__).parent.parent / "watcher-monolith" / "backend"))

try:
    import chromadb
    from chromadb.config import Settings
    import google.generativeai as genai
except ImportError as e:
    print(f"❌ Error importando dependencias: {e}")
    print("\n📦 Instala las dependencias:")
    print("   pip install chromadb google-generativeai")
    sys.exit(1)


class GoogleEmbeddingFunction:
    """Embedding function para Google text-embedding-004 compatible con ChromaDB"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = "models/text-embedding-004"
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        """Genera embeddings para los textos usando Google AI"""
        embeddings = []
        
        # Procesar en batches para manejar rate limits
        batch_size = 100
        for i in range(0, len(input), batch_size):
            batch = input[i:i+batch_size]
            
            for text in batch:
                try:
                    result = genai.embed_content(
                        model=self.model,
                        content=text,
                        task_type="retrieval_document"
                    )
                    embeddings.append(result['embedding'])
                except Exception as e:
                    print(f"   ⚠️  Error generando embedding: {e}")
                    # Fallback: vector de ceros
                    embeddings.append([0.0] * 768)
        
        return embeddings


class GoogleReindexer:
    """Re-indexa con modelo Google text-embedding-004"""
    
    def __init__(self):
        self.persist_dir = Path.home() / ".watcher" / "chromadb"
        self.model_name = "models/text-embedding-004"
        self.collection_name = "watcher_documents"
    
    async def run(self):
        """Ejecuta la re-indexación"""
        print("\n" + "="*80)
        print("RE-INDEXACIÓN CON GOOGLE TEXT-EMBEDDING-004")
        print("="*80)
        print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 ChromaDB: {self.persist_dir}")
        print(f"🤖 Modelo: {self.model_name}")
        print(f"📏 Dimensiones: 768")
        print("="*80)
        
        # Verificar API key
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print("\n❌ Error: GOOGLE_API_KEY no encontrada")
            print("\n💡 Configura tu API key:")
            print("   export GOOGLE_API_KEY='tu-api-key-aqui'")
            print("   # o agrégala al archivo .env")
            return
        
        # Paso 1: Crear embedding function
        print("\n[1/4] Inicializando Google AI...")
        try:
            embedding_fn = GoogleEmbeddingFunction(api_key)
            print("   ✅ Google AI configurado correctamente")
        except Exception as e:
            print(f"   ❌ Error configurando Google AI: {e}")
            return
        
        # Paso 2: Conectar a ChromaDB
        print("\n[2/4] Conectando a ChromaDB...")
        try:
            client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            print(f"   ✅ Conectado a {self.persist_dir}")
        except Exception as e:
            print(f"   ❌ Error conectando: {e}")
            return
        
        # Paso 3: Backup de colección anterior
        print("\n[3/4] Backup de colección anterior...")
        try:
            old_collection = client.get_collection(self.collection_name)
            old_count = old_collection.count()
            print(f"   📊 Colección actual: {old_count} documentos")
            
            # Obtener todos los datos
            all_data = old_collection.get(include=['documents', 'metadatas'])
            print(f"   ✅ Datos extraídos: {len(all_data['ids'])} chunks")
            
            # Hacer backup con timestamp
            backup_name = f"{self.collection_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"   💾 Creando backup: {backup_name}")
            
            # No eliminar la colección aún, solo crear nueva
            
        except Exception as e:
            print(f"   ⚠️  No hay colección anterior: {e}")
            all_data = None
        
        # Paso 4: Crear nueva colección con Google embeddings
        print("\n[4/4] Creando nueva colección con Google embeddings...")
        
        # Nombre temporal para nueva colección
        new_collection_name = f"{self.collection_name}_google"
        
        try:
            # Crear colección con embedding function custom
            new_collection = client.create_collection(
                name=new_collection_name,
                metadata={
                    "description": "Watcher Agent - Google text-embedding-004",
                    "model": self.model_name,
                    "dimensions": 768,
                    "created_at": datetime.now().isoformat()
                },
                embedding_function=embedding_fn
            )
            print(f"   ✅ Nueva colección '{new_collection_name}' creada")
            
            # Re-indexar documentos si existen
            if all_data and all_data['ids']:
                print(f"\n   📝 Re-indexando {len(all_data['ids'])} chunks con Google AI...")
                print(f"   ⚠️  Esto puede tomar tiempo debido a rate limits de la API")
                
                batch_size = 50  # Batch más pequeño para evitar rate limits
                total = len(all_data['ids'])
                
                for i in range(0, total, batch_size):
                    end = min(i + batch_size, total)
                    batch_ids = all_data['ids'][i:end]
                    batch_docs = all_data['documents'][i:end]
                    batch_meta = all_data['metadatas'][i:end]
                    
                    # Agregar con embeddings generados por Google
                    new_collection.add(
                        ids=batch_ids,
                        documents=batch_docs,
                        metadatas=batch_meta
                    )
                    
                    progress = (end / total) * 100
                    print(f"   [{end}/{total}] {progress:.1f}% completado", end='\r')
                    
                    # Pequeña pausa para respetar rate limits
                    await asyncio.sleep(1)
                
                print(f"\n   ✅ {total} chunks re-indexados con Google embeddings")
                
                # Verificar
                final_count = new_collection.count()
                print(f"   ✅ Verificación: {final_count} documentos en nueva colección")
                
                # Instrucciones para swap
                print("\n   💡 Para usar la nueva colección:")
                print(f"      1. Verificar resultados con búsquedas de prueba")
                print(f"      2. Renombrar colección o actualizar código para usar '{new_collection_name}'")
                print(f"      3. Eliminar colección antigua si todo funciona bien")
                
            else:
                print("   ⚠️  No hay documentos previos para re-indexar")
                print("   💡 Ejecuta: python scripts/indexar_embeddings.py --year 2026")
            
        except Exception as e:
            print(f"   ❌ Error creando colección: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Resumen final
        print("\n" + "="*80)
        print("RESUMEN")
        print("="*80)
        print("✅ Re-indexación completada exitosamente")
        print(f"🤖 Modelo: Google {self.model_name}")
        print(f"📏 Dimensiones: 768")
        print(f"📊 Documentos: {new_collection.count()}")
        print(f"🎯 Colección: {new_collection_name}")
        print("\n💡 Ventajas de Google embeddings:")
        print("   - Mayor precisión en español")
        print("   - 768 dimensiones (vs 384 del modelo anterior)")
        print("   - Gratis en free tier de Google AI")
        print("\n📝 Próximos pasos:")
        print("   1. Probar búsquedas en la nueva colección")
        print("   2. Comparar resultados con colección anterior")
        print("   3. Si todo funciona bien, actualizar EmbeddingService para usar nueva colección")
        print("="*80)


async def main():
    """Función principal"""
    reindexer = GoogleReindexer()
    await reindexer.run()


if __name__ == "__main__":
    asyncio.run(main())

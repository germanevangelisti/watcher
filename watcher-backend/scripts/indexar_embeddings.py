#!/usr/bin/env python3
"""
Script para indexación masiva de embeddings en ChromaDB
Lee archivos .txt procesados y crea vectores para búsqueda semántica
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Añadir el directorio raíz del proyecto al sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "watcher-monolith" / "backend"))

from app.db.database import AsyncSessionLocal
from app.db.models import Boletin
from app.services.embedding_service import get_embedding_service
from sqlalchemy import select


class IndexadorEmbeddingsMasivo:
    """Indexador masivo de embeddings"""

    def __init__(self, batch_size: int = 20):
        self.batch_size = batch_size
        self.embedding_service = get_embedding_service()
        self.processed_dir = Path("/Users/germanevangelisti/watcher-agent/watcher-monolith/backend/data/processed")

        # Estadísticas
        self.stats = {
            'documentos_indexados': 0,
            'chunks_creados': 0,
            'ya_existian': 0,
            'fallidos': 0,
            'tiempo_inicio': None,
            'tiempo_fin': None
        }

    async def indexar_embeddings(
        self,
        year: str | None = None,
        month: str | None = None,
        day: str | None = None,
        limit: int | None = None,
        force: bool = False
    ):
        """
        Indexa embeddings de boletines completados
        
        Args:
            year: Filtrar por año (YYYY)
            month: Filtrar por mes (MM)
            day: Filtrar por día (DD)
            limit: Límite de boletines a procesar
            force: Forzar re-indexación (eliminar y recrear)
        """
        self.stats['tiempo_inicio'] = datetime.now()

        print("=" * 70)
        print("  INDEXACIÓN MASIVA DE EMBEDDINGS EN CHROMADB")
        print("=" * 70)

        if not self.embedding_service.collection:
            print("❌ Error: ChromaDB no está disponible")
            return

        print(f"📦 Colección: {self.embedding_service.collection_name}")
        print(f"📊 Documentos existentes: {self.embedding_service.collection.count()}")

        if force:
            print("\n⚠️  Modo FORCE: Se eliminarán documentos existentes")

        async with AsyncSessionLocal() as db:
            # Construir query - solo boletines completados
            query = select(Boletin).where(Boletin.status == 'completed')

            # Aplicar filtros
            if year:
                query = query.where(Boletin.date.like(f"{year}%"))
                print(f"\n📅 Filtro: Año {year}")

            if month:
                if not year:
                    print("⚠️  Advertencia: mes especificado sin año, se ignora")
                else:
                    query = query.where(Boletin.date.like(f"{year}{month}%"))
                    print(f"📅 Filtro: {year}-{month}")

            if day:
                if not year or not month:
                    print("⚠️  Advertencia: día especificado sin año/mes, se ignora")
                else:
                    query = query.where(Boletin.date.like(f"{year}{month}{day}%"))
                    print(f"📅 Filtro: {year}-{month}-{day}")

            if limit:
                query = query.limit(limit)
                print(f"🔢 Límite: {limit} boletines")

            # Ejecutar query
            result = await db.execute(query)
            boletines = result.scalars().all()

            if not boletines:
                print("\n✅ No hay boletines para indexar")
                return

            print(f"\n📊 Encontrados: {len(boletines)} boletines completados")
            print(f"📦 Procesando en lotes de {self.batch_size}...\n")

            # Procesar en lotes
            for i in range(0, len(boletines), self.batch_size):
                batch = boletines[i:i + self.batch_size]
                batch_num = (i // self.batch_size) + 1
                total_batches = (len(boletines) + self.batch_size - 1) // self.batch_size

                print(f"🔄 Lote {batch_num}/{total_batches} ({len(batch)} boletines)")
                print("-" * 70)

                await self._procesar_lote(batch, force)

                print(f"✅ Lote {batch_num} completado\n")

            self.stats['tiempo_fin'] = datetime.now()
            self._imprimir_resumen()

    async def _procesar_lote(self, boletines, force: bool):
        """Procesa un lote de boletines"""

        for idx, boletin in enumerate(boletines, 1):
            try:
                # Construir path al archivo de texto
                txt_path = self.processed_dir / f"{boletin.filename.replace('.pdf', '')}.txt"

                if not txt_path.exists():
                    print(f"  [{idx}/{len(boletines)}] ⚠️  Texto no encontrado: {boletin.filename}")
                    self.stats['fallidos'] += 1
                    continue

                # Leer texto
                with open(txt_path, encoding='utf-8') as f:
                    text = f.read()

                if not text or len(text) < 100:
                    print(f"  [{idx}/{len(boletines)}] ⚠️  Texto vacío: {boletin.filename}")
                    self.stats['fallidos'] += 1
                    continue

                # Usar filename sin extensión como document_id
                document_id = boletin.filename.replace('.pdf', '')

                print(f"  [{idx}/{len(boletines)}] 🔄 Indexando: {boletin.filename}...", end=" ", flush=True)

                # Preparar metadata (todos los valores deben ser strings para ChromaDB)
                metadata = {
                    "document_id": str(document_id),
                    "date": str(boletin.date),
                    "section": str(boletin.section) if boletin.section else "unknown",
                    "jurisdiccion_id": "1",
                    "filename": str(boletin.filename)
                }

                # Agregar documento con chunking automático
                try:
                    result = await self.embedding_service.add_document(
                        document_id=document_id,
                        content=text,
                        metadata=metadata,
                        chunk=True
                    )

                    if result.get('success'):
                        chunks = result.get('chunks_created', 0)
                        self.stats['documentos_indexados'] += 1
                        self.stats['chunks_creados'] += chunks
                        print(f"✅ ({chunks} chunks)")
                    else:
                        print(f"❌ {result.get('error', 'Unknown error')}")
                        self.stats['fallidos'] += 1

                except Exception as add_error:
                    print(f"❌ Error al agregar: {str(add_error)}")
                    self.stats['fallidos'] += 1

            except Exception as e:
                print(f"  [{idx}/{len(boletines)}] ❌ Error general: {boletin.filename}")
                print(f"      {str(e)}")
                self.stats['fallidos'] += 1

    def _imprimir_resumen(self):
        """Imprime resumen de la ejecución"""
        duracion = self.stats['tiempo_fin'] - self.stats['tiempo_inicio']
        duracion_seg = duracion.total_seconds()

        print("=" * 70)
        print("  RESUMEN DE INDEXACIÓN")
        print("=" * 70)
        print(f"📊 Documentos indexados:       {self.stats['documentos_indexados']}")
        print(f"📝 Chunks creados:             {self.stats['chunks_creados']}")
        print(f"⏭️  Ya existían:                {self.stats['ya_existian']}")
        print(f"❌ Fallidos:                   {self.stats['fallidos']}")
        print(f"⏱️  Tiempo total:               {duracion_seg:.1f}s")

        if self.stats['documentos_indexados'] > 0:
            tiempo_promedio = duracion_seg / self.stats['documentos_indexados']
            print(f"⚡ Tiempo promedio/doc:        {tiempo_promedio:.2f}s")

        # Estadísticas finales de ChromaDB
        final_count = self.embedding_service.collection.count()
        print(f"\n📦 Total documentos en ChromaDB: {final_count}")
        print("=" * 70)


async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Indexación masiva de embeddings en ChromaDB'
    )
    parser.add_argument(
        '--year',
        type=str,
        help='Filtrar por año (ej: 2025)'
    )
    parser.add_argument(
        '--month',
        type=str,
        help='Filtrar por mes (ej: 01, 02, ..., 12)'
    )
    parser.add_argument(
        '--day',
        type=str,
        help='Filtrar por día (ej: 01, 02, ..., 31)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Límite de boletines a procesar'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=20,
        help='Tamaño del lote (default: 20)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Forzar re-indexación de documentos existentes'
    )

    args = parser.parse_args()

    indexador = IndexadorEmbeddingsMasivo(batch_size=args.batch_size)

    await indexador.indexar_embeddings(
        year=args.year,
        month=args.month,
        day=args.day,
        limit=args.limit,
        force=args.force
    )


if __name__ == "__main__":
    asyncio.run(main())

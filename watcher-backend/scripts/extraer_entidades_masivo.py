#!/usr/bin/env python3
"""
Script para extracción masiva de entidades de boletines
Lee archivos .txt procesados y extrae entidades + relaciones
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
from app.services.entity_service import get_entity_service
from sqlalchemy import select


class ExtractorEntidadesMasivo:
    """Extractor masivo de entidades"""

    def __init__(self, batch_size: int = 25):
        self.batch_size = batch_size
        self.entity_service = get_entity_service()
        self.processed_dir = Path("/Users/germanevangelisti/watcher-agent/watcher-monolith/backend/data/processed")

        # Estadísticas
        self.stats = {
            'boletines_procesados': 0,
            'entidades_creadas': 0,
            'entidades_actualizadas': 0,
            'menciones_creadas': 0,
            'relaciones_creadas': 0,
            'fallidos': 0,
            'tiempo_inicio': None,
            'tiempo_fin': None
        }

    async def extraer_entidades(
        self,
        year: str | None = None,
        month: str | None = None,
        day: str | None = None,
        limit: int | None = None
    ):
        """
        Extrae entidades de boletines completados

        Args:
            year: Filtrar por año (YYYY)
            month: Filtrar por mes (MM)
            day: Filtrar por día (DD)
            limit: Límite de boletines a procesar
        """
        self.stats['tiempo_inicio'] = datetime.now()

        print("=" * 70)
        print("  EXTRACCIÓN MASIVA DE ENTIDADES")
        print("=" * 70)

        async with AsyncSessionLocal() as db:
            # Construir query - solo boletines completados con texto extraído
            query = select(Boletin).where(Boletin.status == 'completed')

            # Aplicar filtros
            if year:
                query = query.where(Boletin.date.like(f"{year}%"))
                print(f"📅 Filtro: Año {year}")

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
                print("\n✅ No hay boletines para procesar")
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

                await self._procesar_lote(batch, db)

                print(f"✅ Lote {batch_num} completado\n")

            self.stats['tiempo_fin'] = datetime.now()
            self._imprimir_resumen()

    async def _procesar_lote(self, boletines, db):
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

                print(f"  [{idx}/{len(boletines)}] 🔄 Procesando: {boletin.filename}...", end=" ")

                # Extraer entidades
                entities = self.entity_service.extract_entities(text)

                # Persistir entidades
                persist_stats = await self.entity_service.persist_entities(
                    entities, boletin.id, db
                )

                # Detectar relaciones
                relationships = self.entity_service.detect_relationships(entities, text)

                # Persistir relaciones
                rel_count = await self.entity_service.persist_relationships(
                    relationships, boletin.id, entities, db
                )

                # Actualizar estadísticas
                self.stats['boletines_procesados'] += 1
                self.stats['entidades_creadas'] += persist_stats['created']
                self.stats['entidades_actualizadas'] += persist_stats['updated']
                self.stats['menciones_creadas'] += persist_stats['mentions']
                self.stats['relaciones_creadas'] += rel_count

                print(f"✅ ({len(entities)} ent, {rel_count} rel)")

            except Exception as e:
                print(f"  [{idx}/{len(boletines)}] ❌ Error: {boletin.filename}")
                print(f"      {str(e)}")
                self.stats['fallidos'] += 1

    def _imprimir_resumen(self):
        """Imprime resumen de la ejecución"""
        duracion = self.stats['tiempo_fin'] - self.stats['tiempo_inicio']
        duracion_seg = duracion.total_seconds()

        print("=" * 70)
        print("  RESUMEN DE EXTRACCIÓN DE ENTIDADES")
        print("=" * 70)
        print(f"📊 Boletines procesados:       {self.stats['boletines_procesados']}")
        print(f"🆕 Entidades creadas:          {self.stats['entidades_creadas']}")
        print(f"🔄 Entidades actualizadas:     {self.stats['entidades_actualizadas']}")
        print(f"📝 Menciones creadas:          {self.stats['menciones_creadas']}")
        print(f"🔗 Relaciones detectadas:      {self.stats['relaciones_creadas']}")
        print(f"❌ Fallidos:                   {self.stats['fallidos']}")
        print(f"⏱️  Tiempo total:               {duracion_seg:.1f}s")

        if self.stats['boletines_procesados'] > 0:
            tiempo_promedio = duracion_seg / self.stats['boletines_procesados']
            print(f"⚡ Tiempo promedio/boletín:    {tiempo_promedio:.2f}s")

        print("=" * 70)


async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Extracción masiva de entidades de boletines'
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
        default=25,
        help='Tamaño del lote (default: 25)'
    )

    args = parser.parse_args()

    extractor = ExtractorEntidadesMasivo(batch_size=args.batch_size)

    await extractor.extraer_entidades(
        year=args.year,
        month=args.month,
        day=args.day,
        limit=args.limit
    )


if __name__ == "__main__":
    asyncio.run(main())

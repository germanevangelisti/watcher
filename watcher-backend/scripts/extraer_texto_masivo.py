#!/usr/bin/env python3
"""
Script para extracción masiva de texto de PDFs de boletines
Procesa boletines pendientes y guarda el texto extraído
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Añadir el directorio raíz del proyecto al sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "watcher-monolith" / "backend"))

from app.db.database import AsyncSessionLocal
from app.db.models import Boletin
from app.services.pdf_service import PDFProcessor
from sqlalchemy import select


class ExtractorTextoMasivo:
    """Extractor masivo de texto de boletines"""
    
    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
        self.pdf_processor = PDFProcessor()
        self.boletines_dir = Path("/Users/germanevangelisti/watcher-agent/boletines")
        
        # Estadísticas
        self.stats = {
            'procesados': 0,
            'fallidos': 0,
            'saltados': 0,
            'total': 0,
            'tiempo_inicio': None,
            'tiempo_fin': None
        }
    
    async def extraer_texto(
        self,
        year: Optional[str] = None,
        month: Optional[str] = None,
        limit: Optional[int] = None
    ):
        """
        Extrae texto de boletines pendientes
        
        Args:
            year: Filtrar por año (YYYY)
            month: Filtrar por mes (MM)
            limit: Límite de boletines a procesar
        """
        self.stats['tiempo_inicio'] = datetime.now()
        
        print("=" * 70)
        print("  EXTRACCIÓN MASIVA DE TEXTO DE BOLETINES")
        print("=" * 70)
        
        async with AsyncSessionLocal() as db:
            # Construir query
            query = select(Boletin).where(Boletin.status == 'pending')
            
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
            
            if limit:
                query = query.limit(limit)
                print(f"🔢 Límite: {limit} boletines")
            
            # Ejecutar query
            result = await db.execute(query)
            boletines = result.scalars().all()
            
            self.stats['total'] = len(boletines)
            
            if not boletines:
                print("\n✅ No hay boletines pendientes para procesar")
                return
            
            print(f"\n📊 Encontrados: {len(boletines)} boletines pendientes")
            print(f"📦 Procesando en lotes de {self.batch_size}...\n")
            
            # Procesar en lotes
            for i in range(0, len(boletines), self.batch_size):
                batch = boletines[i:i + self.batch_size]
                batch_num = (i // self.batch_size) + 1
                total_batches = (len(boletines) + self.batch_size - 1) // self.batch_size
                
                print(f"🔄 Lote {batch_num}/{total_batches} ({len(batch)} boletines)")
                print("-" * 70)
                
                await self._procesar_lote(batch, db)
                
                # Commit después de cada lote
                await db.commit()
                
                print(f"✅ Lote {batch_num} completado\n")
            
            self.stats['tiempo_fin'] = datetime.now()
            self._imprimir_resumen()
    
    async def _procesar_lote(self, boletines: List[Boletin], db):
        """Procesa un lote de boletines"""
        
        for idx, boletin in enumerate(boletines, 1):
            try:
                # Construir path al PDF
                year = boletin.date[:4]
                month = boletin.date[4:6]
                pdf_path = self.boletines_dir / year / month / boletin.filename
                
                # Verificar si el PDF existe
                if not pdf_path.exists():
                    print(f"  [{idx}/{len(boletines)}] ⚠️  PDF no encontrado: {boletin.filename}")
                    boletin.status = 'failed'
                    boletin.error_message = f"PDF no encontrado: {pdf_path}"
                    self.stats['fallidos'] += 1
                    continue
                
                # Verificar si el txt ya existe
                txt_path = self.pdf_processor.processed_dir / f"{pdf_path.stem}.txt"
                if txt_path.exists():
                    print(f"  [{idx}/{len(boletines)}] ⏭️  Ya existe: {boletin.filename}")
                    boletin.status = 'completed'
                    boletin.error_message = None
                    self.stats['saltados'] += 1
                    continue
                
                # Procesar PDF
                print(f"  [{idx}/{len(boletines)}] 🔄 Procesando: {boletin.filename}...", end=" ")
                
                inicio = datetime.now()
                _txt_result = await self.pdf_processor.process_pdf(pdf_path)
                duracion = (datetime.now() - inicio).total_seconds()
                
                # Actualizar estado
                boletin.status = 'completed'
                boletin.error_message = None
                
                self.stats['procesados'] += 1
                print(f"✅ ({duracion:.1f}s)")
                
            except Exception as e:
                print(f"  [{idx}/{len(boletines)}] ❌ Error: {boletin.filename}")
                print(f"      {str(e)}")
                boletin.status = 'failed'
                boletin.error_message = str(e)
                self.stats['fallidos'] += 1
    
    def _imprimir_resumen(self):
        """Imprime resumen de la ejecución"""
        duracion = self.stats['tiempo_fin'] - self.stats['tiempo_inicio']
        duracion_seg = duracion.total_seconds()
        
        print("=" * 70)
        print("  RESUMEN DE EXTRACCIÓN")
        print("=" * 70)
        print(f"✅ Procesados exitosamente: {self.stats['procesados']}")
        print(f"⏭️  Ya existían (saltados):  {self.stats['saltados']}")
        print(f"❌ Fallidos:                {self.stats['fallidos']}")
        print(f"📊 Total:                   {self.stats['total']}")
        print(f"⏱️  Tiempo total:            {duracion_seg:.1f}s")
        
        if self.stats['procesados'] > 0:
            tiempo_promedio = duracion_seg / self.stats['procesados']
            print(f"⚡ Tiempo promedio/PDF:     {tiempo_promedio:.2f}s")
        
        print("=" * 70)


async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Extracción masiva de texto de boletines'
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
        '--limit',
        type=int,
        help='Límite de boletines a procesar'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Tamaño del lote (default: 50)'
    )
    
    args = parser.parse_args()
    
    extractor = ExtractorTextoMasivo(batch_size=args.batch_size)
    
    await extractor.extraer_texto(
        year=args.year,
        month=args.month,
        limit=args.limit
    )


if __name__ == "__main__":
    asyncio.run(main())

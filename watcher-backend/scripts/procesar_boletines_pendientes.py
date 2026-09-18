"""
Script para procesar boletines pendientes
Extrae contenido de PDFs y analiza con Watcher
"""

import asyncio
import sys
from pathlib import Path

# Agregar path del backend
sys.path.insert(0, str(Path(__file__).parent.parent / "watcher-monolith" / "backend"))

from app.db.database import AsyncSessionLocal
from app.db.models import Boletin
from app.services.batch_processor import BatchProcessor
from sqlalchemy import select


async def main():
    print("=" * 60)
    print("  PROCESAMIENTO DE BOLETINES PENDIENTES")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # Obtener boletines pendientes
        query = select(Boletin).where(Boletin.status == 'pending').limit(50)
        result = await db.execute(query)
        boletines = result.scalars().all()

        print(f"\n📊 Encontrados: {len(boletines)} boletines pendientes")
        print("🎯 Procesando los primeros 50...\n")

        if not boletines:
            print("✅ No hay boletines pendientes para procesar")
            return

        # Crear procesador
        processor = BatchProcessor(db)

        # Procesar cada boletín
        procesados = 0
        errores = 0

        for i, boletin in enumerate(boletines, 1):
            try:
                print(f"[{i}/{len(boletines)}] Procesando: {boletin.filename}...")

                # Construir path al PDF
                pdf_path = Path(f"/Users/germanevangelisti/watcher-agent/boletines/{boletin.date[:4]}/{boletin.date[4:6]}/{boletin.filename}")

                if not pdf_path.exists():
                    print(f"  ⚠️  PDF no encontrado: {pdf_path}")
                    errores += 1
                    continue

                # Procesar PDF
                result = await processor._process_single_pdf(pdf_path)

                if result.get("status") == "success":
                    procesados += 1
                    print("  ✅ Procesado exitosamente")
                else:
                    errores += 1
                    print(f"  ❌ Error: {result.get('error', 'Unknown')}")

            except Exception as e:
                errores += 1
                print(f"  ❌ Error: {str(e)}")

        print("\n" + "=" * 60)
        print("  RESUMEN")
        print("=" * 60)
        print(f"✅ Procesados:  {procesados}")
        print(f"❌ Errores:     {errores}")
        print(f"📊 Total:       {len(boletines)}")
        print("=" * 60)

        if procesados > 0:
            print("\n🎉 ¡Boletines procesados! Ahora puedes ejecutar los análisis.")
            print("   Ve a 'Agentes IA' → 'Análisis Personalizado' y ejecuta nuevamente.")

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Script para registrar todos los boletines físicos en la base de datos
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio raíz del proyecto al sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.database import AsyncSessionLocal
from app.db.models import Boletin, FuenteBoletin
from app.services.url_fetcher import build_url_cordoba_provincial
from sqlalchemy import select, update

async def register_boletines():
    """Registra todos los PDFs físicos en la base de datos"""
    
    # Directorio de boletines
    boletines_dir = Path("/Users/germanevangelisti/watcher-agent/boletines")
    
    if not boletines_dir.exists():
        print(f"❌ Directorio no encontrado: {boletines_dir}")
        return
    
    # Encontrar todos los PDFs
    pdf_files = list(boletines_dir.glob("**/*.pdf"))
    print(f"📁 Encontrados {len(pdf_files)} PDFs en el sistema de archivos")
    
    async with AsyncSessionLocal() as db:
        # Obtener boletines existentes en la BD
        result = await db.execute(select(Boletin.filename))
        existing_filenames = {row[0] for row in result.all()}
        print(f"📊 Ya hay {len(existing_filenames)} boletines registrados en la BD")
        
        registered = 0
        skipped = 0
        failed = 0
        
        for pdf_path in pdf_files:
            filename = pdf_path.name
            
            # Skip si ya existe
            if filename in existing_filenames:
                skipped += 1
                continue
            
            try:
                # Parsear nombre del archivo: YYYYMMDD_N_Secc.pdf
                parts = filename.replace('.pdf', '').split('_')
                if len(parts) < 3:
                    print(f"⚠️  Formato inválido: {filename}")
                    failed += 1
                    continue
                
                date_str = parts[0]  # YYYYMMDD
                section_num = parts[1]  # 1-5
                
                # Mapeo de secciones
                section_names = {
                    '1': 'Designaciones y Decretos',
                    '2': 'Compras y Contrataciones',
                    '3': 'Subsidios y Transferencias',
                    '4': 'Obras Públicas',
                    '5': 'Notificaciones Judiciales'
                }
                
                # Crear registro
                boletin = Boletin(
                    filename=filename,
                    date=date_str,
                    section=section_names.get(section_num, f'Sección {section_num}'),
                    status='pending',
                    fuente=FuenteBoletin.PROVINCIAL,
                    jurisdiccion_id=1,  # Provincia de Córdoba
                    seccion_nombre=section_names.get(section_num),
                    source_url=build_url_cordoba_provincial(filename),
                    origin='synced',
                )
                
                db.add(boletin)
                registered += 1
                
                # Commit cada 100 registros
                if registered % 100 == 0:
                    await db.commit()
                    print(f"  ✅ Registrados {registered} boletines...")
                
            except Exception as e:
                print(f"❌ Error procesando {filename}: {e}")
                failed += 1
        
        # Commit final
        await db.commit()
        
        # Fix masivo: actualizar boletines existentes sin jurisdiccion_id
        print("\n🔧 Actualizando boletines existentes sin jurisdicción...")
        result = await db.execute(
            update(Boletin)
            .where(Boletin.jurisdiccion_id.is_(None))
            .where(Boletin.fuente == 'provincial')
            .values(jurisdiccion_id=1)
        )
        await db.commit()
        updated = result.rowcount if result.rowcount else 0
        print(f"  ✅ Actualizados: {updated} boletines")
        
        print("\n📊 Resumen:")
        print(f"  ✅ Registrados:  {registered}")
        print(f"  ⏭️  Ya existían:  {skipped}")
        print(f"  🔧 Actualizados: {updated}")
        print(f"  ❌ Fallidos:     {failed}")
        print(f"  📁 Total en BD:  {registered + len(existing_filenames)}")

if __name__ == "__main__":
    print("🚀 Registrando boletines en la base de datos...\n")
    asyncio.run(register_boletines())
    print("\n✅ Proceso completado!")

#!/usr/bin/env python3
"""
Script para registrar todos los boletines existentes en el filesystem
"""
import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.database import AsyncSessionLocal
from app.db.models import BoletinDocument

BOLETINES_BASE_DIR = Path("/Users/germanevangelisti/watcher-agent/boletines")


def parse_filename(filename: str):
    """
    Parsear filename: YYYYMMDD_N_Secc.pdf
    Returns: (year, month, day, section) o None si no es válido
    """
    if not filename.endswith('.pdf'):
        return None

    parts = filename.replace('.pdf', '').split('_')
    if len(parts) != 3:
        return None

    try:
        date_str = parts[0]
        section = int(parts[1])

        if len(date_str) != 8:
            return None

        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])

        return (year, month, day, section)
    except Exception:
        return None


async def register_boletines():
    """Registrar todos los boletines encontrados"""
    print("🔍 Escaneando directorio de boletines...")
    print(f"   Base: {BOLETINES_BASE_DIR}")
    print()

    if not BOLETINES_BASE_DIR.exists():
        print(f"❌ Directorio no existe: {BOLETINES_BASE_DIR}")
        return False

    # Buscar todos los PDFs
    pdf_files = list(BOLETINES_BASE_DIR.rglob("*.pdf"))
    print(f"📄 Encontrados {len(pdf_files)} archivos PDF")
    print()

    if not pdf_files:
        print("⚠️  No se encontraron archivos PDF")
        return True

    # Procesar archivos
    documents_to_register = []
    skipped = []

    for pdf_path in pdf_files:
        filename = pdf_path.name
        parsed = parse_filename(filename)

        if not parsed:
            skipped.append(f"{filename} (formato inválido)")
            continue

        year, month, day, section = parsed

        # Calcular tamaño
        try:
            file_size = pdf_path.stat().st_size
        except Exception:
            file_size = None

        documents_to_register.append({
            "filename": filename,
            "year": year,
            "month": month,
            "day": day,
            "section": section,
            "file_path": str(pdf_path),
            "file_size_bytes": file_size
        })

    print(f"✅ Válidos para registrar: {len(documents_to_register)}")
    print(f"⚠️  Omitidos: {len(skipped)}")

    if skipped and len(skipped) <= 10:
        for s in skipped:
            print(f"   • {s}")
    elif skipped:
        print("   Mostrando primeros 10:")
        for s in skipped[:10]:
            print(f"   • {s}")
        print(f"   ... y {len(skipped) - 10} más")

    print()

    # Registrar en la BD
    async with AsyncSessionLocal() as session:
        print("💾 Registrando en base de datos...")

        registered = 0
        duplicates = 0
        errors = 0

        for doc_data in documents_to_register:
            try:
                # Verificar si ya existe
                from sqlalchemy import select
                stmt = select(BoletinDocument).where(
                    BoletinDocument.filename == doc_data["filename"]
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    duplicates += 1
                    continue

                # Crear nuevo documento
                document = BoletinDocument(**doc_data)
                session.add(document)
                registered += 1

                # Commit en batches de 100
                if registered % 100 == 0:
                    await session.commit()
                    print(f"   Procesados: {registered + duplicates + errors}/{len(documents_to_register)}")

            except Exception as e:
                print(f"   ❌ Error con {doc_data['filename']}: {e}")
                errors += 1
                continue

        # Commit final
        try:
            await session.commit()
        except Exception as e:
            print(f"❌ Error en commit final: {e}")
            await session.rollback()
            return False

    print()
    print("="*60)
    print("📊 RESUMEN FINAL")
    print("="*60)
    print(f"✅ Nuevos registrados: {registered}")
    print(f"⏭️  Ya existían: {duplicates}")
    print(f"❌ Errores: {errors}")
    print(f"📁 Total en filesystem: {len(pdf_files)}")
    print("="*60)
    print()

    # Estadísticas por año/mes
    async with AsyncSessionLocal() as session:
        from sqlalchemy import func, select

        stmt = select(
            BoletinDocument.year,
            BoletinDocument.month,
            func.count(BoletinDocument.id)
        ).group_by(
            BoletinDocument.year,
            BoletinDocument.month
        ).order_by(
            BoletinDocument.year,
            BoletinDocument.month
        )

        result = await session.execute(stmt)
        stats = result.all()

        if stats:
            print("📈 DOCUMENTOS POR MES:")
            print("="*60)
            current_year = None
            for year, month, count in stats:
                if year != current_year:
                    if current_year is not None:
                        print()
                    print(f"   Año {year}:")
                    current_year = year
                print(f"      {month:02d}: {count} documentos")
            print("="*60)

    return True


if __name__ == "__main__":
    print()
    print("="*60)
    print("🚀 REGISTRO DE BOLETINES EXISTENTES")
    print("="*60)
    print()

    success = asyncio.run(register_boletines())

    print()
    if success:
        print("✅ Proceso completado exitosamente")
    else:
        print("❌ Proceso terminó con errores")
    print()

    sys.exit(0 if success else 1)


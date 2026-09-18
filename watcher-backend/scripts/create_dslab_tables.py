#!/usr/bin/env python3
"""
Script para crear las tablas del DS Lab en la base de datos
"""
import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.database import Base, engine


async def create_tables():
    """Crear tablas del DS Lab"""
    print("🚀 Creando tablas del DS Lab...")

    try:
        # Crear todas las tablas usando el engine asíncrono
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✅ Tablas creadas exitosamente:")
        print("   • boletin_documents")
        print("   • analysis_configs")
        print("   • analysis_executions")
        print("   • analysis_results")
        print("   • red_flags")
        print("   • analysis_comparisons")

        return True

    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(create_tables())
    sys.exit(0 if success else 1)


"""
Script de Limpieza de Base de Datos
Limpia datos de procesamiento manteniendo estructura y boletines base.

Ejecutar desde: watcher-monolith/backend/
Comando: python ../../scripts/limpiar_db.py
"""

import asyncio
from pathlib import Path

# Asegurar que estamos en el directorio correcto
if not Path("app").exists():
    print("❌ Error: Este script debe ejecutarse desde watcher-monolith/backend/")
    print("   Comando: cd watcher-monolith/backend && python ../../scripts/limpiar_db.py")
    exit(1)

from app.db.database import AsyncSessionLocal
from sqlalchemy import text


async def limpiar_base_datos():
    """
    Limpia la base de datos manteniendo estructura y boletines básicos.
    
    Elimina:
    - Todos los análisis
    - Todas las menciones jurisdiccionales
    - Estados de sincronización
    - Workflows y ejecuciones
    - Análisis de agentes
    
    Mantiene:
    - Estructura de tablas
    - Boletines descargados
    - Jurisdicciones
    - Configuraciones
    """

    print("🧹 Iniciando limpieza de base de datos...")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            # 1. Limpiar menciones jurisdiccionales
            print("\n📍 Limpiando menciones jurisdiccionales...")
            result = await db.execute(text("SELECT COUNT(*) FROM menciones_jurisdiccionales"))
            count_menciones = result.scalar()
            print(f"   → {count_menciones} menciones encontradas")

            await db.execute(text("DELETE FROM menciones_jurisdiccionales"))
            print(f"   ✅ {count_menciones} menciones eliminadas")

            # 2. Limpiar análisis
            print("\n📊 Limpiando análisis...")
            result = await db.execute(text("SELECT COUNT(*) FROM analisis"))
            count_analisis = result.scalar()
            print(f"   → {count_analisis} análisis encontrados")

            await db.execute(text("DELETE FROM analisis"))
            print(f"   ✅ {count_analisis} análisis eliminados")

            # 3. Limpiar alertas
            print("\n🚨 Limpiando alertas...")
            result = await db.execute(text("SELECT COUNT(*) FROM alertas"))
            count_alertas = result.scalar()
            print(f"   → {count_alertas} alertas encontradas")

            await db.execute(text("DELETE FROM alertas"))
            print(f"   ✅ {count_alertas} alertas eliminadas")

            # 4. Limpiar ejecuciones de workflows
            print("\n⚙️  Limpiando ejecuciones de workflows...")
            result = await db.execute(text("SELECT COUNT(*) FROM workflow_executions"))
            count_executions = result.scalar()
            print(f"   → {count_executions} ejecuciones encontradas")

            await db.execute(text("DELETE FROM workflow_executions"))
            print(f"   ✅ {count_executions} ejecuciones eliminadas")

            # 5. Resetear estado de sync
            print("\n🔄 Reseteando estado de sincronización...")
            result = await db.execute(text("SELECT COUNT(*) FROM sync_state"))
            count_sync = result.scalar()

            if count_sync > 0:
                await db.execute(text("DELETE FROM sync_state"))
                print("   ✅ Estado de sync reseteado")
            else:
                print("   ℹ️  No hay estado de sync para resetear")

            # 6. Resetear estados de boletines
            print("\n📄 Reseteando estados de boletines...")
            result = await db.execute(text("SELECT COUNT(*) FROM boletines"))
            count_boletines = result.scalar()
            print(f"   → {count_boletines} boletines encontrados")

            # Resetear status a 'pending' y limpiar mensajes de error
            await db.execute(text("""
                UPDATE boletines 
                SET status = 'pending',
                    error_message = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE status != 'pending'
            """))
            print("   ✅ Estados de boletines reseteados a 'pending'")

            # 7. Mantener jurisdicciones (no eliminar)
            result = await db.execute(text("SELECT COUNT(*) FROM jurisdicciones"))
            count_jurisdicciones = result.scalar()
            print(f"\n🏛️  Jurisdicciones: {count_jurisdicciones} (mantenidas)")

            # 8. Verificar boletines por fuente
            print("\n📊 Distribución de boletines por fuente:")
            result = await db.execute(text("""
                SELECT fuente, COUNT(*) as count 
                FROM boletines 
                GROUP BY fuente
            """))
            for row in result:
                print(f"   → {row[0]}: {row[1]} boletines")

            # Commit de todos los cambios
            await db.commit()

            print("\n" + "=" * 60)
            print("✅ Limpieza completada exitosamente!")
            print("\n📋 Resumen:")
            print(f"   • {count_menciones} menciones eliminadas")
            print(f"   • {count_analisis} análisis eliminados")
            print(f"   • {count_alertas} alertas eliminadas")
            print(f"   • {count_executions} ejecuciones eliminadas")
            print(f"   • {count_boletines} boletines reseteados")
            print(f"   • {count_jurisdicciones} jurisdicciones mantenidas")
            print("\n🎯 Base de datos lista para procesamiento limpio!")

        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error durante la limpieza: {e}")
            raise
        finally:
            await db.close()


async def verificar_estado():
    """Verifica el estado actual de la base de datos."""
    print("\n🔍 Verificando estado actual de la base de datos...")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            # Tablas a verificar
            tablas = [
                "boletines",
                "jurisdicciones",
                "menciones_jurisdiccionales",
                "analisis",
                "alertas",
                "workflow_executions",
                "sync_state"
            ]

            print("\n📊 Conteo de registros por tabla:")
            for tabla in tablas:
                try:
                    result = await db.execute(text(f"SELECT COUNT(*) FROM {tabla}"))
                    count = result.scalar()
                    print(f"   • {tabla:30} → {count:6} registros")
                except Exception as e:
                    print(f"   • {tabla:30} → ERROR: {str(e)[:50]}")

            print("\n" + "=" * 60)

        except Exception as e:
            print(f"\n❌ Error verificando estado: {e}")
        finally:
            await db.close()


async def main():
    """Función principal."""
    print("\n" + "=" * 60)
    print("🗑️  SCRIPT DE LIMPIEZA DE BASE DE DATOS")
    print("=" * 60)

    # Mostrar estado actual
    await verificar_estado()

    # Confirmar con usuario
    print("\n⚠️  ADVERTENCIA: Esta operación eliminará:")
    print("   • Todos los análisis")
    print("   • Todas las menciones")
    print("   • Todas las alertas")
    print("   • Todas las ejecuciones de workflows")
    print("   • Estado de sincronización")
    print("\n✅ Se mantendrán:")
    print("   • Boletines descargados (reseteados a 'pending')")
    print("   • Jurisdicciones")
    print("   • Estructura de tablas")

    respuesta = input("\n¿Deseas continuar? (si/no): ").lower().strip()

    if respuesta in ['si', 's', 'yes', 'y']:
        print("\n🚀 Iniciando limpieza...")
        await limpiar_base_datos()

        # Verificar estado final
        print("\n" + "=" * 60)
        await verificar_estado()

    else:
        print("\n❌ Operación cancelada por el usuario.")


if __name__ == "__main__":
    asyncio.run(main())

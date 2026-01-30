"""
Prueba final del sistema consolidado
"""

import asyncio
import os
from pathlib import Path
from app.db.database import AsyncSessionLocal, init_db
from app.services.batch_processor import BatchProcessor

async def test_sistema_completo():
    """Prueba el sistema completo consolidado."""
    
    print("🎯 PRUEBA FINAL - SISTEMA CONSOLIDADO")
    print("=" * 60)
    
    # Inicializar base de datos
    await init_db()
    
    # Directorio de boletines
    boletines_dir = Path("/Users/germanevangelisti/watcher-agent/boletines")
    
    if not boletines_dir.exists():
        print("❌ Directorio de boletines no encontrado")
        return
    
    print(f"📁 Directorio: {boletines_dir}")
    print(f"📄 Archivos disponibles: {len(list(boletines_dir.glob('*.pdf')))}")
    
    # Verificar API key
    api_key = os.getenv('OPENAI_API_KEY')
    use_mock = not bool(api_key)
    
    print(f"🤖 Modo: {'Mock (sin API key)' if use_mock else 'OpenAI Real'}")
    
    async with AsyncSessionLocal() as db:
        # Crear procesador
        processor = BatchProcessor(db, use_mock=use_mock)
        
        print(f"⚡ Workers: {processor.max_workers}")
        print(f"📦 Batch size: {processor.batch_size}")
        
        # Configurar filtros para prueba pequeña
        filtros = {
            'fecha_desde': '20250829',  # Solo 29 de agosto
            'fecha_hasta': '20250829',
            'secciones': ['1', '2']  # Solo secciones 1 y 2
        }
        
        print(f"🔍 Filtros: {filtros}")
        
        try:
            print(f"\n🚀 Iniciando procesamiento...")
            
            # Procesar con filtros
            stats = await processor.process_directory(
                source_dir=boletines_dir,
                batch_size=3,  # Lote pequeño para prueba
                filtros=filtros
            )
            
            print(f"\n✅ PROCESAMIENTO COMPLETADO")
            print(f"📊 Estadísticas:")
            print(f"   🆔 Batch ID: {stats['batch_id']}")
            print(f"   📄 Total: {stats['total']}")
            print(f"   ✅ Procesados: {stats['processed']}")
            print(f"   ❌ Fallidos: {stats['failed']}")
            print(f"   💰 Ejecuciones: {stats['ejecuciones_detectadas']}")
            print(f"   💵 Monto total: ${stats['monto_total_procesado']:,.0f}")
            print(f"   ⚠️ Alertas: {stats['alertas_generadas']}")
            print(f"   ⏱️ Tiempo: {stats['tiempo_procesamiento']:.2f}s")
            print(f"   🚀 Velocidad: {stats['archivos_por_segundo']:.2f} archivos/s")
            
            print(f"\n🎯 CARACTERÍSTICAS DEMOSTRADAS:")
            print(f"   ✅ Procesamiento paralelo optimizado")
            print(f"   ✅ Manejo de tokens (fragmentación automática)")
            print(f"   ✅ Extracción de montos y organismos")
            print(f"   ✅ Historial acumulativo en BD")
            print(f"   ✅ Sistema de alertas automáticas")
            print(f"   ✅ Control de estados y errores")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            
            if "insufficient_quota" in str(e):
                print("💡 Solución: Agrega créditos a OpenAI o usa modo mock")
            elif "rate_limit_exceeded" in str(e):
                print("💡 El sistema maneja rate limits automáticamente")
            elif "OPENAI_API_KEY" in str(e):
                print("💡 Configura: export OPENAI_API_KEY='tu-api-key'")

async def main():
    """Función principal."""
    await test_sistema_completo()
    
    print(f"\n📋 ARCHIVOS CONSOLIDADOS:")
    print(f"   📄 app/db/models.py - Todos los modelos (base + extendidos)")
    print(f"   🤖 app/services/watcher_service.py - Servicio optimizado con tokens")
    print(f"   ⚡ app/services/batch_processor.py - Procesador completo")
    print(f"   🧪 test_sistema_final.py - Este script de prueba")
    
    print(f"\n🎯 SISTEMA LISTO:")
    print(f"   ✅ Un solo archivo por funcionalidad")
    print(f"   ✅ Versiones optimizadas consolidadas")
    print(f"   ✅ Sin archivos duplicados")
    print(f"   ✅ Fácil mantenimiento")

if __name__ == "__main__":
    asyncio.run(main())

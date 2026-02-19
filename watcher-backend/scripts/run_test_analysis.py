#!/usr/bin/env python3
"""
Script para ejecutar un análisis de prueba en un subset de documentos
"""
import sys
import asyncio
import httpx
from pathlib import Path

# Agregar el directorio raíz al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

API_BASE = "http://localhost:8001/api/v1/dslab"


async def run_test_analysis():
    """Ejecutar análisis de prueba"""
    print()
    print("="*70)
    print("🧪 ANÁLISIS DE PRUEBA - WATCHER DS LAB")
    print("="*70)
    print()
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # 1. Verificar configuración
        print("1️⃣  Verificando configuración...")
        try:
            response = await client.get(f"{API_BASE}/configs")
            configs = response.json()
            
            if not configs:
                print("❌ No hay configuraciones. Ejecuta create_initial_config.py primero")
                return False
            
            active_config = next((c for c in configs if c['is_active']), configs[0])
            print(f"   ✅ Config activa: {active_config['config_name']} v{active_config['version']}")
            print(f"      ID: {active_config['id']}")
            print()
            
        except Exception as e:
            print(f"❌ Error obteniendo configs: {e}")
            return False
        
        # 2. Seleccionar subset de documentos
        print("2️⃣  Seleccionando documentos de prueba...")
        try:
            # Obtener documentos de enero 2025 (primer mes)
            response = await client.get(f"{API_BASE}/documents?year=2025&month=1&limit=10")
            documents = response.json()
            
            if not documents:
                print("❌ No hay documentos para analizar")
                return False
            
            print(f"   ✅ Seleccionados {len(documents)} documentos de enero 2025")
            for doc in documents[:5]:
                print(f"      • {doc['filename']}")
            if len(documents) > 5:
                print(f"      ... y {len(documents) - 5} más")
            print()
            
        except Exception as e:
            print(f"❌ Error obteniendo documentos: {e}")
            return False
        
        # 3. Iniciar ejecución
        print("3️⃣  Iniciando análisis...")
        try:
            execution_data = {
                "execution_name": "Test Analysis - Enero 2025 (10 docs)",
                "config_id": active_config['id'],
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "sections": [1, 2, 3, 4, 5]
            }
            
            response = await client.post(
                f"{API_BASE}/analysis/executions",
                json=execution_data
            )
            
            if response.status_code != 201:
                print(f"❌ Error iniciando análisis: {response.text}")
                return False
            
            execution = response.json()
            execution_id = execution['id']
            
            print(f"   ✅ Ejecución iniciada - ID: {execution_id}")
            print(f"      Total documentos: {execution['total_documents']}")
            print()
            
        except Exception as e:
            print(f"❌ Error iniciando análisis: {e}")
            return False
        
        # 4. Monitorear progreso
        print("4️⃣  Monitoreando progreso...")
        print()
        
        last_processed = 0
        while True:
            try:
                response = await client.get(
                    f"{API_BASE}/analysis/executions/{execution_id}/progress"
                )
                progress = response.json()
                
                status = progress['status']
                processed = progress['processed_documents']
                total = progress['total_documents']
                failed = progress['failed_documents']
                
                # Mostrar progreso si cambió
                if processed != last_processed:
                    percentage = (processed / total * 100) if total > 0 else 0
                    current = progress.get('current_document', '...')
                    
                    print(f"   📊 {processed}/{total} ({percentage:.1f}%) | ❌ {failed} | 📄 {current}")
                    last_processed = processed
                
                if status == 'completed':
                    print()
                    print("   ✅ Análisis completado!")
                    break
                elif status == 'failed':
                    print()
                    print("   ❌ Análisis falló")
                    return False
                
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"   ⚠️  Error monitoreando: {e}")
                await asyncio.sleep(2)
                continue
        
        print()
        
        # 5. Obtener resumen
        print("5️⃣  Obteniendo resultados...")
        try:
            response = await client.get(
                f"{API_BASE}/analysis/executions/{execution_id}/summary"
            )
            summary = response.json()
            
            print()
            print("="*70)
            print("📊 RESUMEN DE RESULTADOS")
            print("="*70)
            print(f"Estado: {summary['status']}")
            print(f"Documentos procesados: {summary['processed_documents']}/{summary['total_documents']}")
            print(f"Documentos fallidos: {summary['failed_documents']}")
            print()
            
            if summary.get('avg_transparency_score'):
                print(f"Score promedio de transparencia: {summary['avg_transparency_score']:.1f}/100")
            
            print()
            print("Distribución de riesgo:")
            risk_dist = summary.get('risk_distribution', {})
            for level, count in risk_dist.items():
                emoji = "🔴" if level == "high" else "🟡" if level == "medium" else "🟢"
                print(f"   {emoji} {level.upper()}: {count} documentos")
            
            print()
            print(f"Total red flags detectadas: {summary.get('total_red_flags', 0)}")
            
            flags_by_severity = summary.get('red_flags_by_severity', {})
            if flags_by_severity:
                print("Por severidad:")
                for severity, count in flags_by_severity.items():
                    print(f"   • {severity}: {count}")
            
            print()
            duration = summary.get('duration_seconds', 0)
            print(f"Duración: {duration:.1f} segundos")
            
            if duration > 0 and summary['processed_documents'] > 0:
                rate = summary['processed_documents'] / duration
                print(f"Velocidad: {rate:.2f} docs/segundo")
            
            print("="*70)
            print()
            
        except Exception as e:
            print(f"❌ Error obteniendo resumen: {e}")
            return False
        
        # 6. Ver top red flags
        print("6️⃣  Top Red Flags Detectadas...")
        try:
            response = await client.get(
                f"{API_BASE}/red-flags?execution_id={execution_id}&limit=10"
            )
            red_flags = response.json()
            
            if red_flags:
                print()
                for i, flag in enumerate(red_flags[:5], 1):
                    severity_emoji = "🔴" if flag['severity'] == "high" else "🟡" if flag['severity'] == "medium" else "ℹ️"
                    print(f"{i}. {severity_emoji} [{flag['severity'].upper()}] {flag['title']}")
                    print(f"   Tipo: {flag['flag_type']} | Categoría: {flag['category']}")
                    if flag.get('description'):
                        desc = flag['description'][:80] + "..." if len(flag['description']) > 80 else flag['description']
                        print(f"   {desc}")
                    print()
            else:
                print("   ✅ No se detectaron red flags")
            
        except Exception as e:
            print(f"⚠️  Error obteniendo red flags: {e}")
        
        print("="*70)
        print()
        print("✅ ANÁLISIS DE PRUEBA COMPLETADO EXITOSAMENTE")
        print()
        print("💡 Próximos pasos:")
        print("   • Revisar resultados en la BD")
        print("   • Ver detalles: GET /api/v1/dslab/analysis/executions/{execution_id}/results")
        print("   • Ajustar parámetros de configuración si es necesario")
        print("   • Ejecutar análisis completo cuando estés listo")
        print()
        
        return True


if __name__ == "__main__":
    print()
    print("⚠️  IMPORTANTE: Asegúrate de que el backend esté corriendo en http://localhost:8001")
    print()
    
    success = asyncio.run(run_test_analysis())
    sys.exit(0 if success else 1)


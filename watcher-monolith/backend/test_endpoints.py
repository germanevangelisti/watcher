"""
Script para probar los endpoints de la API
"""

import asyncio
import httpx
import json

async def test_endpoints():
    """Prueba los endpoints principales de la API."""
    
    base_url = "http://127.0.0.1:8001"
    
    async with httpx.AsyncClient() as client:
        
        print("🚀 Probando endpoints de la API Watcher...")
        
        # 1. Probar endpoint de documentación
        try:
            response = await client.get(f"{base_url}/docs")
            print(f"✅ Documentación API: {response.status_code}")
        except Exception as e:
            print(f"❌ Error en documentación: {e}")
        
        # 2. Probar endpoint de estado de boletines
        try:
            response = await client.get(f"{base_url}/api/v1/boletines/status/")
            print(f"✅ Estado de boletines: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   📊 Total boletines: {data.get('total', 0)}")
                print(f"   📈 Estadísticas: {data.get('stats', {})}")
        except Exception as e:
            print(f"❌ Error en estado boletines: {e}")
        
        # 3. Probar endpoint de estadísticas batch
        try:
            response = await client.get(f"{base_url}/api/v1/batch/stats/")
            print(f"✅ Estadísticas batch: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   📊 Stats batch: {data}")
        except Exception as e:
            print(f"❌ Error en stats batch: {e}")
        
        # 4. Probar endpoint de análisis de texto (mock)
        try:
            test_text = "Decreto N° 123 - Se designa a Juan Pérez como Director General."
            response = await client.post(
                f"{base_url}/api/v1/watcher/analyze/text/mock/",
                params={"text": test_text, "max_fragments": 1}
            )
            print(f"✅ Análisis de texto (mock): {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   🔍 Análisis: {data['analysis']['categoria']} - {data['analysis']['riesgo']}")
                print(f"   📝 Servicio: {data['service']}")
        except Exception as e:
            print(f"❌ Error en análisis texto: {e}")
        
        print("\n🎉 Pruebas completadas!")

if __name__ == "__main__":
    asyncio.run(test_endpoints())

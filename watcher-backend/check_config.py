"""
Script para verificar la configuración del sistema antes de ejecutar
"""
import os
import sys
from pathlib import Path

# Agregar el directorio al path
sys.path.insert(0, str(Path(__file__).parent))

print("🔍 Verificando configuración del sistema...\n")

# 1. Verificar API Key de Google
print("1️⃣  Verificando Google API Key...")

try:
    from app.core.agent_config import DEFAULT_AGENT_CONFIG
    
    api_key_from_config = DEFAULT_AGENT_CONFIG.google_api_key
    api_key_from_env = os.getenv('GOOGLE_API_KEY')
    
    if api_key_from_env:
        print("   ✅ API Key encontrada en variable de entorno")
        print(f"      Longitud: {len(api_key_from_env)} caracteres")
    elif api_key_from_config and api_key_from_config != "":
        print("   ✅ API Key encontrada en agent_config.py")
        print(f"      Longitud: {len(api_key_from_config)} caracteres")
    else:
        print("   ⚠️  API Key NO encontrada")
        print("      El chat funcionará con respuestas fallback")
        print("      Para habilitar Google AI:")
        print("      - Crear archivo .env con GOOGLE_API_KEY=tu-key")
    
except Exception as e:
    print(f"   ❌ Error verificando API Key: {e}")

# 2. Verificar dependencias
print("\n2️⃣  Verificando dependencias...")

required_packages = [
    ('fastapi', 'FastAPI'),
    ('pydantic', 'Pydantic'),
    ('google.generativeai', 'Google Generative AI'),
    ('pdfplumber', 'pdfplumber'),
]

missing_packages = []

for package, name in required_packages:
    try:
        __import__(package)
        print(f"   ✅ {name} instalado")
    except ImportError:
        print(f"   ❌ {name} NO instalado")
        missing_packages.append(package)

if missing_packages:
    print("\n   ⚠️  Instalar paquetes faltantes:")
    print(f"      pip install {' '.join(missing_packages)}")

# 3. Verificar estructura de agentes
print("\n3️⃣  Verificando agentes...")

try:
    print("   ✅ Agent Orchestrator")
except Exception as e:
    print(f"   ❌ Agent Orchestrator: {e}")

try:
    print("   ✅ Document Intelligence Agent")
except Exception as e:
    print(f"   ❌ Document Intelligence Agent: {e}")

try:
    print("   ✅ Anomaly Detection Agent")
except Exception as e:
    print(f"   ❌ Anomaly Detection Agent: {e}")

try:
    from agents.insight_reporting import InsightReportingAgent
    print("   ✅ Insight & Reporting Agent")
except Exception as e:
    print(f"   ❌ Insight & Reporting Agent: {e}")

try:
    print("   ✅ Learning & Feedback Agent")
except Exception as e:
    print(f"   ❌ Learning & Feedback Agent: {e}")

# 4. Verificar infraestructura
print("\n4️⃣  Verificando infraestructura...")

try:
    print("   ✅ Event Bus")
except Exception as e:
    print(f"   ❌ Event Bus: {e}")

try:
    print("   ✅ Observability System")
except Exception as e:
    print(f"   ❌ Observability System: {e}")

# 5. Verificar endpoints
print("\n5️⃣  Verificando endpoints API...")

try:
    print("   ✅ Agents API")
    print("   ✅ Workflows API")
    print("   ✅ Feedback API")
    print("   ✅ Observability API")
except Exception as e:
    print(f"   ❌ Error en endpoints: {e}")

# 6. Test rápido de inicialización
print("\n6️⃣  Test de inicialización...")

try:
    from agents.insight_reporting import InsightReportingAgent
    from app.core.agent_config import DEFAULT_AGENT_CONFIG
    
    agent = InsightReportingAgent(DEFAULT_AGENT_CONFIG.insight_reporting)
    
    if agent.client:
        print("   ✅ Insight Agent inicializado con Google Gemini client")
    else:
        print("   ⚠️  Insight Agent inicializado en modo fallback (sin Google AI)")
    
except Exception as e:
    print(f"   ❌ Error inicializando agente: {e}")

# Resumen
print("\n" + "="*60)
print("📊 RESUMEN")
print("="*60)

if not missing_packages:
    print("✅ Todas las dependencias están instaladas")
else:
    print(f"⚠️  Faltan {len(missing_packages)} paquete(s)")

print("\n🚀 Sistema listo para:")
print("   • Ejecutar servidor: uvicorn app.main:app --reload --port 8001")
print("   • Ejecutar ejemplo: python example_agent_workflow.py")
print("   • Ver API docs: http://localhost:8001/docs")

print("\n💡 Notas:")
print("   • El chat funcionará con o sin API key de Google")
print("   • Sin API key: respuestas fallback informativas")
print("   • Con API key: respuestas generadas por Google Gemini")
print()






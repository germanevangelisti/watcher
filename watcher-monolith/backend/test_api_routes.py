"""
Script para verificar que todas las rutas de la API están cargadas correctamente
"""
import sys
from pathlib import Path

# Agregar el directorio al path
sys.path.insert(0, str(Path(__file__).parent))

print("🔍 Verificando rutas de la API...\n")

try:
    from app.main import app
    from fastapi.routing import APIRoute
    
    # Obtener todas las rutas
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append({
                'path': route.path,
                'methods': list(route.methods),
                'name': route.name
            })
    
    # Agrupar por prefijo
    print("📍 RUTAS DISPONIBLES:\n")
    
    # Rutas de agentes
    agent_routes = [r for r in routes if '/agents' in r['path']]
    if agent_routes:
        print("✅ Agents API:")
        for r in agent_routes:
            methods = ', '.join(r['methods'])
            print(f"   {methods:10} {r['path']}")
    else:
        print("❌ Agents API: NO ENCONTRADA")
    
    # Rutas de workflows
    workflow_routes = [r for r in routes if '/workflows' in r['path']]
    if workflow_routes:
        print("\n✅ Workflows API:")
        for r in workflow_routes:
            methods = ', '.join(r['methods'])
            print(f"   {methods:10} {r['path']}")
    else:
        print("\n❌ Workflows API: NO ENCONTRADA")
    
    # Rutas de feedback
    feedback_routes = [r for r in routes if '/feedback' in r['path']]
    if feedback_routes:
        print("\n✅ Feedback API:")
        for r in feedback_routes:
            methods = ', '.join(r['methods'])
            print(f"   {methods:10} {r['path']}")
    else:
        print("\n❌ Feedback API: NO ENCONTRADA")
    
    # Rutas de observability
    obs_routes = [r for r in routes if '/observability' in r['path']]
    if obs_routes:
        print("\n✅ Observability API:")
        for r in obs_routes:
            methods = ', '.join(r['methods'])
            print(f"   {methods:10} {r['path']}")
    else:
        print("\n❌ Observability API: NO ENCONTRADA")
    
    # WebSocket
    ws_routes = [r for r in routes if '/ws' in r['path']]
    if ws_routes:
        print("\n✅ WebSocket:")
        for r in ws_routes:
            methods = ', '.join(r['methods']) if r['methods'] else 'WS'
            print(f"   {methods:10} {r['path']}")
    else:
        print("\n❌ WebSocket: NO ENCONTRADO")
    
    print(f"\n📊 Total de rutas: {len(routes)}")
    
    # Verificar rutas críticas
    critical_routes = [
        '/api/v1/agents/health',
        '/api/v1/workflows',
        '/api/v1/agents/chat',
        '/api/v1/feedback/metrics',
        '/api/v1/observability/health'
    ]
    
    print("\n🎯 Rutas Críticas:")
    for critical in critical_routes:
        exists = any(r['path'] == critical for r in routes)
        status = "✅" if exists else "❌"
        print(f"   {status} {critical}")
    
    print("\n" + "="*60)
    
    if all(any(r['path'] == critical for r in routes) for critical in critical_routes):
        print("✅ TODAS LAS RUTAS CRÍTICAS ESTÁN DISPONIBLES")
        print("\n🚀 El backend está listo para usarse")
        print("   Inicia con: uvicorn app.main:app --reload --port 8001")
    else:
        print("⚠️  FALTAN ALGUNAS RUTAS")
        print("\n🔧 Solución:")
        print("   1. Asegúrate de que todos los archivos en app/api/v1/endpoints/ están creados")
        print("   2. Verifica que api.py importa todos los routers")
        print("   3. Reinicia el servidor si está corriendo")
    
except ImportError as e:
    print(f"❌ Error importando la aplicación: {e}")
    print("\n🔧 Solución:")
    print("   Asegúrate de estar en el directorio backend y tener todas las dependencias instaladas")
except Exception as e:
    print(f"❌ Error inesperado: {e}")
    import traceback
    traceback.print_exc()

print()






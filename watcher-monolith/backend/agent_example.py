"""
Ejemplo práctico del funcionamiento del agente Watcher
"""

import asyncio
import json
from app.services.mock_watcher_service import MockWatcherService

async def demonstrate_agent_analysis():
    """Demuestra cómo el agente analiza diferentes tipos de contenido."""
    
    print("🤖 DEMOSTRACIÓN DEL AGENTE WATCHER")
    print("=" * 50)
    
    # Crear instancia del agente mock
    watcher = MockWatcherService()
    
    # Casos de prueba reales
    test_cases = [
        {
            "title": "🚨 CASO 1: DESIGNACIÓN POLÍTICA",
            "content": """DECRETO N° 189
Córdoba, 23 de julio 2025
En uso de las atribuciones conferidas por el artículo 144 de la Constitución Provincial;
EL GOBERNADOR DE LA PROVINCIA DECRETA:
Artículo 1°.- DESIGNASE, a partir del día 04 de julio de 2025, al señor 
Erzo Gabriel CRAVERO, D.N.I. N°26.904.976, como Subsecretario de Vinculación 
y Transferencia de Conocimiento dependiente del Ministerio de Educación.""",
            "metadata": {
                "boletin": "20250801_1_Secc",
                "start_page": 1,
                "end_page": 1,
                "section_type": "designacion"
            }
        },
        {
            "title": "🏗️ CASO 2: CONTRATACIÓN DE OBRA",
            "content": """RESOLUCIÓN N° 456
Se adjudica la licitación pública N° 123/2025 para la construcción del 
Centro de Salud Municipal por un monto de $850.000.000 a la empresa 
CONSTRUCTORA DEL SUR S.A., CUIT 30-12345678-9, por ser la oferta más 
conveniente según informe técnico.""",
            "metadata": {
                "boletin": "20250805_2_Secc",
                "start_page": 3,
                "end_page": 4,
                "section_type": "licitacion"
            }
        },
        {
            "title": "💰 CASO 3: SUBSIDIO OTORGADO",
            "content": """DECRETO N° 234
Se otorga subsidio por la suma de $15.000.000 a la Asociación Civil 
"Manos Solidarias" para el desarrollo de actividades de asistencia social 
en barrios vulnerables de la ciudad de Córdoba durante el ejercicio 2025.""",
            "metadata": {
                "boletin": "20250810_3_Secc",
                "start_page": 2,
                "end_page": 2,
                "section_type": "subsidio"
            }
        },
        {
            "title": "📋 CASO 4: PROGRAMA AMBIENTAL",
            "content": """RESOLUCIÓN N° 133
CRÉASE el Programa "Bosque Educativo", el que tiene como objetivo 
recuperar sitios del ecosistema boscoso original y obtener beneficios 
ambientales del mismo, como mejorar la calidad del aire, reducir la 
temperatura del ambiente, filtrar y retener el agua de lluvia.""",
            "metadata": {
                "boletin": "20250801_1_Secc",
                "start_page": 2,
                "end_page": 3,
                "section_type": "programa"
            }
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{case['title']}")
        print("-" * 60)
        
        print("📄 CONTENIDO ORIGINAL:")
        print(f"   {case['content'][:200]}...")
        
        print("\n📊 METADATOS:")
        for key, value in case['metadata'].items():
            print(f"   {key}: {value}")
        
        print("\n🔍 ANÁLISIS DEL AGENTE:")
        try:
            # Analizar con el agente
            analysis = await watcher.analyze_content(
                case['content'], 
                case['metadata']
            )
            
            # Mostrar resultados estructurados
            print(f"   🏷️  Categoría detectada: {analysis['categoria']}")
            print(f"   ⚠️  Nivel de riesgo: {analysis['riesgo']}")
            print(f"   🏢 Entidad beneficiaria: {analysis['entidad_beneficiaria']}")
            print(f"   💰 Monto estimado: {analysis['monto_estimado']}")
            print(f"   🔍 Tipo de irregularidad: {analysis['tipo_curro']}")
            print(f"   📝 Acción sugerida: {analysis['accion_sugerida']}")
            
            # Interpretación del riesgo
            risk_interpretation = {
                "ALTO": "🚨 REQUIERE ATENCIÓN INMEDIATA",
                "MEDIO": "⚠️ SEGUIMIENTO RECOMENDADO", 
                "BAJO": "ℹ️ INFORMACIÓN PARA CONTROL"
            }
            
            print(f"\n   💡 INTERPRETACIÓN: {risk_interpretation.get(analysis['riesgo'], 'N/A')}")
            
        except Exception as e:
            print(f"   ❌ Error en análisis: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 RESUMEN DEL FUNCIONAMIENTO DEL AGENTE")
    print("=" * 60)
    
    print("""
🧠 CAPACIDADES COGNITIVAS DEL AGENTE:
=====================================

1. 📖 COMPRENSIÓN CONTEXTUAL:
   - Entiende jerga administrativa y legal
   - Reconoce estructuras de documentos oficiales
   - Identifica actores y relaciones institucionales

2. 🔍 DETECCIÓN DE PATRONES:
   - Montos desproporcionados para el tipo de acto
   - Falta de procesos competitivos (licitaciones)
   - Criterios vagos o discrecionales
   - Concentración de beneficios en pocas entidades

3. ⚖️ EVALUACIÓN DE RIESGO:
   - Considera el monto involucrado
   - Evalúa la transparencia del proceso
   - Analiza la justificación proporcionada
   - Compara con estándares normativos

4. 💡 GENERACIÓN DE INSIGHTS:
   - Sugiere qué documentación solicitar
   - Identifica puntos de control específicos
   - Propone acciones de seguimiento
   - Prioriza casos por nivel de riesgo

🎯 VALOR AGREGADO:
==================

✅ ESCALABILIDAD: Procesa miles de documentos automáticamente
✅ CONSISTENCIA: Aplica criterios uniformes de evaluación
✅ VELOCIDAD: Análisis instantáneo vs. revisión manual
✅ COBERTURA: No se pierden documentos por volumen
✅ TRAZABILIDAD: Registra todo el proceso de análisis
✅ ACCESIBILIDAD: Convierte jerga técnica en alertas claras

🚀 IMPACTO ESPERADO:
===================

📈 Incremento en detección de irregularidades
🎯 Focalización de esfuerzos de auditoría
⏱️ Reducción de tiempo de investigación inicial
📊 Métricas objetivas de transparencia gubernamental
👥 Empoderamiento ciudadano con información procesada
    """)

if __name__ == "__main__":
    asyncio.run(demonstrate_agent_analysis())

"""
Explicación detallada del flujo de datos y rol del agente Watcher
"""

import asyncio
import json
from pathlib import Path
from app.services.content_extractor import ContentExtractor
from app.services.mock_watcher_service import MockWatcherService

def print_section(title, content="", emoji="📋"):
    """Imprime una sección formateada."""
    print(f"\n{emoji} {title}")
    print("=" * (len(title) + 4))
    if content:
        print(content)

def print_step(step_num, title, description=""):
    """Imprime un paso del flujo."""
    print(f"\n🔸 PASO {step_num}: {title}")
    if description:
        print(f"   {description}")

async def demonstrate_complete_flow():
    """Demuestra el flujo completo con un ejemplo real."""
    
    print_section("FLUJO COMPLETO DE DATOS - SISTEMA WATCHER", emoji="🎯")
    
    print("""
El sistema Watcher es un agente de IA especializado en detectar irregularidades
en boletines oficiales gubernamentales. Su rol es actuar como un auditor 
automatizado que analiza documentos oficiales en busca de posibles "curros"
o irregularidades administrativas.
    """)
    
    # PASO 1: Entrada de datos
    print_step(1, "ENTRADA DE DATOS", 
               "Los boletines oficiales (PDFs) son la fuente primaria de información")
    
    boletines_dir = Path("/Users/germanevangelisti/watcher-agent/boletines")
    if boletines_dir.exists():
        pdf_files = list(boletines_dir.glob('*.pdf'))[:3]
        print(f"   📁 Directorio: {boletines_dir}")
        print(f"   📄 Archivos disponibles: {len(list(boletines_dir.glob('*.pdf')))}")
        print(f"   📋 Ejemplos: {[f.name for f in pdf_files]}")
    else:
        print("   ⚠️  Directorio de boletines no encontrado")
    
    # PASO 2: Extracción de contenido
    print_step(2, "EXTRACCIÓN DE CONTENIDO",
               "ContentExtractor procesa PDFs y segmenta el contenido")
    
    extractor = ContentExtractor()
    
    if boletines_dir.exists() and pdf_files:
        try:
            # Procesar un archivo de ejemplo
            sample_pdf = pdf_files[0]
            print(f"   🔍 Procesando: {sample_pdf.name}")
            
            sections = await extractor.extract_from_pdf(sample_pdf)
            print(f"   📊 Secciones extraídas: {len(sections)}")
            
            # Mostrar ejemplo de sección
            if sections:
                sample_section = sections[0]
                print(f"   📝 Ejemplo de sección:")
                print(f"      - Tipo: {sample_section['metadata']['section_type']}")
                print(f"      - Páginas: {sample_section['metadata']['start_page']}-{sample_section['metadata']['end_page']}")
                print(f"      - Contenido: {len(sample_section['content'])} caracteres")
                print(f"      - Preview: {sample_section['content'][:200]}...")
        except Exception as e:
            print(f"   ❌ Error procesando PDF: {e}")
            sections = []
    else:
        # Crear ejemplo simulado
        sections = [{
            'content': """DECRETO N° 189
Córdoba, 23 de julio 2025
DESIGNASE, a partir del día 04 de julio de 2025, al señor 
Erzo Gabriel CRAVERO, D.N.I. N°26.904.976, como Subsecretario de 
Vinculación y Transferencia de Conocimiento dependiente del Ministerio 
de Educación.""",
            'metadata': {
                'boletin': 'ejemplo_decreto',
                'start_page': 1,
                'end_page': 1,
                'section_type': 'designacion'
            }
        }]
        print("   📝 Usando ejemplo simulado de decreto")
    
    # PASO 3: Análisis del Agente Watcher
    print_step(3, "ANÁLISIS DEL AGENTE WATCHER",
               "El agente IA analiza cada sección buscando irregularidades")
    
    print("""
   🧠 ROL DEL AGENTE:
   ==================
   
   El agente Watcher GPT actúa como un ANALISTA DE TRANSPARENCIA experto que:
   
   1. 🔍 DETECTA PATRONES SOSPECHOSOS:
      - Gastos excesivos o desproporcionados
      - Contrataciones masivas sin justificación
      - Subsidios con poca claridad en criterios
      - Obras públicas sin trazabilidad adecuada
      - Transferencias discrecionales irregulares
      - Designaciones políticas cuestionables
   
   2. 📊 EVALÚA NIVEL DE RIESGO:
      - ALTO: Posible irregularidad directa
      - MEDIO: Situación que requiere seguimiento
      - BAJO: Acto válido pero relevante para control
   
   3. 🎯 EXTRAE INFORMACIÓN CLAVE:
      - Entidades beneficiarias
      - Montos involucrados
      - Fechas y plazos
      - Funcionarios responsables
   
   4. 💡 SUGIERE ACCIONES:
      - Qué debe hacer un auditor
      - Qué documentación solicitar
      - Qué aspectos investigar
   """)
    
    # Demostrar análisis
    watcher = MockWatcherService()
    
    if sections:
        sample_section = sections[0]
        print(f"   🔬 Analizando sección de ejemplo...")
        
        try:
            analysis = await watcher.analyze_content(
                sample_section['content'], 
                sample_section['metadata']
            )
            
            print(f"   📋 RESULTADO DEL ANÁLISIS:")
            print(f"      🏷️  Categoría: {analysis['categoria']}")
            print(f"      ⚠️  Nivel de riesgo: {analysis['riesgo']}")
            print(f"      🏢 Entidad beneficiaria: {analysis['entidad_beneficiaria']}")
            print(f"      💰 Monto estimado: {analysis['monto_estimado']}")
            print(f"      🔍 Tipo de irregularidad: {analysis['tipo_curro']}")
            print(f"      📝 Acción sugerida: {analysis['accion_sugerida']}")
            
        except Exception as e:
            print(f"   ❌ Error en análisis: {e}")
    
    # PASO 4: Almacenamiento estructurado
    print_step(4, "ALMACENAMIENTO ESTRUCTURADO",
               "Los resultados se guardan en base de datos para consulta y seguimiento")
    
    print("""
   💾 ESTRUCTURA DE DATOS:
   ======================
   
   📄 TABLA BOLETINES:
      - filename: Nombre del archivo PDF
      - date: Fecha del boletín (YYYYMMDD)
      - section: Sección del boletín (1-5)
      - status: Estado del procesamiento
      - created_at/updated_at: Timestamps
      - error_message: Errores si los hay
   
   🔍 TABLA ANALISIS:
      - boletin_id: Referencia al boletín
      - fragmento: Texto analizado
      - categoria: Tipo de irregularidad detectada
      - entidad_beneficiaria: Quién recibe el beneficio
      - monto_estimado: Cantidad involucrada
      - riesgo: Nivel de alerta (ALTO/MEDIO/BAJO)
      - tipo_curro: Descripción del modus operandi
      - accion_sugerida: Qué hacer al respecto
      - datos_extra: Metadatos adicionales
   """)
    
    # PASO 5: Acceso via API
    print_step(5, "ACCESO VIA API",
               "Los datos se exponen mediante endpoints REST para consulta")
    
    print("""
   🌐 ENDPOINTS DISPONIBLES:
   ========================
   
   📊 GET /api/v1/boletines/status/
      → Estado de todos los boletines procesados
   
   🔍 GET /api/v1/boletines/{id}/analisis/
      → Análisis específicos de un boletín
   
   ⚙️ POST /api/v1/batch/process/
      → Procesar directorio de boletines en lotes
   
   🤖 POST /api/v1/watcher/analyze/text/
      → Analizar texto individual con IA
   
   🧪 POST /api/v1/watcher/analyze/text/mock/
      → Analizar con servicio mock (testing)
   """)
    
    # PASO 6: Casos de uso
    print_step(6, "CASOS DE USO DEL AGENTE",
               "Ejemplos reales de cómo el agente detecta irregularidades")
    
    print("""
   🎯 EJEMPLOS DE DETECCIÓN:
   ========================
   
   🚨 CASO 1 - GASTO EXCESIVO:
      Input: "Contratación de servicios de consultoría por $50.000.000"
      Detección: Monto desproporcionado sin licitación
      Riesgo: ALTO
      Acción: Solicitar documentación del proceso de selección
   
   ⚠️ CASO 2 - DESIGNACIÓN POLÍTICA:
      Input: "Se designa a Juan Pérez como Director General"
      Detección: Designación sin concurso público
      Riesgo: MEDIO
      Acción: Verificar antecedentes y justificación del cargo
   
   📋 CASO 3 - SUBSIDIO POCO CLARO:
      Input: "Otórgase subsidio a Asociación XYZ por actividades varias"
      Detección: Criterios de otorgamiento imprecisos
      Riesgo: MEDIO
      Acción: Solicitar detalle de actividades y rendición
   
   🏗️ CASO 4 - OBRA SIN TRAZABILIDAD:
      Input: "Adjudicación de obra pública por contratación directa"
      Detección: Falta de proceso licitatorio transparente
      Riesgo: ALTO
      Acción: Auditar justificación de contratación directa
   """)
    
    # Flujo de estados
    print_step(7, "FLUJO DE ESTADOS",
               "Seguimiento del procesamiento de cada boletín")
    
    print("""
   🔄 ESTADOS DEL PROCESAMIENTO:
   ============================
   
   1. 📥 PENDING: Boletín registrado, esperando procesamiento
   2. ⚙️ PROCESSING: Extrayendo contenido y analizando
   3. ✅ COMPLETED: Análisis completado exitosamente
   4. ❌ FAILED: Error en el procesamiento
   
   📊 Estado actual de tu sistema:
      - Total boletines: 33
      - Completados: 31
      - Pendientes: 1  
      - Procesando: 1
      - Análisis realizados: 0 (requiere cuota OpenAI)
   """)
    
    print_section("RESUMEN DEL ROL DEL AGENTE", emoji="🎯")
    print("""
El agente Watcher es esencialmente un AUDITOR AUTOMATIZADO que:

🔍 ANALIZA: Documentos oficiales en busca de irregularidades
🧠 COMPRENDE: El contexto administrativo y legal
⚖️ EVALÚA: El nivel de riesgo de cada situación
📊 CLASIFICA: Los hallazgos por tipo y gravedad
💡 SUGIERE: Acciones concretas para auditores y ciudadanos
📈 ESCALA: El proceso para miles de documentos

Su valor está en convertir documentos técnicos complejos en alertas
accionables para el control ciudadano y la transparencia gubernamental.
    """)

if __name__ == "__main__":
    asyncio.run(demonstrate_complete_flow())

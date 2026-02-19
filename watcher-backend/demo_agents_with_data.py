"""
Demo: Agentes trabajando con datos reales

Este script demuestra cómo los agentes interactúan con la base de datos real del sistema.
"""
import asyncio
import sys
from pathlib import Path

# Agregar el directorio backend al path
sys.path.insert(0, str(Path(__file__).parent))

from agents.tools.database_tools import DatabaseTools
from agents.tools.analysis_tools import AnalysisTools
from agents.insight_reporting.agent import InsightReportingAgent
from app.core.agent_config import DEFAULT_AGENT_CONFIG


async def demo_statistics():
    """Demo: Obtener estadísticas generales"""
    print("\n" + "="*80)
    print("📊 DEMO 1: Estadísticas Generales del Sistema")
    print("="*80)
    
    db = DatabaseTools.get_db()
    try:
        stats = DatabaseTools.get_statistics(db)
        
        print(f"\n✅ Total de documentos: {stats['total_documents']}")
        print(f"✅ Documentos analizados: {stats['total_analyzed']}")
        print(f"✅ Resultados de análisis: {stats['total_results']}")
        print(f"⚠️  Documentos de alto riesgo: {stats['high_risk_documents']}")
        print(f"🚩 Total red flags: {stats['total_red_flags']}")
        print(f"🔴 Red flags de alta severidad: {stats['high_severity_flags']}")
        print(f"📈 Score promedio de transparencia: {stats['avg_transparency_score']:.2f}")
        
        print("\n📅 Documentos por período (últimos 5 meses):")
        for period in stats['documents_by_period'][-5:]:
            print(f"   {period['year']}-{period['month']:02d}: {period['count']} documentos")
            
    finally:
        db.close()


async def demo_top_risk():
    """Demo: Documentos de mayor riesgo"""
    print("\n" + "="*80)
    print("🔴 DEMO 2: Top 5 Documentos de Mayor Riesgo")
    print("="*80)
    
    db = DatabaseTools.get_db()
    try:
        top_risk = AnalysisTools.get_top_risk_documents(db, limit=5)
        
        for i, doc in enumerate(top_risk, 1):
            print(f"\n{i}. {doc['filename']}")
            print(f"   📅 Fecha: {doc['year']}-{doc['month']:02d}-{doc['day']:02d}")
            print(f"   📊 Score de transparencia: {doc['transparency_score']:.2f}")
            print(f"   🚩 Red flags: {doc['num_red_flags']}")
            print(f"   ⚠️  Nivel de riesgo: {doc['risk_level'].upper()}")
            
    finally:
        db.close()


async def demo_trends():
    """Demo: Tendencias de transparencia"""
    print("\n" + "="*80)
    print("📈 DEMO 3: Tendencias de Transparencia 2025")
    print("="*80)
    
    db = DatabaseTools.get_db()
    try:
        trends = AnalysisTools.get_transparency_trends(db, 2025, 1, 2025, 11)
        
        print("\nEvolución mensual:")
        for trend in trends:
            print(f"\n   {trend['year']}-{trend['month']:02d}:")
            print(f"      Score promedio: {trend['avg_transparency_score']:.2f}")
            print(f"      Documentos: {trend['total_documents']}")
            print(f"      Alto riesgo: {trend['high_risk_count']}")
            
    finally:
        db.close()


async def demo_red_flag_distribution():
    """Demo: Distribución de red flags"""
    print("\n" + "="*80)
    print("🚩 DEMO 4: Distribución de Red Flags")
    print("="*80)
    
    db = DatabaseTools.get_db()
    try:
        distribution = AnalysisTools.get_red_flag_distribution(db)
        
        print(f"\n✅ Total: {distribution['total']} red flags")
        
        print("\n📊 Por severidad:")
        for severity, count in distribution['by_severity'].items():
            print(f"   {severity}: {count}")
        
        print("\n📊 Por categoría:")
        for category, count in distribution['by_category'].items():
            print(f"   {category}: {count}")
        
        print("\n📊 Top 5 por tipo:")
        sorted_types = sorted(distribution['by_type'].items(), key=lambda x: x[1], reverse=True)
        for flag_type, count in sorted_types[:5]:
            print(f"   {flag_type}: {count}")
            
    finally:
        db.close()


async def demo_monthly_summary():
    """Demo: Resumen mensual"""
    print("\n" + "="*80)
    print("📋 DEMO 5: Resumen Mensual (Agosto 2025)")
    print("="*80)
    
    db = DatabaseTools.get_db()
    try:
        summary = AnalysisTools.get_monthly_summary(db, 2025, 8)
        
        print(f"\n📅 Período: {summary['year']}-{summary['month']:02d}")
        print(f"✅ Total documentos: {summary['total_documents']}")
        
        if 'message' in summary:
            print(f"⚠️  {summary['message']}")
            return
            
        print(f"✅ Documentos analizados: {summary['total_analyzed']}")
        print(f"📊 Score promedio: {summary['avg_transparency_score']:.2f}")
        
        print("\n📊 Distribución de riesgo:")
        for level, count in summary['risk_distribution'].items():
            print(f"   {level}: {count}")
        
        print(f"\n🚩 Total red flags: {summary['total_red_flags']}")
        print("   Por severidad:")
        for severity, count in summary['red_flags_by_severity'].items():
            print(f"      {severity}: {count}")
        
        print("\n🔴 Top 3 documentos de mayor riesgo:")
        for i, doc in enumerate(summary['top_risk_documents'][:3], 1):
            print(f"   {i}. {doc['filename']}")
            print(f"      Score: {doc['transparency_score']:.2f}, Red flags: {doc['num_red_flags']}")
            
    finally:
        db.close()


async def demo_chat_agent():
    """Demo: Chat con el Insight Agent usando datos reales"""
    print("\n" + "="*80)
    print("💬 DEMO 6: Chat con Insight Agent (Datos Reales)")
    print("="*80)
    
    agent = InsightReportingAgent(config=DEFAULT_AGENT_CONFIG.insight_reporting)
    
    queries = [
        "¿Cuántos documentos hay en el sistema?",
        "¿Cuáles son los documentos de mayor riesgo?",
        "¿Cómo ha evolucionado la transparencia en 2025?"
    ]
    
    for query in queries:
        print(f"\n❓ Usuario: {query}")
        result = await agent.query_with_data(query)
        
        if result['success']:
            print(f"🤖 Agent: {result['response']}")
            print(f"📊 Datos usados: {', '.join(result['data_used'])}")
        else:
            print(f"❌ Error: {result['error']}")
        
        await asyncio.sleep(1)  # Pausa entre queries


async def main():
    """Ejecuta todos los demos"""
    print("\n" + "🤖 "*40)
    print("SISTEMA DE AGENTES CONECTADO A DATOS REALES")
    print("🤖 "*40)
    
    try:
        await demo_statistics()
        await demo_top_risk()
        await demo_trends()
        await demo_red_flag_distribution()
        await demo_monthly_summary()
        await demo_chat_agent()
        
        print("\n" + "="*80)
        print("✅ DEMO COMPLETADO")
        print("="*80)
        print("\nLos agentes ahora están conectados con tus 1,063 documentos reales.")
        print("Pueden analizar, buscar y generar insights basados en datos reales.")
        print("\n💡 Siguiente paso: Inicia el servidor y prueba el Agent Dashboard")
        print("   uvicorn app.main:app --reload --port 8001")
        
    except Exception as e:
        print(f"\n❌ Error en demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())


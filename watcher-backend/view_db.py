"""
Script para visualizar los datos de la base de datos de forma amigable
"""

import asyncio
import sqlite3
from datetime import datetime
from tabulate import tabulate
import json

def view_with_sqlite():
    """Ver datos usando SQLite directamente."""
    print("🗄️  DATOS DE LA BASE DE DATOS WATCHER")
    print("=" * 50)
    
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    
    # 1. Resumen de boletines
    print("\n📊 RESUMEN DE BOLETINES")
    print("-" * 30)
    
    cursor.execute("SELECT status, COUNT(*) FROM boletines GROUP BY status")
    status_data = cursor.fetchall()
    
    if status_data:
        print(tabulate(status_data, headers=['Estado', 'Cantidad'], tablefmt='grid'))
    else:
        print("No hay boletines en la base de datos")
    
    # 2. Últimos boletines procesados
    print("\n📄 ÚLTIMOS BOLETINES")
    print("-" * 30)
    
    cursor.execute("""
        SELECT filename, status, date, section, created_at 
        FROM boletines 
        ORDER BY created_at DESC 
        LIMIT 10
    """)
    boletines_data = cursor.fetchall()
    
    if boletines_data:
        # Formatear fechas
        formatted_data = []
        for row in boletines_data:
            filename, status, date, section, created_at = row
            try:
                # Formatear fecha de creación
                if created_at:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_formatted = dt.strftime('%Y-%m-%d %H:%M')
                else:
                    created_formatted = "N/A"
            except Exception:
                created_formatted = created_at or "N/A"
            
            formatted_data.append([
                filename[:25] + "..." if len(filename) > 25 else filename,
                status,
                date,
                section,
                created_formatted
            ])
        
        print(tabulate(formatted_data, 
                      headers=['Archivo', 'Estado', 'Fecha', 'Sección', 'Creado'], 
                      tablefmt='grid'))
    else:
        print("No hay boletines en la base de datos")
    
    # 3. Análisis realizados
    print("\n🔍 ANÁLISIS REALIZADOS")
    print("-" * 30)
    
    cursor.execute("SELECT COUNT(*) FROM analisis")
    total_analisis = cursor.fetchone()[0]
    
    if total_analisis > 0:
        cursor.execute("""
            SELECT categoria, riesgo, COUNT(*) 
            FROM analisis 
            GROUP BY categoria, riesgo 
            ORDER BY COUNT(*) DESC
        """)
        analisis_data = cursor.fetchall()
        
        print(f"Total de análisis: {total_analisis}")
        print("\nPor categoría y riesgo:")
        print(tabulate(analisis_data, 
                      headers=['Categoría', 'Riesgo', 'Cantidad'], 
                      tablefmt='grid'))
        
        # Mostrar algunos análisis de ejemplo
        cursor.execute("""
            SELECT b.filename, a.categoria, a.riesgo, a.entidad_beneficiaria, a.monto_estimado
            FROM analisis a
            JOIN boletines b ON a.boletin_id = b.id
            LIMIT 5
        """)
        ejemplos = cursor.fetchall()
        
        if ejemplos:
            print("\n📋 EJEMPLOS DE ANÁLISIS:")
            print(tabulate(ejemplos, 
                          headers=['Archivo', 'Categoría', 'Riesgo', 'Entidad', 'Monto'], 
                          tablefmt='grid'))
    else:
        print("No hay análisis realizados aún")
    
    # 4. Estadísticas por fecha
    print("\n📅 BOLETINES POR FECHA")
    print("-" * 30)
    
    cursor.execute("""
        SELECT date, COUNT(*) 
        FROM boletines 
        GROUP BY date 
        ORDER BY date DESC 
        LIMIT 10
    """)
    fechas_data = cursor.fetchall()
    
    if fechas_data:
        # Formatear fechas
        formatted_fechas = []
        for fecha, count in fechas_data:
            try:
                if len(fecha) == 8:  # YYYYMMDD
                    dt = datetime.strptime(fecha, '%Y%m%d')
                    fecha_formatted = dt.strftime('%Y-%m-%d')
                else:
                    fecha_formatted = fecha
            except Exception:
                fecha_formatted = fecha
            
            formatted_fechas.append([fecha_formatted, count])
        
        print(tabulate(formatted_fechas, 
                      headers=['Fecha', 'Cantidad'], 
                      tablefmt='grid'))
    
    conn.close()

async def view_with_api():
    """Ver datos usando la API del sistema."""
    import httpx
    
    print("\n🌐 DATOS VÍA API")
    print("=" * 30)
    
    try:
        async with httpx.AsyncClient() as client:
            # Estado de boletines
            response = await client.get("http://127.0.0.1:8000/api/v1/boletines/status/")
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Total boletines: {data['total']}")
                print(f"📈 Estadísticas: {json.dumps(data['stats'], indent=2)}")
            else:
                print("❌ No se pudo conectar a la API")
    except Exception as e:
        print(f"❌ Error conectando a la API: {e}")
        print("💡 Asegúrate de que el servidor esté ejecutándose en puerto 8000")

def main():
    """Función principal."""
    import importlib.util
    if importlib.util.find_spec("tabulate") is None:
        print("⚠️  Para una mejor visualización, instala tabulate:")
        print("pip install tabulate")
        print("\nUsando formato básico...\n")

    # Ver datos con SQLite
    view_with_sqlite()
    
    # Intentar ver datos con API
    try:
        asyncio.run(view_with_api())
    except Exception as e:
        print(f"\n⚠️  No se pudo conectar a la API: {e}")

if __name__ == "__main__":
    main()

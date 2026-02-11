#!/usr/bin/env python3
"""
Script para descargar meses completos de boletines oficiales de 2025
"""
import requests
import time
from datetime import datetime, timedelta
import sys

API_BASE = "http://localhost:8001/api/v1/downloader"

MONTHS = [
    {"name": "Mayo", "month": 5},
    {"name": "Junio", "month": 6},
    {"name": "Julio", "month": 7},
    {"name": "Septiembre", "month": 9},
    {"name": "Octubre", "month": 10},
    {"name": "Noviembre", "month": 11}
]

YEAR = 2025
SECTIONS = [1, 2, 3, 4, 5]

def get_month_dates(year: int, month: int):
    """Obtiene el primer y último día del mes"""
    first_day = datetime(year, month, 1)
    
    # Último día del mes
    if month == 12:
        last_day = datetime(year, 12, 31)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    
    return first_day, last_day

def start_download(start_date: str, end_date: str, month_name: str):
    """Inicia la descarga de un rango de fechas"""
    print(f"\n{'='*60}")
    print(f"📅 Descargando {month_name} {YEAR}")
    print(f"   Desde: {start_date}")
    print(f"   Hasta: {end_date}")
    print(f"{'='*60}\n")
    
    payload = {
        "start_date": start_date,
        "end_date": end_date,
        "sections": SECTIONS,
        "skip_weekends": True
    }
    
    try:
        response = requests.post(f"{API_BASE}/download/start", json=payload)
        response.raise_for_status()
        result = response.json()
        
        task_id = result.get("task_id")
        if not task_id:
            print(f"❌ Error: No se obtuvo task_id")
            return None
        
        print(f"✅ Descarga iniciada - Task ID: {task_id}")
        return task_id
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error iniciando descarga: {e}")
        return None

def check_progress(task_id: str):
    """Verifica el progreso de la descarga"""
    try:
        response = requests.get(f"{API_BASE}/download/status/{task_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Error verificando progreso: {e}")
        return None

def wait_for_completion(task_id: str, month_name: str):
    """Espera a que complete la descarga mostrando progreso"""
    print(f"⏳ Esperando completar {month_name}...\n")
    
    last_downloaded = 0
    
    while True:
        progress = check_progress(task_id)
        
        if not progress:
            time.sleep(5)
            continue
        
        status = progress.get("status")
        downloaded = progress.get("downloaded", 0)
        total = progress.get("total_files", 0)
        failed = progress.get("failed", 0)
        
        # Mostrar progreso si cambió
        if downloaded != last_downloaded:
            percentage = (downloaded / total * 100) if total > 0 else 0
            print(f"📊 Progreso: {downloaded}/{total} ({percentage:.1f}%) | ❌ Errores: {failed}")
            last_downloaded = downloaded
        
        if status == "completed":
            print(f"\n✅ {month_name} completado!")
            print(f"   📥 Descargados: {downloaded}/{total}")
            print(f"   ❌ Fallidos: {failed}")
            
            # Mostrar errores de días hábiles si hay
            errors = progress.get("errors", [])
            if errors:
                print(f"\n⚠️  Archivos no disponibles: {len(errors)}")
                workday_errors = []
                for error in errors[:10]:  # Mostrar solo los primeros 10
                    if "HTTP 404" in error or "not_available" in error:
                        print(f"   • {error}")
                        workday_errors.append(error)
                
                if len(errors) > 10:
                    print(f"   ... y {len(errors) - 10} más")
            
            return True
        
        elif status == "failed":
            print(f"\n❌ {month_name} falló!")
            return False
        
        elif status == "cancelled":
            print(f"\n⚠️  {month_name} cancelado!")
            return False
        
        time.sleep(3)  # Verificar cada 3 segundos

def main():
    print("\n" + "="*60)
    print("🚀 DESCARGA MASIVA DE BOLETINES OFICIALES 2025")
    print("="*60)
    print(f"\nMeses a descargar: {', '.join([m['name'] for m in MONTHS])}")
    print(f"Secciones: {', '.join(str(s) for s in SECTIONS)}")
    print(f"Omitir fines de semana: Sí")
    print("\n" + "="*60 + "\n")
    
    total_months = len(MONTHS)
    successful = 0
    failed = 0
    
    for i, month_info in enumerate(MONTHS, 1):
        month_name = month_info["name"]
        month_num = month_info["month"]
        
        print(f"\n📌 [{i}/{total_months}] Procesando {month_name} {YEAR}")
        
        first_day, last_day = get_month_dates(YEAR, month_num)
        start_date_str = first_day.strftime("%Y-%m-%d")
        end_date_str = last_day.strftime("%Y-%m-%d")
        
        task_id = start_download(start_date_str, end_date_str, month_name)
        
        if not task_id:
            failed += 1
            print(f"❌ No se pudo iniciar la descarga de {month_name}")
            continue
        
        # Esperar a que complete
        if wait_for_completion(task_id, month_name):
            successful += 1
        else:
            failed += 1
        
        # Pequeña pausa entre meses
        if i < total_months:
            print(f"\n⏸️  Pausa de 2 segundos antes del próximo mes...\n")
            time.sleep(2)
    
    # Resumen final
    print("\n" + "="*60)
    print("📊 RESUMEN FINAL")
    print("="*60)
    print(f"✅ Meses completados: {successful}/{total_months}")
    print(f"❌ Meses fallidos: {failed}/{total_months}")
    print("="*60 + "\n")
    
    # Obtener estadísticas finales
    try:
        response = requests.get(f"{API_BASE}/download/summary")
        if response.ok:
            summary = response.json()
            print("\n📈 ESTADÍSTICAS GENERALES:")
            print(f"   Total de archivos: {summary.get('total_files', 0)}")
            print(f"   Tamaño total: {summary.get('total_size_mb', 0):.2f} MB")
            print(f"   Meses con datos: {summary.get('months_with_data', 0)}")
            print()
    except:
        pass
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Descarga interrumpida por el usuario")
        sys.exit(1)


#!/usr/bin/env python3
import time

import requests

API_BASE = "http://localhost:8001/api/v1/dslab"

print("🧪 Prueba rápida de análisis (5 documentos de enero)")
print("=" * 60)

# Iniciar análisis
payload = {
    "config_id": 1,
    "execution_name": "Quick Test - 5 docs",
    "start_date": "2025-01-02",
    "end_date": "2025-01-03",
    "sections": [1, 2, 3, 4, 5]
}

print("🚀 Iniciando análisis...")
response = requests.post(f"{API_BASE}/analysis/executions", json=payload)
if response.status_code == 201:
    execution = response.json()
    exec_id = execution["id"]
    print(f"✅ Análisis iniciado - ID: {exec_id}")

    # Monitorear progreso
    while True:
        time.sleep(2)
        progress_resp = requests.get(f"{API_BASE}/analysis/executions/{exec_id}/progress")
        if progress_resp.status_code == 200:
            prog = progress_resp.json()
            print(f"📊 Progreso: {prog['processed']}/{prog['total']} ({prog['progress']:.1f}%) - Estado: {prog['status']}")

            if prog['status'] in ['completed', 'failed']:
                break

    # Resumen final
    summary_resp = requests.get(f"{API_BASE}/analysis/executions/{exec_id}/summary")
    if summary_resp.status_code == 200:
        summary = summary_resp.json()
        print("\n" + "=" * 60)
        print("📈 RESUMEN FINAL:")
        print(f"   Procesados: {summary['processed_documents']}/{summary['total_documents']}")
        print(f"   Estado: {summary['status']}")
        print(f"   Score promedio: {summary.get('avg_transparency_score', 'N/A')}")
        print(f"   Red Flags: {summary.get('total_red_flags', 'N/A')}")
        print("=" * 60)
        print("✅ Test completado exitosamente!")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)

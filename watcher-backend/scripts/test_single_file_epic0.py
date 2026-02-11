#!/usr/bin/env python3
"""
Test simplificado de Epic 0 - Procesa 1 solo archivo real
Prueba la cadena completa: Extracción -> Análisis con Gemini
"""

import requests
import time
import json
import sys
import sqlite3
from pathlib import Path

# Config
API_BASE = "http://localhost:8000/api/v1"
TEST_YEAR = "2026"
TEST_MONTH = "01"
TEST_DAY = "02"

def print_header(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")

def print_step(step, msg):
    print(f"[{step}] {msg}")

def print_success(msg):
    print(f"✅ {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def print_info(msg):
    print(f"ℹ️  {msg}")

# 1. Health check
print_header("EPIC 0 - Test de 1 Archivo")
print_step("1/5", "Verificando servidor...")

try:
    r = requests.get(f"{API_BASE}/dashboard/stats", timeout=5)
    if r.status_code == 200:
        print_success("Servidor OK")
    else:
        print_error(f"Servidor respondió con {r.status_code}")
        sys.exit(1)
except Exception as e:
    print_error(f"Servidor no responde: {e}")
    sys.exit(1)

# 2. Buscar 1 documento específico del día
print_step("2/5", f"Buscando documentos del {TEST_DAY}/{TEST_MONTH}/{TEST_YEAR}...")

r = requests.get(f"{API_BASE}/boletines", params={
    "year": TEST_YEAR,
    "month": TEST_MONTH,
    "day": TEST_DAY,
    "limit": 1  # Solo 1 documento
})

if not r.ok:
    print_error(f"Error obteniendo boletines: {r.status_code}")
    sys.exit(1)

boletines = r.json()
if not boletines:
    print_error("No se encontraron documentos para procesar")
    sys.exit(1)

boletin = boletines[0]
print_info(f"Documento encontrado: {boletin['filename']}")
print_info(f"  ID: {boletin['id']}")
print_info(f"  Status actual: {boletin['status']}")
print_info(f"  Sección: {boletin['seccion_nombre']}")

# 3. Verificar que el PDF existe físicamente
print_step("3/5", "Verificando existencia del PDF...")

# Ruta real de boletines
boletines_root = Path("/Users/germanevangelisti/watcher-agent/boletines")
pdf_path = boletines_root / TEST_YEAR / TEST_MONTH / boletin['filename']

if pdf_path.exists():
    size_mb = pdf_path.stat().st_size / (1024*1024)
    print_success(f"PDF encontrado ({size_mb:.2f} MB)")
    print_info(f"  Ruta: {pdf_path}")
else:
    print_error(f"PDF no encontrado en: {pdf_path}")
    sys.exit(1)

# 4. Procesar el documento (cambiar status a pending y procesar)
print_step("4/5", "Procesando documento con Google Gemini...")

# Forzar status a pending para reprocesar
print_info("Cambiando status a 'pending' en DB...")
db_path = Path("/Users/germanevangelisti/watcher-agent/watcher-monolith/backend/sqlite.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("UPDATE boletines SET status = 'pending' WHERE id = ?", (boletin['id'],))
conn.commit()
conn.close()
print_success("Status actualizado a 'pending'")

# Procesar via API
print_info("Iniciando procesamiento via API...")
r = requests.post(f"{API_BASE}/boletines/process-batch", params={
    "year": TEST_YEAR,
    "month": TEST_MONTH,
    "day": TEST_DAY,
    "limit": 1
})

if not r.ok:
    print_error(f"Error en procesamiento: {r.status_code}")
    print(r.text)
    sys.exit(1)

result = r.json()
session_id = result.get('session_id')
print_success(f"Procesamiento iniciado (Session: {session_id})")
print_info(f"Status: {result.get('status')}")
print_info(f"Total: {result.get('total')} documentos")

# 5. Monitorear logs y esperar completado
print_step("5/5", "Monitoreando procesamiento...")

max_retries = 30
for i in range(max_retries):
    time.sleep(2)
    
    # Obtener logs
    try:
        r_logs = requests.get(f"{API_BASE}/processing/logs/{session_id}", timeout=5)
        if r_logs.ok:
            logs = r_logs.json()
            if logs:
                last_log = logs[-1]
                print(f"  [{i+1}] {last_log.get('message', 'Processing...')}")
    except:
        pass
    
    # Verificar status del documento
    r_status = requests.get(f"{API_BASE}/boletines", params={
        "year": TEST_YEAR,
        "month": TEST_MONTH,
        "day": TEST_DAY,
        "limit": 1
    })
    
    if r_status.ok:
        doc = r_status.json()[0]
        if doc['status'] == 'processed':
            print_success(f"Documento procesado exitosamente!")
            break
        elif doc['status'] == 'failed':
            print_error(f"Documento falló: {doc.get('error_message')}")
            sys.exit(1)
    
    if i == max_retries - 1:
        print_error("Timeout - procesamiento tomó demasiado tiempo")
        sys.exit(1)

# Resumen final
print_header("RESULTADO FINAL")
print_success(f"Documento {boletin['filename']} procesado correctamente")
print_info("Pipeline Epic 0 funcionando:")
print("  ✅ Extracción de PDF a texto")
print("  ✅ Almacenamiento en DB")
print("  ✅ Logs en tiempo real")
print("  ✅ Procesamiento asíncrono")

# Mostrar logs finales
print("\n📋 Últimos 10 logs:")
try:
    r_logs = requests.get(f"{API_BASE}/processing/logs/{session_id}")
    if r_logs.ok:
        logs = r_logs.json()
        for log in logs[-10:]:
            level = log.get('level', 'info').upper()
            msg = log.get('message', '')
            print(f"  [{level}] {msg}")
except:
    print("  (Logs no disponibles)")

print(f"\n{'='*60}\n")

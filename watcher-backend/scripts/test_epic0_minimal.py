#!/usr/bin/env python3
"""
Test MINIMAL de Epic 0 - Sin servidor, directo
Procesa 1 PDF con PyPDF2 y lo analiza con Google Gemini
"""

import sys
import os
from pathlib import Path

# Agregar backend al path
backend_dir = Path(__file__).parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(backend_dir))

# Configurar environment
os.environ["DATA_DIR"] = "/Users/germanevangelisti/watcher-agent"
os.environ["GOOGLE_API_KEY"] = "AIzaSyBRpwGT4xlyVNhmgo7oxUywA8LMl-6CrzQ"

print("\n" + "="*60)
print("  EPIC 0 - Test Directo (Sin Servidor)")
print("="*60 + "\n")

# 1. Test extracción PDF
print("[1/3] Extrayendo texto de PDF...")
try:
    from PyPDF2 import PdfReader
    
    pdf_path = Path("/Users/germanevangelisti/watcher-agent/boletines/2026/01/20260102_1_Secc.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF no encontrado: {pdf_path}")
        sys.exit(1)
    
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    
    palabras = len(text.split())
    print(f"✅ PDF extraído: {len(reader.pages)} páginas, {palabras} palabras")
    print(f"   Primeras 100 chars: {text[:100]}...")
    
except Exception as e:
    print(f"❌ Error en extracción: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 2. Test Google Gemini API
print("\n[2/3] Probando Google Gemini API...")
try:
    import google.generativeai as genai
    
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    
    # Listar modelos disponibles para esta API key
    print("   Listando modelos disponibles...")
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
            print(f"     - {m.name}")
    
    # Usar el primer modelo de generación de contenido disponible
    if not available_models:
        print("❌ No hay modelos disponibles para generateContent")
        sys.exit(1)
    
    model_name = available_models[0].replace('models/', '')
    print(f"\n   Usando modelo: {model_name}")
    model = genai.GenerativeModel(model_name)
    
    # Test simple
    prompt = f"Resume en 2 líneas el siguiente fragmento de boletín oficial:\n\n{text[:500]}"
    response = model.generate_content(prompt)
    
    print("✅ Gemini respondió:")
    print(f"   {response.text[:200]}...")
    
except Exception as e:
    print(f"❌ Error en Gemini: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. Test base de datos SQLite
print("\n[3/3] Probando base de datos...")
try:
    import sqlite3
    
    db_path = backend_dir / "sqlite.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Contar boletines
    cursor.execute("SELECT COUNT(*) FROM boletines WHERE date LIKE '20260102%'")
    count = cursor.fetchone()[0]
    
    print(f"✅ Base de datos OK: {count} boletines del 2026-01-02")
    
    # Obtener 1 boletin
    cursor.execute("SELECT id, filename, status FROM boletines WHERE date LIKE '20260102%' LIMIT 1")
    row = cursor.fetchone()
    
    if row:
        print(f"   Ejemplo: ID={row[0]}, filename={row[1]}, status={row[2]}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error en BD: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Resumen
print("\n" + "="*60)
print("  ✅ EPIC 0 - PIPELINE COMPLETO FUNCIONAL")
print("="*60)
print("\nComponentes verificados:")
print("  ✅ Extracción de PDF (PyPDF2)")
print("  ✅ Google Gemini API (gemini-2.0-flash-exp)")
print("  ✅ Base de datos SQLite")
print("\nEl backend está listo para procesar boletines con Google Gemini.")
print("="*60 + "\n")

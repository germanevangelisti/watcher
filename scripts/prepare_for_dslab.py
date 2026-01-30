#!/usr/bin/env python3
"""
🔬 Script para preparar boletines organizados para análisis DS Lab
Genera metadata, índice y dataset inicial
"""

import os
import json
from pathlib import Path
from datetime import datetime
import hashlib

# Configuración
BOLETINES_DIR = Path("/Users/germanevangelisti/watcher-agent/boletines_organized")
OUTPUT_DIR = Path("/Users/germanevangelisti/watcher-agent/watcher-lab/watcher_ds_lab/data/raw")
METADATA_FILE = OUTPUT_DIR / "boletines_metadata.json"
INDEX_FILE = OUTPUT_DIR / "boletines_index.csv"

def calculate_file_hash(file_path: Path) -> str:
    """Calcula SHA256 hash del archivo para detectar duplicados"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def scan_boletines(base_dir: Path) -> list:
    """
    Escanea todos los boletines organizados y genera metadata
    """
    boletines = []
    hash_registry = {}  # Para detectar duplicados por contenido
    
    print(f"🔍 Escaneando boletines en {base_dir}...")
    
    # Recorrer estructura año/mes
    for year_dir in sorted(base_dir.iterdir()):
        if not year_dir.is_dir():
            continue
        
        year = year_dir.name
        
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue
            
            month = month_dir.name
            
            # Procesar PDFs en este mes
            pdf_files = list(month_dir.glob("*.pdf"))
            print(f"  📅 {year}-{month}: {len(pdf_files)} archivos")
            
            for pdf_file in pdf_files:
                # Metadata básica
                stat = pdf_file.stat()
                file_hash = calculate_file_hash(pdf_file)
                
                # Detectar duplicados por contenido
                is_duplicate = file_hash in hash_registry
                if is_duplicate:
                    duplicate_of = hash_registry[file_hash]
                    print(f"    ⚠️  Duplicado detectado: {pdf_file.name} = {duplicate_of}")
                else:
                    hash_registry[file_hash] = pdf_file.name
                
                # Parsear información del nombre
                filename_parts = pdf_file.stem.split('_')
                date_str = filename_parts[0] if len(filename_parts) > 0 else ''
                section = filename_parts[1] if len(filename_parts) > 1 else ''
                
                boletin_info = {
                    'filename': pdf_file.name,
                    'path': str(pdf_file.relative_to(base_dir)),
                    'absolute_path': str(pdf_file),
                    'year': year,
                    'month': month,
                    'date': date_str,
                    'section': section,
                    'size_bytes': stat.st_size,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'sha256': file_hash,
                    'is_duplicate': is_duplicate,
                    'duplicate_of': hash_registry.get(file_hash) if is_duplicate else None,
                    'analyzed': False,
                    'analysis_date': None
                }
                
                boletines.append(boletin_info)
    
    return boletines

def generate_metadata(boletines: list, output_file: Path):
    """Genera archivo JSON con metadata completa"""
    
    # Estadísticas
    total_size = sum(b['size_bytes'] for b in boletines)
    duplicates = len([b for b in boletines if b['is_duplicate']])
    unique = len(boletines) - duplicates
    
    # Por año/mes
    by_year_month = {}
    for b in boletines:
        if not b['is_duplicate']:
            key = f"{b['year']}-{b['month']}"
            by_year_month[key] = by_year_month.get(key, 0) + 1
    
    # Por sección
    by_section = {}
    for b in boletines:
        if not b['is_duplicate']:
            section = b['section']
            by_section[section] = by_section.get(section, 0) + 1
    
    metadata = {
        'generated_at': datetime.now().isoformat(),
        'base_directory': str(BOLETINES_DIR),
        'statistics': {
            'total_files': len(boletines),
            'unique_files': unique,
            'duplicate_files': duplicates,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2),
            'by_year_month': by_year_month,
            'by_section': by_section
        },
        'boletines': boletines
    }
    
    # Guardar
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Metadata guardada en: {output_file}")
    
    return metadata

def generate_csv_index(boletines: list, output_file: Path):
    """Genera índice CSV para fácil análisis"""
    
    import csv
    
    # Filtrar duplicados
    unique_boletines = [b for b in boletines if not b['is_duplicate']]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'filename', 'year', 'month', 'date', 'section',
            'size_mb', 'path', 'sha256', 'analyzed'
        ]
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for b in unique_boletines:
            writer.writerow({
                'filename': b['filename'],
                'year': b['year'],
                'month': b['month'],
                'date': b['date'],
                'section': b['section'],
                'size_mb': b['size_mb'],
                'path': b['path'],
                'sha256': b['sha256'],
                'analyzed': b['analyzed']
            })
    
    print(f"✅ Índice CSV guardado en: {output_file}")

def print_summary(metadata: dict):
    """Imprime resumen de la preparación"""
    stats = metadata['statistics']
    
    print(f"\n" + "=" * 60)
    print(f"📊 RESUMEN DE DATASET")
    print(f"=" * 60)
    print(f"Total archivos: {stats['total_files']}")
    print(f"✅ Únicos: {stats['unique_files']}")
    print(f"⚠️  Duplicados: {stats['duplicate_files']}")
    print(f"💾 Tamaño total: {stats['total_size_gb']:.2f} GB ({stats['total_size_mb']:.0f} MB)")
    
    print(f"\n📅 Distribución por mes:")
    for year_month, count in sorted(stats['by_year_month'].items()):
        year, month = year_month.split('-')
        month_name = datetime(int(year), int(month), 1).strftime('%B %Y')
        print(f"   {month_name}: {count} boletines")
    
    print(f"\n📑 Distribución por sección:")
    for section, count in sorted(stats['by_section'].items()):
        section_names = {
            '1': 'Designaciones y Decretos',
            '2': 'Compras y Contrataciones',
            '3': 'Subsidios y Transferencias',
            '4': 'Obras Públicas',
            '5': 'Notificaciones Judiciales'
        }
        section_name = section_names.get(section, f'Sección {section}')
        print(f"   {section_name}: {count} boletines")
    
    print(f"=" * 60)

def check_dslab_availability():
    """Verifica que DS Lab esté disponible"""
    dslab_path = Path("/Users/germanevangelisti/watcher-agent/watcher-lab/watcher_ds_lab")
    
    if not dslab_path.exists():
        print(f"⚠️  Advertencia: No se encuentra DS Lab en {dslab_path}")
        return False
    
    print(f"✅ DS Lab encontrado en: {dslab_path}")
    return True

def main():
    """Función principal"""
    print("🔬 PREPARACIÓN DE DATASET PARA DS LAB")
    print("=" * 60)
    
    # Verificar directorio de boletines
    if not BOLETINES_DIR.exists():
        print(f"❌ Error: No existe directorio {BOLETINES_DIR}")
        print(f"\n💡 Primero ejecuta: python scripts/reorganize_boletines.py")
        return
    
    # Escanear boletines
    boletines = scan_boletines(BOLETINES_DIR)
    
    if not boletines:
        print(f"❌ No se encontraron boletines en {BOLETINES_DIR}")
        return
    
    # Generar metadata
    metadata = generate_metadata(boletines, METADATA_FILE)
    
    # Generar índice CSV
    generate_csv_index(boletines, INDEX_FILE)
    
    # Resumen
    print_summary(metadata)
    
    # Verificar DS Lab
    dslab_available = check_dslab_availability()
    
    # Próximos pasos
    print(f"\n✅ Dataset preparado exitosamente")
    print(f"\n📁 Archivos generados:")
    print(f"   • Metadata: {METADATA_FILE}")
    print(f"   • Índice CSV: {INDEX_FILE}")
    
    if dslab_available:
        print(f"\n🚀 Próximos pasos:")
        print(f"   1. Revisar metadata en: {METADATA_FILE}")
        print(f"   2. Ejecutar análisis DS Lab:")
        print(f"      cd watcher-lab/watcher_ds_lab")
        print(f"      python scripts/analyze_boletines.py")
        print(f"   3. Visualizar resultados en UI del DS Lab Manager")
    else:
        print(f"\n⚠️  DS Lab no encontrado. Configura primero.")

if __name__ == "__main__":
    main()


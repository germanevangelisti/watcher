#!/usr/bin/env python3
"""
🗂️ REORGANIZACIÓN DE BOLETINES
Organiza los PDFs existentes en estructura año/mes para mejor gestión
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Directorios
SOURCE_DIR = Path("/Users/germanevangelisti/watcher-agent/boletines")
TARGET_DIR = Path("/Users/germanevangelisti/watcher-agent/boletines")
BACKUP_DIR = Path("/Users/germanevangelisti/watcher-agent/boletines_backup")

def parse_filename(filename: str) -> dict:
    """
    Parsea el nombre del archivo para extraer información
    Formato: YYYYMMDD_N_Secc.pdf
    """
    try:
        # Remover extensión
        base_name = filename.replace('.pdf', '')
        parts = base_name.split('_')
        
        if len(parts) >= 3:
            date_str = parts[0]  # YYYYMMDD
            section = parts[1]   # N
            
            # Parsear fecha
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
            
            return {
                'valid': True,
                'year': year,
                'month': month,
                'day': day,
                'section': section,
                'filename': filename
            }
    except Exception as e:
        print(f"⚠️ Error parseando {filename}: {e}")
    
    return {'valid': False, 'filename': filename}

def create_directory_structure(base_dir: Path, years: list):
    """Crea la estructura de directorios año/mes con formato 01-12"""
    print(f"📁 Creando estructura de directorios en: {base_dir}")
    
    # Usar formato 01, 02, 03... en lugar de 1, 2, 3...
    months = [f"{i:02d}" for i in range(1, 13)]
    
    for year in years:
        for month in months:
            dir_path = base_dir / year / month
            dir_path.mkdir(parents=True, exist_ok=True)
    
    print(f"✅ Estructura creada con formato 01-12")

def analyze_existing_files(source_dir: Path):
    """Analiza archivos existentes y genera reporte"""
    print(f"\n📊 Analizando archivos en: {source_dir}")
    print("=" * 60)
    
    pdf_files = list(source_dir.glob("*.pdf"))
    
    stats = {
        'total': len(pdf_files),
        'valid': 0,
        'invalid': 0,
        'by_year': defaultdict(int),
        'by_month': defaultdict(int),
        'by_section': defaultdict(int),
        'size_mb': 0
    }
    
    files_to_move = []
    
    for pdf_file in pdf_files:
        # Parsear información
        info = parse_filename(pdf_file.name)
        
        if info['valid']:
            stats['valid'] += 1
            stats['by_year'][info['year']] += 1
            stats['by_month'][f"{info['year']}-{info['month']}"] += 1
            stats['by_section'][info['section']] += 1
            stats['size_mb'] += pdf_file.stat().st_size / (1024 * 1024)
            
            files_to_move.append({
                'source': pdf_file,
                'year': info['year'],
                'month': info['month'],
                'filename': info['filename']
            })
        else:
            stats['invalid'] += 1
            print(f"⚠️ Archivo inválido: {pdf_file.name}")
    
    # Imprimir reporte
    print(f"\n📈 REPORTE DE ARCHIVOS:")
    print(f"  Total archivos: {stats['total']}")
    print(f"  Válidos: {stats['valid']}")
    print(f"  Inválidos: {stats['invalid']}")
    print(f"  Tamaño total: {stats['size_mb']:.2f} MB")
    
    print(f"\n📅 Por año:")
    for year in sorted(stats['by_year'].keys()):
        print(f"  {year}: {stats['by_year'][year]} archivos")
    
    print(f"\n📆 Por mes:")
    for month in sorted(stats['by_month'].keys()):
        print(f"  {month}: {stats['by_month'][month]} archivos")
    
    print(f"\n📑 Por sección:")
    for section in sorted(stats['by_section'].keys()):
        print(f"  Sección {section}: {stats['by_section'][section]} archivos")
    
    return files_to_move, stats

def backup_existing_files(source_dir: Path, backup_dir: Path):
    """Crea backup de seguridad antes de reorganizar"""
    print(f"\n💾 Creando backup en: {backup_dir}")
    
    if backup_dir.exists():
        print(f"⚠️ El backup ya existe. ¿Sobrescribir? (y/n): ", end='')
        response = input().lower()
        if response != 'y':
            print("❌ Backup cancelado")
            return False
        shutil.rmtree(backup_dir)
    
    # Copiar archivos
    shutil.copytree(source_dir, backup_dir, 
                    ignore=shutil.ignore_patterns('202*'))  # Ignorar directorios ya organizados
    
    print(f"✅ Backup creado con {len(list(backup_dir.glob('*.pdf')))} archivos")
    return True

def move_files_to_structure(files_to_move: list, target_dir: Path, dry_run: bool = True):
    """Mueve archivos a la estructura organizada"""
    print(f"\n🚚 {'[DRY RUN] ' if dry_run else ''}Moviendo archivos a estructura organizada...")
    print("=" * 60)
    
    moved = 0
    skipped = 0
    errors = 0
    
    for file_info in files_to_move:
        source_path = file_info['source']
        year = file_info['year']
        month = file_info['month']
        filename = file_info['filename']
        
        # Construir ruta destino
        dest_dir = target_dir / year / month
        dest_path = dest_dir / filename
        
        # Verificar si ya existe
        if dest_path.exists():
            # Comparar tamaños
            source_size = source_path.stat().st_size
            dest_size = dest_path.stat().st_size
            
            if source_size == dest_size:
                print(f"⏭️  Ya existe (mismo tamaño): {year}/{month}/{filename}")
                skipped += 1
                continue
            else:
                print(f"⚠️ Ya existe (diferente tamaño): {year}/{month}/{filename}")
                print(f"   Source: {source_size} bytes, Dest: {dest_size} bytes")
                errors += 1
                continue
        
        # Mover archivo
        if not dry_run:
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_path), str(dest_path))
                print(f"✅ Movido: {filename} → {year}/{month}/")
                moved += 1
            except Exception as e:
                print(f"❌ Error moviendo {filename}: {e}")
                errors += 1
        else:
            print(f"📋 [DRY RUN] Movería: {filename} → {year}/{month}/")
            moved += 1
    
    print(f"\n📊 RESUMEN:")
    print(f"  Movidos: {moved}")
    print(f"  Omitidos (ya existen): {skipped}")
    print(f"  Errores: {errors}")
    
    return moved, skipped, errors

def verify_organization(target_dir: Path):
    """Verifica la organización final"""
    print(f"\n🔍 Verificando organización en: {target_dir}")
    print("=" * 60)
    
    total_files = 0
    structure = defaultdict(lambda: defaultdict(int))
    
    for year_dir in sorted(target_dir.glob("202*")):
        if year_dir.is_dir():
            year = year_dir.name
            for month_dir in sorted(year_dir.glob("*")):
                if month_dir.is_dir():
                    month = month_dir.name
                    pdf_count = len(list(month_dir.glob("*.pdf")))
                    structure[year][month] = pdf_count
                    total_files += pdf_count
    
    print(f"\n📊 ESTRUCTURA FINAL:")
    for year in sorted(structure.keys()):
        print(f"\n📅 {year}:")
        for month in sorted(structure[year].keys()):
            count = structure[year][month]
            print(f"  {month}: {count} archivos")
    
    print(f"\n✅ Total de archivos organizados: {total_files}")
    
    return total_files

def main():
    """Proceso principal de reorganización"""
    print("🗂️  REORGANIZACIÓN DE BOLETINES OFICIALES")
    print("=" * 60)
    print(f"Directorio fuente: {SOURCE_DIR}")
    print(f"Directorio destino: {TARGET_DIR}")
    print("=" * 60)
    
    # 1. Analizar archivos existentes
    files_to_move, stats = analyze_existing_files(SOURCE_DIR)
    
    if not files_to_move:
        print("\n❌ No hay archivos para reorganizar")
        return
    
    # 2. Confirmar acción
    print(f"\n⚠️  Se moverán {len(files_to_move)} archivos")
    print(f"¿Continuar? (y/n): ", end='')
    response = input().lower()
    
    if response != 'y':
        print("❌ Operación cancelada")
        return
    
    # 3. Crear backup
    if not backup_existing_files(SOURCE_DIR, BACKUP_DIR):
        print("❌ No se pudo crear backup. Abortando.")
        return
    
    # 4. Crear estructura de directorios (con formato 01-12)
    years = sorted(set(f['year'] for f in files_to_move))
    create_directory_structure(TARGET_DIR, years)
    
    # 5. DRY RUN primero
    print("\n" + "=" * 60)
    print("EJECUTANDO DRY RUN (simulación)")
    print("=" * 60)
    move_files_to_structure(files_to_move, TARGET_DIR, dry_run=True)
    
    print(f"\n¿Proceder con el movimiento real? (y/n): ", end='')
    response = input().lower()
    
    if response != 'y':
        print("❌ Operación cancelada")
        return
    
    # 6. Mover archivos (real)
    print("\n" + "=" * 60)
    print("MOVIENDO ARCHIVOS (real)")
    print("=" * 60)
    moved, skipped, errors = move_files_to_structure(files_to_move, TARGET_DIR, dry_run=False)
    
    # 7. Verificar resultado
    total_organized = verify_organization(TARGET_DIR)
    
    # 8. Resumen final
    print("\n" + "=" * 60)
    print("✅ REORGANIZACIÓN COMPLETADA")
    print("=" * 60)
    print(f"Archivos organizados: {total_organized}")
    print(f"Backup disponible en: {BACKUP_DIR}")
    print(f"\nEstructura:")
    print(f"  {TARGET_DIR}/")
    print(f"    ├── 2025/")
    print(f"    │   ├── 01/")
    print(f"    │   ├── 08/  ← {stats['by_month'].get('2025-08', 0)} archivos")
    print(f"    │   └── ...")
    print(f"    └── ...")
    
    print(f"\n💡 Próximos pasos:")
    print(f"  1. Verificar archivos en {TARGET_DIR}")
    print(f"  2. Actualizar downloader para usar nueva estructura")
    print(f"  3. Ejecutar análisis con DS Lab")

if __name__ == "__main__":
    main()

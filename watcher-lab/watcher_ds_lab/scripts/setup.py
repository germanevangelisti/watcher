#!/usr/bin/env python3
"""
🔍 WATCHER DS LAB - SETUP
Script de configuración inicial para el proyecto
"""

import sys
import os
from pathlib import Path
import shutil
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_directories():
    """Crea directorios necesarios"""
    base_dir = Path(__file__).parent.parent
    
    directories = [
        base_dir / "data",
        base_dir / "models", 
        base_dir / "reports",
        base_dir / "logs",
        base_dir / "data" / "processed",
        base_dir / "data" / "raw",
        base_dir / "reports" / "false_positive_analysis"
    ]
    
    for dir_path in directories:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Directorio creado: {dir_path}")

def copy_original_data():
    """Copia datos del proyecto anterior"""
    original_dir = Path("/Users/germanevangelisti/watcher-agent/watcher-lab/resultados_watcher")
    target_dir = Path(__file__).parent.parent / "data" / "raw"
    
    if original_dir.exists():
        for file in original_dir.glob("*.csv"):
            target_file = target_dir / file.name
            shutil.copy2(file, target_file)
            logger.info(f"📋 Copiado: {file.name}")
        
        for file in original_dir.glob("*.pkl"):
            target_file = target_dir / file.name
            shutil.copy2(file, target_file)
            logger.info(f"🤖 Modelo copiado: {file.name}")
    else:
        logger.warning(f"⚠️ Directorio original no encontrado: {original_dir}")

def main():
    """Setup principal"""
    logger.info("🚀 Iniciando setup de Watcher DS Lab...")
    
    setup_directories()
    copy_original_data()
    
    logger.info("✅ Setup completado!")
    print("\n🎯 Próximos pasos:")
    print("1. cd watcher_ds_lab")
    print("2. python scripts/analyze_false_positives.py --detailed --export-results")

if __name__ == "__main__":
    main()

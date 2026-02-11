#!/usr/bin/env python3
"""
Script para crear la configuración inicial del DS Lab
basada en el análisis de agosto 2025
"""
import sys
import asyncio
from pathlib import Path

# Agregar el directorio raíz al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.database import AsyncSessionLocal
from app.db.models import AnalysisConfig

# Configuración basada en el análisis de agosto
INITIAL_CONFIG = {
    "config_name": "watcher_baseline",
    "version": "1.0.0",
    "description": "Configuración baseline basada en análisis exhaustivo de 99 boletines de agosto 2025",
    "model_version": "v1.0_agosto2025",
    "created_by": "DS Lab Team",
    "parameters": {
        "transparency_thresholds": {
            "high_risk": 30,
            "medium_risk": 50,
            "low_risk": 70,
            "description": "Scores de transparencia (0-100). Menor score = mayor riesgo"
        },
        "amount_thresholds": {
            "very_high": 50000000,
            "high": 10000000,
            "medium": 1000000,
            "suspicious_pattern_amount": 999999,
            "description": "Montos en pesos argentinos"
        },
        "ml_models": {
            "random_forest": {
                "enabled": True,
                "n_estimators": 100,
                "max_depth": 10,
                "min_samples_split": 5,
                "description": "Modelo para clasificación de riesgo"
            },
            "isolation_forest": {
                "enabled": True,
                "contamination": 0.1,
                "n_estimators": 100,
                "description": "Detección de anomalías"
            },
            "kmeans": {
                "enabled": True,
                "n_clusters": 3,
                "description": "Clustering de patrones"
            }
        },
        "nlp_config": {
            "extract_amounts": True,
            "extract_beneficiaries": True,
            "extract_organisms": True,
            "extract_dates": True,
            "min_entity_confidence": 0.7,
            "amount_regex_patterns": [
                r"\$\s*[\d\.,]+",
                r"(?:pesos|ARS)\s*[\d\.,]+",
                r"[\d\.,]+\s*(?:millones?|mil)"
            ],
            "beneficiary_keywords": [
                "adjudicatario",
                "beneficiario",
                "contratista",
                "proveedor",
                "empresa"
            ]
        },
        "red_flag_rules": {
            "HIGH_AMOUNT": {
                "enabled": True,
                "threshold": 50000000,
                "severity": "high",
                "category": "amounts"
            },
            "MISSING_BENEFICIARY": {
                "enabled": True,
                "severity": "medium",
                "category": "transparency"
            },
            "SUSPICIOUS_AMOUNT_PATTERN": {
                "enabled": True,
                "patterns": ["999999", "9999"],
                "severity": "medium",
                "category": "patterns"
            },
            "LOW_TRANSPARENCY_SCORE": {
                "enabled": True,
                "threshold": 30,
                "severity": "high",
                "category": "transparency"
            },
            "REPEATED_BENEFICIARY": {
                "enabled": True,
                "frequency_threshold": 5,
                "severity": "medium",
                "category": "patterns"
            }
        },
        "processing_options": {
            "extract_full_text": True,
            "store_text_sample_chars": 5000,
            "parallel_processing": True,
            "max_workers": 4,
            "timeout_seconds": 300,
            "retry_on_error": True,
            "max_retries": 3
        },
        "analysis_metadata": {
            "training_dataset": "agosto_2025_99_boletines",
            "training_date": "2025-08-31",
            "total_training_documents": 99,
            "high_risk_detected": 16,
            "anomalies_detected": 10,
            "avg_transparency_score": 44.6,
            "success_rate": 1.0
        }
    }
}


async def create_initial_config():
    """Crear la configuración inicial"""
    print("🚀 Creando configuración inicial del DS Lab...")
    print()
    
    async with AsyncSessionLocal() as session:
        try:
            # Verificar si ya existe
            from sqlalchemy import select
            stmt = select(AnalysisConfig).where(
                AnalysisConfig.config_name == INITIAL_CONFIG["config_name"],
                AnalysisConfig.version == INITIAL_CONFIG["version"]
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"⚠️  Configuración '{INITIAL_CONFIG['config_name']}' v{INITIAL_CONFIG['version']} ya existe")
                print(f"   ID: {existing.id}")
                print(f"   Creada: {existing.created_at}")
                print(f"   Activa: {'Sí' if existing.is_active else 'No'}")
                return True
            
            # Crear nueva configuración
            config = AnalysisConfig(**INITIAL_CONFIG, is_active=True)
            session.add(config)
            await session.commit()
            await session.refresh(config)
            
            print("✅ Configuración creada exitosamente")
            print()
            print("📋 DETALLES:")
            print("="*60)
            print(f"   ID: {config.id}")
            print(f"   Nombre: {config.config_name}")
            print(f"   Versión: {config.version}")
            print(f"   Descripción: {config.description}")
            print(f"   Modelo: {config.model_version}")
            print(f"   Activa: Sí")
            print("="*60)
            print()
            print("📊 PARÁMETROS PRINCIPALES:")
            print("   • Thresholds de transparencia: 30/50/70")
            print("   • Threshold monto alto: $50M")
            print("   • Modelos ML: Random Forest, Isolation Forest, K-Means")
            print("   • Reglas de red flags: 5 tipos configurados")
            print("   • Procesamiento paralelo: 4 workers")
            print()
            print("💡 USO:")
            print("   Para iniciar un análisis con esta config:")
            print(f"   POST /api/v1/dslab/analysis/executions")
            print(f"   {{ \"config_id\": {config.id}, ... }}")
            print()
            
            return True
            
        except Exception as e:
            print(f"❌ Error creando configuración: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = asyncio.run(create_initial_config())
    sys.exit(0 if success else 1)


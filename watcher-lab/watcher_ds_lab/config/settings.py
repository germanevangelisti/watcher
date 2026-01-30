"""
🔍 WATCHER DS LAB - CONFIGURACIÓN PRINCIPAL
Configuraciones globales para el sistema de análisis de transparencia
"""

from pathlib import Path
import os

# Directorios base
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
SRC_DIR = BASE_DIR / "src"

# Datos originales (desde proyecto anterior)
ORIGINAL_DATA_DIR = Path("/Users/germanevangelisti/watcher-agent/watcher-lab/resultados_watcher")
BOLETINES_DIR = Path("/Users/germanevangelisti/watcher-agent/boletines")

# Configuración de modelos ML
ML_CONFIG = {
    "risk_classifier": {
        "model_type": "RandomForest",
        "n_estimators": 100,
        "max_depth": 10,
        "random_state": 42
    },
    "anomaly_detector": {
        "model_type": "IsolationForest",
        "contamination": 0.1,
        "random_state": 42,
        "n_estimators": 100
    },
    "clustering": {
        "model_type": "KMeans",
        "n_clusters": 5,
        "random_state": 42,
        "n_init": 10
    }
}

# Configuración de extracción de entidades
EXTRACTION_CONFIG = {
    "amount_patterns": [
        r'\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',  # $999.999.999,99
        r'PESOS\s+(\w+(?:\s+\w+)*)',  # PESOS CINCO MIL
        r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*PESOS',  # 999.999,99 PESOS
    ],
    "entity_patterns": [
        r'(?:BENEFICIARIO|CONTRATISTA|PROVEEDOR|ADJUDICADO A):\s*([A-Z\s\.,]+)',
        r'(?:EMPRESA|COOPERATIVA|FUNDACIÓN|ASOCIACIÓN)\s+([A-Z\s\.,]+)',
        r'(?:SR\.|SRA\.|SEÑOR|SEÑORA)\s+([A-Z\s\.]+)',
    ],
    "risk_keywords": {
        'ALTO': [
            'urgencia', 'emergencia', 'excepción', 'sin licitación',
            'contratación directa', 'exclusivo', 'único proveedor',
            'decreto de necesidad', 'situación excepcional'
        ],
        'MEDIO': [
            'discrecional', 'renovación', 'prórroga', 'modificación',
            'ampliación', 'adicional', 'complementario', 'convenio marco'
        ],
        'BAJO': [
            'licitación pública', 'concurso', 'proceso regular',
            'marco legal', 'transparencia', 'registro público'
        ]
    },
    "transparency_keywords": {
        'POSITIVE': [
            'licitación pública', 'concurso', 'transparencia', 'público',
            'resolución', 'decreto', 'normativa', 'registro público',
            'proceso competitivo', 'marco legal'
        ],
        'NEGATIVE': [
            'urgencia', 'excepción', 'directa', 'exclusivo',
            'único proveedor', 'situación excepcional', 'emergencia'
        ]
    }
}

# Configuración de scoring de transparencia
TRANSPARENCY_CONFIG = {
    "base_score": 50,
    "risk_penalties": {
        "ALTO": -30,
        "MEDIO": -15,
        "BAJO": 0
    },
    "amount_bonus": 10,  # Bonus por tener montos específicos
    "transparency_bonus": 5,  # Bonus por palabra de transparencia
    "opacity_penalty": -8,  # Penalización por palabra de opacidad
    "min_score": 0,
    "max_score": 100
}

# Configuración de validación
VALIDATION_CONFIG = {
    "false_positive_thresholds": {
        "transparency_score": 50,  # Si > 50 y riesgo ALTO, posible FP
        "anomaly_score": 0.3,      # Si < 0.3 y riesgo ALTO, posible FP
        "transparency_keywords_min": 2  # Mínimo keywords transparencia para FP
    },
    "quality_metrics": {
        "target_precision": 0.8,
        "target_recall": 0.7,
        "target_f1": 0.75,
        "max_false_positive_rate": 0.2
    }
}

# Configuración de procesamiento
PROCESSING_CONFIG = {
    "max_workers": 6,
    "batch_size": 10,
    "timeout_seconds": 300,
    "max_text_length": 1000000,
    "pdf_extraction_method": "pdfplumber"
}

# Nuevas features a implementar
NEW_FEATURES_CONFIG = {
    "contexto_transparente": {
        "keywords": ["norma", "decreto", "licitación", "resolución", "registro"],
        "min_mentions": 1
    },
    "justificacion_detectada": {
        "positive_patterns": [
            r"en virtud de",
            r"considerando",
            r"por cuanto",
            r"atento a"
        ],
        "negative_patterns": [
            r"sin justificación",
            r"sin fundamento"
        ]
    },
    "tipo_evento": {
        "patterns": {
            "DESIGNACION": ["design", "nombr", "cargo", "función"],
            "SUBSIDIO": ["subsid", "transfer", "ayuda", "apoyo"],
            "OBRA_PUBLICA": ["obra", "construcción", "infraestructura"],
            "CONTRATACION": ["contrat", "licit", "proveedor", "servicio"],
            "CONVENIO": ["convenio", "acuerdo", "alianza"]
        }
    }
}

# Configuración de alertas agentic
AGENT_CONFIG = {
    "alert_thresholds": {
        "critical_transparency": 25,
        "high_risk_amount": 1000000,  # 1M pesos
        "anomaly_threshold": -0.1,
        "keyword_density": 0.05
    },
    "monitoring_intervals": {
        "real_time": 60,  # segundos
        "daily_summary": 86400,
        "weekly_report": 604800
    },
    "notification_levels": {
        "CRITICO": {"color": "red", "priority": 1},
        "ALTO": {"color": "orange", "priority": 2},
        "MEDIO": {"color": "yellow", "priority": 3},
        "INFORMATIVO": {"color": "blue", "priority": 4}
    }
}

# Configuración de outputs
OUTPUT_CONFIG = {
    "report_formats": ["json", "csv", "html", "pdf"],
    "visualization_types": [
        "timeline", "heatmap", "network", "distribution", 
        "correlation", "anomaly_plot", "risk_dashboard"
    ],
    "export_options": {
        "include_raw_data": True,
        "include_models": True,
        "include_visualizations": True,
        "compress_output": True
    }
}

# Logging configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": str(BASE_DIR / "logs" / "watcher.log"),
    "max_size": "10MB",
    "backup_count": 5
}

"""
Configuración central del backend
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Settings(BaseModel):
    """Configuración central de la aplicación."""
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Watcher API"
    
    # Google AI
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    
    # Anthropic (optional alternative)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    # LLM Provider selection
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")
    
    # Watcher
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    MAX_FRAGMENT_SIZE: int = int(os.getenv("MAX_FRAGMENT_SIZE", "2000"))
    
    # Upload settings (Epic 1.2 & 1.3)
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    MIN_UPLOAD_SIZE_KB: int = int(os.getenv("MIN_UPLOAD_SIZE_KB", "10"))
    ALLOWED_FILE_TYPES: list = ["application/pdf"]
    DOWNLOAD_TIMEOUT: float = float(os.getenv("DOWNLOAD_TIMEOUT", "60.0"))
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    PROJECT_ROOT: Path = BASE_DIR.parent  # /watcher (repo root)
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOADS_DIR: Path = DATA_DIR / "uploads"
    RESULTS_DIR: Path = DATA_DIR / "results"
    BOLETINES_DIR: Path = PROJECT_ROOT / "boletines"  # Downloaded PDFs organized by year/month

    class Config:
        case_sensitive = True

# Instancia global de configuración
settings = Settings()

# Crear directorios necesarios
settings.UPLOADS_DIR.mkdir(exist_ok=True)
settings.RESULTS_DIR.mkdir(exist_ok=True)

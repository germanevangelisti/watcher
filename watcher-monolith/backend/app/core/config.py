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
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Watcher
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    MAX_FRAGMENT_SIZE: int = int(os.getenv("MAX_FRAGMENT_SIZE", "2000"))
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOADS_DIR: Path = DATA_DIR / "uploads"
    RESULTS_DIR: Path = DATA_DIR / "results"

    class Config:
        case_sensitive = True

# Instancia global de configuración
settings = Settings()

# Crear directorios necesarios
settings.UPLOADS_DIR.mkdir(exist_ok=True)
settings.RESULTS_DIR.mkdir(exist_ok=True)

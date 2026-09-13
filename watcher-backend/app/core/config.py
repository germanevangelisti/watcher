"""
Configuración central del backend
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

# Busca .env desde el directorio actual hacia arriba (cubre tanto watcher-backend/ como watcher/)
_env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path if _env_path.exists() else None)


def _parse_origins(raw: str | None) -> list[str]:
    if not raw:
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


class Settings(BaseModel):
    """Configuración central de la aplicación."""
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Watcher API"

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///sqlite.db",
    )
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL",
        "sqlite:///sqlite.db",
    )

    # Neo4j Graph Database
    NEO4J_URI: str | None = os.getenv("NEO4J_URI", None)
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "watcher_neo4j_2026")

    # CORS
    ALLOWED_ORIGINS: list[str] = _parse_origins(os.getenv("ALLOWED_ORIGINS"))

    # Google AI
    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")

    # Anthropic (optional alternative)
    ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")

    # LLM Provider selection
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")

    # Hardware / local pipeline (H.1)
    HARDWARE_PROFILE: str = os.getenv("HARDWARE_PROFILE", "")
    INTELLIGENCE_PROVIDER: str = os.getenv("INTELLIGENCE_PROVIDER", "auto")
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "")
    RERANK_STRATEGY: str = os.getenv("RERANK_STRATEGY", "auto")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
    LOCAL_EMBEDDING_MODEL: str = os.getenv(
        "LOCAL_EMBEDDING_MODEL",
        "paraphrase-multilingual-MiniLM-L12-v2",
    )
    LOCAL_RERANK_MODEL: str = os.getenv(
        "LOCAL_RERANK_MODEL",
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
    )

    # Watcher
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    MAX_FRAGMENT_SIZE: int = int(os.getenv("MAX_FRAGMENT_SIZE", "2000"))

    # Upload settings
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    MIN_UPLOAD_SIZE_KB: int = int(os.getenv("MIN_UPLOAD_SIZE_KB", "10"))
    ALLOWED_FILE_TYPES: list = ["application/pdf"]
    DOWNLOAD_TIMEOUT: float = float(os.getenv("DOWNLOAD_TIMEOUT", "60.0"))

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    PROJECT_ROOT: Path = BASE_DIR.parent
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOADS_DIR: Path = DATA_DIR / "uploads"
    RESULTS_DIR: Path = DATA_DIR / "results"
    BOLETINES_DIR: Path = Path(os.getenv("BOLETINES_DIR", str(PROJECT_ROOT / "boletines")))

    class Config:
        case_sensitive = True

    @property
    def is_postgres(self) -> bool:
        return "postgresql" in self.DATABASE_URL

    @property
    def neo4j_enabled(self) -> bool:
        return self.NEO4J_URI is not None

    @property
    def hardware_profile(self) -> str:
        from app.core.hardware import hardware_profile as _profile

        return _profile()

    @property
    def pipeline_workers(self) -> int:
        from app.core.hardware import pipeline_workers as _workers

        return _workers()

    @property
    def llm_max_concurrent(self) -> int:
        from app.core.hardware import llm_max_concurrent as _llm

        return _llm()

    @property
    def prefer_local_ai(self) -> bool:
        from app.core.hardware import prefer_local_ai as _local

        return _local()

settings = Settings()

settings.UPLOADS_DIR.mkdir(exist_ok=True, parents=True)
settings.RESULTS_DIR.mkdir(exist_ok=True, parents=True)

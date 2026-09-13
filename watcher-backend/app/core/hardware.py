"""Perfil de hardware y concurrencia del pipeline.

Prioriza la workstation local (CPU count, GPU) frente al perfil cloud
(GCE e2-medium). Los valores se leen de env en cada llamada para que los
tests puedan parchear os.environ sin reinstanciar Settings.
"""

from __future__ import annotations

import os
from functools import lru_cache


def cpu_count() -> int:
    return os.cpu_count() or 2


def hardware_profile() -> str:
    """Return ``local`` or ``cloud``.

    Explicit ``HARDWARE_PROFILE`` wins. Production defaults to cloud so the
    GCE e2-medium deploy keeps conservative memory; development defaults to
    local (cooperledge / any workstation).
    """
    explicit = os.getenv("HARDWARE_PROFILE", "").strip().lower()
    if explicit in {"local", "cloud"}:
        return explicit
    if os.getenv("ENVIRONMENT", "development").strip().lower() == "production":
        return "cloud"
    return "local"


def prefer_local_ai() -> bool:
    return hardware_profile() == "local"


def cpu_reserve() -> int:
    raw = os.getenv("PIPELINE_CPU_RESERVE", "2").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 2


def default_worker_count(reserve: int | None = None) -> int:
    """PDF / extract workers: ``max(1, nproc - reserve)``."""
    reserved = cpu_reserve() if reserve is None else max(0, reserve)
    return max(1, cpu_count() - reserved)


def pipeline_workers() -> int:
    raw = os.getenv("PIPELINE_WORKERS", "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return default_worker_count()


def llm_max_concurrent() -> int:
    """Cap concurrent LLM calls so a 12 GB GPU is not oversubscribed."""
    raw = os.getenv("LLM_MAX_CONCURRENT", "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return 1 if prefer_local_ai() else 4


def document_pipeline_concurrency() -> int:
    """PDF extract/index concurrency. LLM calls are capped separately."""
    return pipeline_workers()


def ollama_num_ctx() -> int:
    """KV-cache size. 4096 fits a 14B Q4 on 12 GB; 8192 often spills to RAM."""
    raw = os.getenv("OLLAMA_NUM_CTX", "").strip()
    if raw:
        try:
            return max(512, int(raw))
        except ValueError:
            pass
    return 4096


def ollama_timeout_s() -> float:
    raw = os.getenv("OLLAMA_TIMEOUT_S", "").strip()
    if raw:
        try:
            return max(30.0, float(raw))
        except ValueError:
            pass
    return 600.0


def index_chunk_size() -> int:
    """Larger chunks on local so judiciales PDFs do not explode to 500+ pieces."""
    raw = os.getenv("PIPELINE_CHUNK_SIZE", "").strip()
    if raw:
        try:
            return max(400, int(raw))
        except ValueError:
            pass
    return 3000 if prefer_local_ai() else 1000


def max_index_chunks() -> int:
    """0 = no cap. Local default keeps Chroma/CPU bounded per PDF."""
    raw = os.getenv("PIPELINE_MAX_INDEX_CHUNKS", "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            pass
    return 80 if prefer_local_ai() else 0


def max_analysis_fragments() -> int:
    """0 = no cap. Local default limits sequential Ollama calls per PDF."""
    raw = os.getenv("ANALYSIS_MAX_FRAGMENTS", "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            pass
    return 8 if prefer_local_ai() else 0


@lru_cache(maxsize=1)
def cuda_available() -> bool:
    try:
        import torch  # type: ignore[import-untyped]

        return bool(torch.cuda.is_available())
    except (ImportError, OSError, RuntimeError):
        return False


def local_device() -> str:
    return "cuda" if cuda_available() else "cpu"


def embedding_provider_default() -> str:
    explicit = os.getenv("EMBEDDING_PROVIDER", "").strip().lower()
    if explicit in {"google", "local"}:
        return explicit
    return "local" if prefer_local_ai() else "google"


def rerank_strategy_default() -> str | None:
    explicit = os.getenv("RERANK_STRATEGY", "").strip().lower()
    if explicit in {"cross-encoder", "google", "noop"}:
        return explicit
    if explicit in {"", "auto"}:
        return None
    return None


def intelligence_provider_choice() -> str:
    """Return ``local`` | ``google`` | ``free`` | ``auto``."""
    explicit = os.getenv("INTELLIGENCE_PROVIDER", "auto").strip().lower()
    if explicit in {"local", "google", "free", "auto"}:
        return explicit
    return "auto"


def ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "").strip()


def ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen2.5:14b").strip() or "qwen2.5:14b"


def local_embedding_model() -> str:
    return (
        os.getenv("LOCAL_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2").strip()
        or "paraphrase-multilingual-MiniLM-L12-v2"
    )


def local_rerank_model() -> str:
    return (
        os.getenv("LOCAL_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2").strip()
        or "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )


def hardware_snapshot() -> dict[str, object]:
    return {
        "profile": hardware_profile(),
        "cpu_count": cpu_count(),
        "pipeline_workers": pipeline_workers(),
        "llm_max_concurrent": llm_max_concurrent(),
        "document_pipeline_concurrency": document_pipeline_concurrency(),
        "prefer_local_ai": prefer_local_ai(),
        "cuda_available": cuda_available(),
        "device": local_device(),
        "embedding_provider": embedding_provider_default(),
        "rerank_strategy": rerank_strategy_default() or "auto",
        "intelligence_provider": intelligence_provider_choice(),
        "ollama_configured": bool(ollama_base_url()),
        "ollama_num_ctx": ollama_num_ctx(),
        "max_index_chunks": max_index_chunks(),
        "max_analysis_fragments": max_analysis_fragments(),
    }

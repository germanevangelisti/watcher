"""LocalPro — IntelligenceProvider backed by a local Ollama server.

Uses the same acto schema as Gemini so downstream feature engineering
does not change. Concurrent calls are capped (default 1) to fit a 12 GB GPU.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
from app.core.hardware import (
    llm_max_concurrent,
    ollama_base_url,
    ollama_model,
    ollama_num_ctx,
    ollama_timeout_s,
)
from app.services.analysis_schema import (
    ANALYSIS_SYSTEM_PROMPT,
    FRAGMENT_ANALYSIS_SCHEMA,
)
from app.services.intelligence_provider import FreeProvider, IntelligenceProvider

logger = logging.getLogger(__name__)

_LLM_SEM: asyncio.Semaphore | None = None


def salvage_fragment_json(raw: str) -> dict[str, Any] | None:
    """Parse a LocalPro payload, recovering complete acto objects if truncated."""
    if not raw or not isinstance(raw, str):
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    marker = raw.find('"actos"')
    bracket = raw.find("[", marker if marker >= 0 else 0)
    if bracket < 0:
        return None
    decoder = json.JSONDecoder()
    actos: list[dict[str, Any]] = []
    i = bracket
    while i < len(raw):
        if raw[i] != "{":
            i += 1
            continue
        try:
            obj, end = decoder.raw_decode(raw, i)
        except json.JSONDecodeError:
            break
        if isinstance(obj, dict):
            actos.append(obj)
        i = end
    if not actos:
        return None
    return {
        "actos": actos,
        "resumen_general": "JSON truncado; actos recuperados",
    }


def _llm_semaphore() -> asyncio.Semaphore:
    global _LLM_SEM
    if _LLM_SEM is None:
        _LLM_SEM = asyncio.Semaphore(llm_max_concurrent())
    return _LLM_SEM


def _normalize_actos(result: dict[str, Any], metadata: dict[str, Any], model_name: str) -> dict[str, Any]:
    if "actos" not in result or not isinstance(result["actos"], list):
        result["actos"] = []
    if "resumen_general" not in result:
        result["resumen_general"] = "Resumen no disponible"
    for acto in result["actos"]:
        if not isinstance(acto, dict):
            continue
        acto.setdefault("tipo_acto", "otro")
        acto.setdefault("organismo", "No especificado")
        acto.setdefault("descripcion", "Sin descripción")
        acto.setdefault("riesgo", "informativo")
        acto.setdefault("beneficiarios", [])
        acto.setdefault("montos", [])
        acto.setdefault("monto_total_numerico", 0)
        acto.setdefault("texto_original", "")
        acto.setdefault("fecha_acto", None)
        acto.setdefault("expediente", None)
        acto.setdefault("referencias_normativas", [])
        acto.setdefault("fechas_clave", [])
        acto.setdefault("relacion_principal", None)
        acto.setdefault("firmante", None)
        acto.setdefault("imputacion_presupuestaria", None)
        acto.setdefault("presupuesto_oficial", 0)
    result["metadata"] = metadata
    result["model_used"] = model_name
    return result


class LocalProProvider(IntelligenceProvider):
    """Structured acto extraction via Ollama HTTP API."""

    tier = "local"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float | None = None,
    ) -> None:
        self.base_url = (base_url or ollama_base_url() or "http://127.0.0.1:11434").rstrip("/")
        self.model_name = model or ollama_model()
        self.timeout_s = float(timeout_s) if timeout_s is not None else ollama_timeout_s()
        self._free = FreeProvider()

    def list_capabilities(self) -> list[str]:
        return [
            "llm_structured_extraction",
            "local_inference",
            "risk_classification",
            "entity_extraction",
            "amount_parsing",
        ]

    async def analyze_fragment(
        self, content: str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        prompt = f"Contenido a analizar:\n{content}"
        payload = {
            "model": self.model_name,
            "stream": False,
            "keep_alive": "30m",
            "format": FRAGMENT_ANALYSIS_SCHEMA,
            "messages": [
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "options": {
                "temperature": 0.1,
                "num_ctx": ollama_num_ctx(),
                "num_predict": 2048,
            },
        }
        url = f"{self.base_url}/api/chat"
        try:
            async with _llm_semaphore(), httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, OSError, TimeoutError, ValueError) as exc:
            logger.warning(
                "LocalPro Ollama unavailable (%s); falling back to FreeProvider",
                exc,
            )
            fallback = await self._free.analyze_fragment(content, metadata)
            fallback["model_used"] = f"free_fallback_after_local:{exc.__class__.__name__}"
            return fallback

        message = body.get("message") or {}
        raw = message.get("content") or body.get("response") or "{}"
        try:
            parsed = salvage_fragment_json(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            parsed = None
        if parsed is None:
            logger.warning("LocalPro returned invalid JSON")
            return _normalize_actos(
                {
                    "actos": [],
                    "resumen_general": "JSON inválido del modelo local",
                    "error": "invalid_json",
                },
                metadata,
                self.model_name,
            )
        if not isinstance(parsed, dict):
            parsed = {"actos": [], "resumen_general": "Respuesta local no era un objeto"}
        return _normalize_actos(parsed, metadata, self.model_name)

    async def analyze_content(
        self, content: str, metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        result = await self.analyze_fragment(content, metadata)
        all_actos: list[dict[str, Any]] = []
        for i, acto in enumerate(result.get("actos", [])):
            acto["_fragment_index"] = i
            acto["_fragment_content"] = acto.get("texto_original") or content[:500]
            acto["_resumen_fragmento"] = result.get("resumen_general", "")
            acto["_model_used"] = result.get("model_used", self.model_name)
            all_actos.append(acto)
        return all_actos

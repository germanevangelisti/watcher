"""
intelligence_provider.py — Analysis tier abstraction for Watcher.

Defines an IntelligenceProvider protocol with two concrete implementations:

- FreeProvider  — keyword/rule-based, no LLM, no API key required.
- ProProvider   — full LLM analysis via Google Gemini (requires GOOGLE_API_KEY).

Usage:
    from app.services.intelligence_provider import get_default_provider

    provider = get_default_provider()
    result = await provider.analyze_fragment(content, metadata)
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword lists for free-tier risk detection
# ---------------------------------------------------------------------------
_ALTO_RIESGO_KEYWORDS = (
    "contratación directa",
    "sin licitación",
    "fraccionamiento",
    "urgencia",
    "emergencia",
    "excepción",
)

_MEDIO_RIESGO_KEYWORDS = (
    "modificación",
    "ampliación",
    "adenda",
    "prorroga",
    "prórroga",
)

_MONTO_RE = re.compile(r"[\$\$]?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?")
_BIG_AMOUNT_THRESHOLD = 1_000_000_000  # 1 billion ARS


def _parse_max_amount(content: str) -> float:
    """Extract the largest numeric amount from a text fragment."""
    max_val = 0.0
    for m in _MONTO_RE.finditer(content):
        raw = m.group().replace("$", "").replace(" ", "")
        # Normalise: last separator is decimal, others are thousands
        raw = raw.replace(".", "").replace(",", ".")
        try:
            val = float(raw)
            if val > max_val:
                max_val = val
        except ValueError:
            continue
    return max_val


def _free_risk_level(content: str, max_amount: float) -> str:
    low = content.lower()
    for kw in _ALTO_RIESGO_KEYWORDS:
        if kw in low:
            return "alto"
    for kw in _MEDIO_RIESGO_KEYWORDS:
        if kw in low:
            return "medio"
    if max_amount >= _BIG_AMOUNT_THRESHOLD:
        return "medio"
    if max_amount >= 100_000_000:
        return "bajo"
    return "informativo"


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class IntelligenceProvider:
    """
    Structural protocol for analysis providers.

    Both FreeProvider and ProProvider satisfy this interface.
    """

    tier: str

    async def analyze_fragment(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    async def analyze_content(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def list_capabilities(self) -> List[str]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# FreeProvider — no LLM, rule-based
# ---------------------------------------------------------------------------


class FreeProvider(IntelligenceProvider):
    """
    Rule-based analysis provider.

    Returns a single synthetic acto per fragment using keyword detection
    and amount parsing. Does not require any API key.
    """

    tier = "free"

    def list_capabilities(self) -> List[str]:
        return [
            "keyword_risk_detection",
            "amount_extraction",
            "basic_type_classification",
        ]

    async def analyze_fragment(
        self, content: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        amount = _parse_max_amount(content)
        risk = _free_risk_level(content, amount)

        # Classify type from keywords
        low = content.lower()
        if "licitación" in low or "licitacion" in low:
            tipo = "licitacion"
        elif "decreto" in low:
            tipo = "decreto"
        elif "resolución" in low or "resolucion" in low:
            tipo = "resolucion"
        elif "designación" in low or "designacion" in low:
            tipo = "designacion"
        elif "subsidio" in low:
            tipo = "subsidio"
        elif "transferencia" in low:
            tipo = "transferencia"
        else:
            tipo = "otro"

        acto: Dict[str, Any] = {
            "tipo_acto": tipo,
            "organismo": metadata.get("fuente", "No especificado"),
            "beneficiarios": [],
            "montos": [],
            "monto_total_numerico": amount,
            "descripcion": f"Análisis básico (sin LLM) — {content[:100].strip()}",
            "riesgo": risk,
            "motivo_riesgo": f"Detección por palabras clave (tier={self.tier})",
            "accion_sugerida": "Revisar manualmente",
            "texto_original": content[:300],
            "fecha_acto": None,
            "expediente": None,
            "referencias_normativas": [],
            "fechas_clave": [],
            "relacion_principal": None,
            "firmante": None,
            "imputacion_presupuestaria": None,
            "presupuesto_oficial": 0,
        }

        return {
            "actos": [acto],
            "resumen_general": f"Fragmento analizado con proveedor libre (tier={self.tier})",
            "metadata": metadata,
            "fragment_tokens": len(content) // 4,
            "model_used": f"rule_based_{self.tier}",
        }

    async def analyze_content(
        self, content: str, metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        result = await self.analyze_fragment(content, metadata)
        all_actos: List[Dict[str, Any]] = []
        for i, acto in enumerate(result.get("actos", [])):
            acto["_fragment_index"] = i
            acto["_fragment_content"] = acto.get("texto_original") or content[:500]
            acto["_resumen_fragmento"] = result.get("resumen_general", "")
            acto["_model_used"] = result.get("model_used", "rule_based")
            all_actos.append(acto)
        return all_actos


# ---------------------------------------------------------------------------
# ProProvider — full LLM via Google Gemini
# ---------------------------------------------------------------------------


class ProProvider(IntelligenceProvider):
    """
    LLM-backed analysis provider using Google Gemini.

    Delegates to WatcherService for fragment analysis.
    Requires GOOGLE_API_KEY to be configured.
    """

    tier = "pro"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._service: Optional[Any] = None

    def _get_service(self) -> Any:
        """Lazy-initialise WatcherService (avoids circular imports)."""
        if self._service is None:
            from app.services.watcher_service import WatcherService  # noqa: PLC0415
            self._service = WatcherService()
        return self._service

    def list_capabilities(self) -> List[str]:
        return [
            "llm_structured_extraction",
            "risk_classification",
            "entity_extraction",
            "amount_parsing",
            "timeline_enrichment",
            "reference_firewall",
        ]

    async def analyze_fragment(
        self, content: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        svc = self._get_service()
        return await svc.analyze_fragment(content, metadata)

    async def analyze_content(
        self, content: str, metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        svc = self._get_service()
        return await svc.analyze_content(content, metadata)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_PROVIDER_CACHE: Dict[str, IntelligenceProvider] = {}


def get_default_provider(api_key: Optional[str] = None) -> IntelligenceProvider:
    """
    Return the appropriate provider based on API key availability.

    - If api_key is provided and non-empty: returns ProProvider (Gemini).
    - Otherwise: returns FreeProvider (rule-based, no LLM).

    Results are cached by tier.
    """
    if not api_key:
        from app.core.config import settings  # noqa: PLC0415
        api_key = settings.GOOGLE_API_KEY

    tier = "pro" if api_key else "free"

    cached = _PROVIDER_CACHE.get(tier)
    if cached is not None:
        return cached

    provider: IntelligenceProvider
    if tier == "pro":
        assert api_key is not None  # guaranteed by condition above
        provider = ProProvider(api_key)
        logger.info("IntelligenceProvider: using ProProvider (Gemini)")
    else:
        provider = FreeProvider()
        logger.info("IntelligenceProvider: using FreeProvider (rule-based, no LLM)")

    _PROVIDER_CACHE[tier] = provider
    return provider

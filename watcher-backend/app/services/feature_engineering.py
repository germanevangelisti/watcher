"""Feature Engineering per acto administrativo — Épica 3.

Centraliza la lógica que antes estaba repartida (DSLabAnalyzer a nivel documento,
AlertGenerator sin cablear, watcher_service con riesgo categórico) en un único
servicio que opera **por acto administrativo** ya extraído por Gemini / FreeProvider.

Expone:
- ``TransparencyScorer``: score 0–100 de transparencia por acto (3.1).
- ``RedFlagClassifier``: clasificación de irregularidades con tipología (3.2).
- ``ActoFeatureEngineer``: fachada que combina ambos en un solo paso.

El servicio es puro (sin I/O, sin LLM): toma el dict del acto producido por
``WatcherService.analyze_content`` y devuelve features deterministas y testeables.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tipología unificada de red flags
# ---------------------------------------------------------------------------


class RedFlagType(str, Enum):
    """Tipología canónica de irregularidades detectables por acto."""

    HIGH_AMOUNT = "HIGH_AMOUNT"
    SUSPICIOUS_AMOUNT_PATTERN = "SUSPICIOUS_AMOUNT_PATTERN"
    ROUND_AMOUNT = "ROUND_AMOUNT"
    MISSING_BENEFICIARY = "MISSING_BENEFICIARY"
    MISSING_AMOUNT = "MISSING_AMOUNT"
    MISSING_EXPEDIENTE = "MISSING_EXPEDIENTE"
    MISSING_LEGAL_REFERENCE = "MISSING_LEGAL_REFERENCE"
    LOW_TRANSPARENCY_SCORE = "LOW_TRANSPARENCY_SCORE"
    OVER_BUDGET = "OVER_BUDGET"


class Severity(str, Enum):
    """Severidad canónica (alineada con ``riesgo`` de los actos)."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RedFlag:
    """Una irregularidad detectada en un acto."""

    type: RedFlagType
    severity: Severity
    title: str
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class ActoFeatures:
    """Resultado del feature engineering de un acto."""

    transparency_score: float
    red_flags: List[RedFlag] = field(default_factory=list)
    score_breakdown: Dict[str, float] = field(default_factory=dict)

    @property
    def num_red_flags(self) -> int:
        return len(self.red_flags)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transparency_score": round(self.transparency_score, 2),
            "num_red_flags": self.num_red_flags,
            "red_flags": [rf.to_dict() for rf in self.red_flags],
            "score_breakdown": {k: round(v, 2) for k, v in self.score_breakdown.items()},
        }


# ---------------------------------------------------------------------------
# Helpers de normalización del acto
# ---------------------------------------------------------------------------


def _is_present(value: Any) -> bool:
    """True si el campo tiene contenido útil (no vacío, no placeholder)."""
    if value is None:
        return False
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    text = str(value).strip()
    if not text:
        return False
    return text.lower() not in {
        "no especificado",
        "no especificada",
        "n/a",
        "na",
        "none",
        "null",
        "-",
        "sin datos",
        "desconocido",
    }


def _acto_monto(acto: Dict[str, Any]) -> float:
    """Extrae el monto numérico total del acto, robusto a múltiples formatos."""
    for key in ("monto_total_numerico", "monto_numerico"):
        val = acto.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    # Fallback: parsear strings de montos
    montos = acto.get("montos") or []
    total = 0.0
    for raw in montos:
        total += _parse_amount_string(str(raw))
    return total


_AMOUNT_RE = re.compile(r"[\d.,]+")


def _parse_amount_string(raw: str) -> float:
    """Convierte '$3.010.523.733,29' o 'pesos 1.000.000' a float (formato es-AR)."""
    match = _AMOUNT_RE.search(str(raw).replace(" ", ""))
    if not match:
        return 0.0
    token = match.group(0).strip(".,")
    if not token:
        return 0.0
    # Formato es-AR: '.' separa miles, ',' separa decimales.
    if "," in token:
        token = token.replace(".", "").replace(",", ".")
    elif "." in token:
        token = token.replace(".", "")
    try:
        return float(token)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# 3.1 Transparency scoring (0–100) por acto
# ---------------------------------------------------------------------------


class TransparencyScorer:
    """Calcula un score de transparencia 0–100 por acto administrativo.

    Mayor score = mayor transparencia (más completo y trazable). El score parte
    de una base y suma puntos por la presencia de los campos que permiten
    auditar el acto (organismo, beneficiarios, montos, expediente, referencias
    normativas, imputación presupuestaria, firmante, fechas). Penaliza
    descripciones ausentes o muy cortas.
    """

    BASE_SCORE = 30.0

    # Peso de cada campo de trazabilidad (suman 70 → base 30 + 70 = 100).
    FIELD_WEIGHTS: Dict[str, float] = {
        "organismo": 12.0,
        "beneficiarios": 12.0,
        "montos": 10.0,
        "expediente": 10.0,
        "referencias_normativas": 8.0,
        "imputacion_presupuestaria": 8.0,
        "firmante": 5.0,
        "fecha_acto": 5.0,
    }

    SHORT_DESCRIPTION_PENALTY = 8.0
    MIN_DESCRIPTION_LEN = 40

    def score(self, acto: Dict[str, Any]) -> tuple[float, Dict[str, float]]:
        """Devuelve ``(score, breakdown)`` con el detalle por campo."""
        breakdown: Dict[str, float] = {"base": self.BASE_SCORE}
        score = self.BASE_SCORE

        for field_name, weight in self.FIELD_WEIGHTS.items():
            if _is_present(acto.get(field_name)):
                score += weight
                breakdown[field_name] = weight
            else:
                breakdown[field_name] = 0.0

        # Penalización por descripción ausente o demasiado corta.
        descripcion = str(acto.get("descripcion") or "").strip()
        if len(descripcion) < self.MIN_DESCRIPTION_LEN:
            score -= self.SHORT_DESCRIPTION_PENALTY
            breakdown["descripcion_penalty"] = -self.SHORT_DESCRIPTION_PENALTY

        score = max(0.0, min(100.0, score))
        return score, breakdown


# ---------------------------------------------------------------------------
# 3.2 Red flag classification con tipología
# ---------------------------------------------------------------------------


@dataclass
class RedFlagConfig:
    """Umbrales configurables del clasificador de red flags."""

    high_amount_threshold: float = 50_000_000.0
    round_amount_threshold: float = 1_000_000.0
    suspicious_patterns: tuple[str, ...] = ("999999", "9999", "888888")
    low_transparency_threshold: float = 40.0
    # Tipos de acto donde un monto es esperable (ausencia ⇒ red flag).
    amount_expected_types: tuple[str, ...] = (
        "licitacion",
        "subsidio",
        "transferencia",
    )


class RedFlagClassifier:
    """Clasifica irregularidades de un acto según la tipología canónica."""

    def __init__(self, config: Optional[RedFlagConfig] = None):
        self.config = config or RedFlagConfig()

    def classify(
        self,
        acto: Dict[str, Any],
        transparency_score: Optional[float] = None,
    ) -> List[RedFlag]:
        flags: List[RedFlag] = []
        monto = _acto_monto(acto)
        tipo_acto = str(acto.get("tipo_acto") or "").lower()
        has_beneficiary = _is_present(acto.get("beneficiarios"))

        # HIGH_AMOUNT
        if monto >= self.config.high_amount_threshold:
            flags.append(
                RedFlag(
                    type=RedFlagType.HIGH_AMOUNT,
                    severity=Severity.HIGH,
                    title=f"Monto elevado: ${monto:,.0f}",
                    description=(
                        f"El acto involucra ${monto:,.0f}, por encima del umbral "
                        f"de ${self.config.high_amount_threshold:,.0f}."
                    ),
                    evidence={"monto": monto, "threshold": self.config.high_amount_threshold},
                    confidence=0.9,
                )
            )

        # SUSPICIOUS_AMOUNT_PATTERN
        if monto > 0:
            monto_str = str(int(monto))
            for pattern in self.config.suspicious_patterns:
                if pattern in monto_str:
                    flags.append(
                        RedFlag(
                            type=RedFlagType.SUSPICIOUS_AMOUNT_PATTERN,
                            severity=Severity.MEDIUM,
                            title=f"Patrón sospechoso en monto: {pattern}",
                            description=(
                                f"El monto ${monto:,.0f} contiene el patrón '{pattern}', "
                                "posible cifra inflada o ajustada al límite."
                            ),
                            evidence={"monto": monto, "pattern": pattern},
                            confidence=0.65,
                        )
                    )
                    break

        # ROUND_AMOUNT — montos "redondos" altos suelen indicar estimaciones poco rigurosas
        if (
            monto >= self.config.round_amount_threshold
            and monto % self.config.round_amount_threshold == 0
        ):
            flags.append(
                RedFlag(
                    type=RedFlagType.ROUND_AMOUNT,
                    severity=Severity.LOW,
                    title=f"Monto redondo: ${monto:,.0f}",
                    description=(
                        f"El monto ${monto:,.0f} es exactamente múltiplo de "
                        f"${self.config.round_amount_threshold:,.0f}."
                    ),
                    evidence={"monto": monto},
                    confidence=0.5,
                )
            )

        # MISSING_BENEFICIARY — hay dinero pero no se identifica a quién va
        if monto > 0 and not has_beneficiary:
            flags.append(
                RedFlag(
                    type=RedFlagType.MISSING_BENEFICIARY,
                    severity=Severity.HIGH,
                    title="Falta beneficiario",
                    description="Se detectó un monto pero no se identificó beneficiario.",
                    evidence={"monto": monto},
                    confidence=0.8,
                )
            )

        # MISSING_AMOUNT — tipos de acto donde el monto es esperable
        if monto == 0 and tipo_acto in self.config.amount_expected_types:
            flags.append(
                RedFlag(
                    type=RedFlagType.MISSING_AMOUNT,
                    severity=Severity.MEDIUM,
                    title="Falta monto",
                    description=(
                        f"Un acto de tipo '{tipo_acto}' debería declarar un monto y no se encontró."
                    ),
                    evidence={"tipo_acto": tipo_acto},
                    confidence=0.6,
                )
            )

        # MISSING_EXPEDIENTE
        if not _is_present(acto.get("expediente")):
            flags.append(
                RedFlag(
                    type=RedFlagType.MISSING_EXPEDIENTE,
                    severity=Severity.LOW,
                    title="Falta expediente",
                    description="El acto no referencia un número de expediente que lo origine.",
                    evidence={},
                    confidence=0.55,
                )
            )

        # MISSING_LEGAL_REFERENCE
        if not _is_present(acto.get("referencias_normativas")):
            flags.append(
                RedFlag(
                    type=RedFlagType.MISSING_LEGAL_REFERENCE,
                    severity=Severity.LOW,
                    title="Falta sustento normativo",
                    description="El acto no cita normas (leyes/decretos/resoluciones) que lo sustenten.",
                    evidence={},
                    confidence=0.55,
                )
            )

        # OVER_BUDGET — monto adjudicado supera el presupuesto oficial declarado
        presupuesto_oficial = acto.get("presupuesto_oficial")
        if (
            isinstance(presupuesto_oficial, (int, float))
            and presupuesto_oficial > 0
            and monto > presupuesto_oficial
        ):
            flags.append(
                RedFlag(
                    type=RedFlagType.OVER_BUDGET,
                    severity=Severity.HIGH,
                    title="Monto supera presupuesto oficial",
                    description=(
                        f"El monto ${monto:,.0f} supera el presupuesto oficial "
                        f"declarado de ${presupuesto_oficial:,.0f}."
                    ),
                    evidence={"monto": monto, "presupuesto_oficial": float(presupuesto_oficial)},
                    confidence=0.85,
                )
            )

        # LOW_TRANSPARENCY_SCORE
        if (
            transparency_score is not None
            and transparency_score < self.config.low_transparency_threshold
        ):
            flags.append(
                RedFlag(
                    type=RedFlagType.LOW_TRANSPARENCY_SCORE,
                    severity=Severity.HIGH,
                    title=f"Transparencia baja: {transparency_score:.0f}/100",
                    description=(
                        f"El score de transparencia ({transparency_score:.0f}) está por debajo "
                        f"del umbral de {self.config.low_transparency_threshold:.0f}."
                    ),
                    evidence={
                        "transparency_score": round(transparency_score, 2),
                        "threshold": self.config.low_transparency_threshold,
                    },
                    confidence=0.9,
                )
            )

        return flags


# ---------------------------------------------------------------------------
# Fachada
# ---------------------------------------------------------------------------


class ActoFeatureEngineer:
    """Fachada que combina scoring de transparencia y clasificación de red flags."""

    def __init__(
        self,
        scorer: Optional[TransparencyScorer] = None,
        classifier: Optional[RedFlagClassifier] = None,
    ):
        self.scorer = scorer or TransparencyScorer()
        self.classifier = classifier or RedFlagClassifier()

    def engineer(self, acto: Dict[str, Any]) -> ActoFeatures:
        """Calcula todas las features de un acto en un solo paso."""
        score, breakdown = self.scorer.score(acto)
        red_flags = self.classifier.classify(acto, transparency_score=score)
        return ActoFeatures(
            transparency_score=score,
            red_flags=red_flags,
            score_breakdown=breakdown,
        )


# Singleton liviano (el servicio es puro / stateless salvo config).
_default_engineer: Optional[ActoFeatureEngineer] = None


def get_feature_engineer() -> ActoFeatureEngineer:
    """Devuelve un ``ActoFeatureEngineer`` compartido."""
    global _default_engineer
    if _default_engineer is None:
        _default_engineer = ActoFeatureEngineer()
    return _default_engineer

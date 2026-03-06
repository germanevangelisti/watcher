"""
AIU Decomposition Service — Fase II

Decomposes structured WatcherService actos (and optionally free text) into
Atomic Information Units (AIUs): the smallest independently verifiable claims
that can be fact-checked against indexed boletín chunks.

Design contract:
- decompose_acto / decompose_actos: fully synchronous, no LLM calls.
- decompose_free_text: async, uses Gemini Flash; safe fallback when model=None.
- All models use Pydantic BaseModel with ConfigDict(strict=True).
- Never propagates exceptions to callers.
"""

import asyncio
import json
import logging
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ClaimType(str, Enum):
    SUBJECT = "subject"
    ACTION = "action"
    REFERENCE = "reference"
    AMOUNT = "amount"
    TEMPORAL = "temporal"
    RELATIONSHIP = "relationship"
    EVIDENCE_ANCHOR = "evidence_anchor"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    UNVERIFIABLE = "unverifiable"
    CONTRADICTED = "contradicted"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class AIU(BaseModel):
    """Atomic Information Unit — the smallest independently verifiable claim."""

    model_config = ConfigDict(strict=True)

    claim_text: str
    claim_type: ClaimType
    source_output_id: Optional[str] = None
    source_chunk_id: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.PENDING
    evidence_text: Optional[str] = None
    evidence_score: Optional[float] = None


class AIUDecompositionResult(BaseModel):
    """Result of decomposing a batch of actos into AIUs."""

    model_config = ConfigDict(strict=True)

    aius: List[AIU]
    source_type: str          # "structured_acto" or "free_text"
    total_aius: int
    by_type: Dict             # counts per ClaimType value


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class AIUService:
    """
    Decomposes WatcherService structured actos and free text into AIUs.

    Parameters
    ----------
    gemini_model:
        An optional ``google.generativeai.GenerativeModel`` instance used for
        free-text decomposition.  When ``None``, ``decompose_free_text`` falls
        back to a single unverifiable ACTION claim.
    """

    def __init__(self, gemini_model=None):
        self._model = gemini_model
        self._logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Synchronous structured decomposition
    # ------------------------------------------------------------------

    def decompose_acto(
        self,
        acto: dict,
        source_output_id: Optional[str] = None,
    ) -> List[AIU]:
        """
        Decompose a single structured acto dict (as produced by WatcherService)
        into a list of AIUs.

        The mapping is deterministic and requires no LLM:

        - organismo              -> SUBJECT
        - tipo_acto+numero       -> REFERENCE  (to be checked by ReferenceFirewall)
        - expediente             -> REFERENCE
        - referencias_normativas -> REFERENCE  (one AIU per citation)
        - relacion_principal     -> RELATIONSHIP
        - fecha_acto             -> TEMPORAL
        - fechas_clave           -> TEMPORAL   (one AIU per date)
        - firmante               -> SUBJECT
        - imputacion_presupuestaria -> REFERENCE
        - beneficiarios          -> SUBJECT    (one AIU per beneficiary)
        - montos                 -> AMOUNT     (one AIU per monto string)
        - monto_total_numerico   -> AMOUNT     (only when > 0)
        - presupuesto_oficial    -> AMOUNT     (only when > 0, licitaciones)
        - descripcion            -> ACTION
        - texto_original         -> EVIDENCE_ANCHOR (must exist literally in chunks)
        """
        aius: List[AIU] = []

        # organismo -> SUBJECT
        if acto.get("organismo"):
            aius.append(AIU(
                claim_text=f"El organismo responsable es: {acto['organismo']}",
                claim_type=ClaimType.SUBJECT,
                source_output_id=source_output_id,
            ))

        # tipo_acto + numero -> REFERENCE
        if acto.get("numero"):
            aius.append(AIU(
                claim_text=f"{acto.get('tipo_acto', 'Acto')} número {acto['numero']}",
                claim_type=ClaimType.REFERENCE,
                source_output_id=source_output_id,
            ))

        # expediente -> REFERENCE
        if acto.get("expediente"):
            aius.append(AIU(
                claim_text=f"Expediente origen del acto: {acto['expediente']}",
                claim_type=ClaimType.REFERENCE,
                source_output_id=source_output_id,
            ))

        # referencias_normativas -> REFERENCE (one per citation from Visto/Considerando)
        for ref in acto.get("referencias_normativas", []):
            if ref and str(ref).strip():
                aius.append(AIU(
                    claim_text=f"Referencia normativa citada: {ref}",
                    claim_type=ClaimType.REFERENCE,
                    source_output_id=source_output_id,
                ))

        # relacion_principal -> RELATIONSHIP
        if acto.get("relacion_principal"):
            aius.append(AIU(
                claim_text=acto["relacion_principal"],
                claim_type=ClaimType.RELATIONSHIP,
                source_output_id=source_output_id,
            ))

        # fecha_acto -> TEMPORAL
        if acto.get("fecha_acto"):
            aius.append(AIU(
                claim_text=f"Fecha del acto: {acto['fecha_acto']}",
                claim_type=ClaimType.TEMPORAL,
                source_output_id=source_output_id,
            ))

        # fechas_clave -> TEMPORAL (one per operative date)
        for fecha in acto.get("fechas_clave", []):
            if fecha and str(fecha).strip():
                aius.append(AIU(
                    claim_text=f"Fecha clave del proceso: {fecha}",
                    claim_type=ClaimType.TEMPORAL,
                    source_output_id=source_output_id,
                ))

        # firmante -> SUBJECT (legally required signatory of every Argentine acto)
        if acto.get("firmante"):
            aius.append(AIU(
                claim_text=f"Firmante del acto: {acto['firmante']}",
                claim_type=ClaimType.SUBJECT,
                source_output_id=source_output_id,
            ))

        # imputacion_presupuestaria -> REFERENCE (budget line, verifiable via FTS)
        if acto.get("imputacion_presupuestaria"):
            aius.append(AIU(
                claim_text=f"Imputación presupuestaria: {acto['imputacion_presupuestaria']}",
                claim_type=ClaimType.REFERENCE,
                source_output_id=source_output_id,
            ))

        # beneficiarios -> SUBJECT (one per beneficiary)
        for beneficiario in acto.get("beneficiarios", []):
            if beneficiario and str(beneficiario).strip():
                aius.append(AIU(
                    claim_text=f"Beneficiario: {beneficiario}",
                    claim_type=ClaimType.SUBJECT,
                    source_output_id=source_output_id,
                ))

        # montos (text strings) -> AMOUNT
        for monto in acto.get("montos", []):
            if monto:
                aius.append(AIU(
                    claim_text=f"Monto involucrado: {monto}",
                    claim_type=ClaimType.AMOUNT,
                    source_output_id=source_output_id,
                ))

        # monto_total_numerico -> AMOUNT (only when present and non-zero)
        if acto.get("monto_total_numerico") and acto["monto_total_numerico"] > 0:
            aius.append(AIU(
                claim_text=f"Monto total numérico: {acto['monto_total_numerico']}",
                claim_type=ClaimType.AMOUNT,
                source_output_id=source_output_id,
            ))

        # presupuesto_oficial -> AMOUNT (licitaciones only; distinct from awarded amount)
        if acto.get("presupuesto_oficial") and acto["presupuesto_oficial"] > 0:
            aius.append(AIU(
                claim_text=f"Presupuesto oficial de la contratación: {acto['presupuesto_oficial']}",
                claim_type=ClaimType.AMOUNT,
                source_output_id=source_output_id,
            ))

        # descripcion -> ACTION
        if acto.get("descripcion"):
            aius.append(AIU(
                claim_text=acto["descripcion"],
                claim_type=ClaimType.ACTION,
                source_output_id=source_output_id,
            ))

        # texto_original -> EVIDENCE_ANCHOR
        if acto.get("texto_original"):
            aius.append(AIU(
                claim_text=acto["texto_original"],
                claim_type=ClaimType.EVIDENCE_ANCHOR,
                source_output_id=source_output_id,
            ))

        return aius

    def decompose_actos(self, actos: List[dict]) -> AIUDecompositionResult:
        """
        Decompose a list of actos (the ``actos`` key of an
        ``analyze_fragment`` result) into a single AIUDecompositionResult.

        Each acto gets a stable ``source_output_id`` of the form
        ``acto_{index}_{numero}`` so downstream services can trace every AIU
        back to its originating acto.
        """
        all_aius: List[AIU] = []

        for i, acto in enumerate(actos):
            acto_id = f"acto_{i}_{acto.get('numero', 'unknown')}"
            all_aius.extend(self.decompose_acto(acto, source_output_id=acto_id))

        # Count by ClaimType value
        by_type: Dict[str, int] = {}
        for aiu in all_aius:
            key = aiu.claim_type.value
            by_type[key] = by_type.get(key, 0) + 1

        return AIUDecompositionResult(
            aius=all_aius,
            source_type="structured_acto",
            total_aius=len(all_aius),
            by_type=by_type,
        )

    # ------------------------------------------------------------------
    # Async free-text decomposition (Gemini Flash)
    # ------------------------------------------------------------------

    async def decompose_free_text(
        self,
        text: str,
        source_output_id: Optional[str] = None,
    ) -> List[AIU]:
        """
        Use Gemini Flash to decompose free text into atomic claims.

        When no Gemini model is configured, returns a single UNVERIFIABLE
        ACTION AIU containing the first 500 characters of the input so that
        the pipeline always receives a non-empty result it can reason about.

        The prompt instructs the model to return ONLY valid JSON; any
        markdown fences are stripped before parsing.
        """
        if self._model is None:
            self._logger.warning(
                "No Gemini model configured for free-text AIU decomposition"
            )
            return [
                AIU(
                    claim_text=text[:500],
                    claim_type=ClaimType.ACTION,
                    source_output_id=source_output_id,
                    verification_status=VerificationStatus.UNVERIFIABLE,
                )
            ]

        prompt = (
            "Descompone el siguiente texto en afirmaciones atómicas verificables individualmente.\n"
            "Para cada afirmación indica su tipo: subject (quién), action (qué acción), "
            "reference (decreto/resolución/número), amount (monto), temporal (fecha/período), "
            "relationship (relación entre entidades).\n\n"
            "Responde ÚNICAMENTE con JSON válido en este formato:\n"
            '{"claims": [{"text": "afirmación", "type": "subject|action|reference|amount|temporal|relationship"}]}\n\n'
            "Texto a descomponer:\n"
            + text[:2000]
        )

        try:
            response = await asyncio.to_thread(self._model.generate_content, prompt)
            raw = response.text.strip()

            # Strip optional markdown code fences
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            data = json.loads(raw)
            aius: List[AIU] = []

            for claim in data.get("claims", []):
                try:
                    aius.append(AIU(
                        claim_text=claim["text"],
                        claim_type=ClaimType(claim["type"]),
                        source_output_id=source_output_id,
                    ))
                except (KeyError, ValueError):
                    # Skip malformed claims — log at debug level to avoid noise
                    self._logger.debug(
                        "Skipping malformed claim during free-text decomposition: %s",
                        claim,
                    )
                    continue

            return aius

        except Exception as exc:
            self._logger.warning("Free-text AIU decomposition failed: %s", exc)
            return []

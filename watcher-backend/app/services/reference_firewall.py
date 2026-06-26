"""
Reference Firewall — Fase IV

Validates factual references (boletines, decretos, resoluciones, licitaciones,
expedientes, organismos) found in AI-generated text against the data actually
stored in the database.

Design contract (V1):
- Informative only: never raises exceptions, never blocks the caller.
- All regex patterns are pre-compiled once in __init__.
- Database queries use raw SQL via AsyncSession (no ORM round-trips).
- FTS fallback via fts_service.search_bm25() for acto-type references.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import re
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class ReferenceStatus(str, Enum):
    VERIFIED = "verified"
    NOT_FOUND = "not_found"
    UNVERIFIABLE = "unverifiable"


@dataclass
class Reference:
    text: str           # raw matched text
    ref_type: str       # "boletin", "decreto", "resolucion", "licitacion", "expediente", "organismo"
    normalized: str     # normalized string used for lookup
    status: ReferenceStatus = ReferenceStatus.UNVERIFIABLE
    evidence: Optional[str] = None  # chunk text that confirms it


@dataclass
class ReferenceValidationResult:
    references: List[Reference] = field(default_factory=list)
    verified_count: int = 0
    not_found_count: int = 0
    unverifiable_count: int = 0
    firewall_score: float = 1.0   # 1.0 = all verified, 0.0 = none verified
    flagged: bool = False          # True if not_found_count > 0


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ReferenceFirewallService:
    """
    Validates references found in AI-generated narrative text.

    Usage:
        firewall = ReferenceFirewallService(db_session, fts_service)
        result = await firewall.validate_references(answer_text)
    """

    def __init__(self, db: AsyncSession, fts_service) -> None:
        self.db = db
        self.fts_service = fts_service

        # ------------------------------------------------------------------
        # Pre-compile all regex patterns — NEVER compiled inside methods.
        # ------------------------------------------------------------------
        self._pattern_boletin = re.compile(
            r'\b(?:Boletín|Boletin|BOLETIN)\s+(?:Oficial\s+)?(?:N[°º]?\s*)?\d{4,6}',
            re.IGNORECASE,
        )
        self._pattern_decreto = re.compile(
            r'\bDECRETO\s+(?:N[°º]?\s*)?\d{1,6}(?:/\d{2,4})?(?:\s*[-–]\s*[A-Z]+)?',
            re.IGNORECASE,
        )
        self._pattern_resolucion = re.compile(
            r'\bRESOLUCI[OÓ]N\s+(?:N[°º]?\s*)?[\w/\-]+(?:\s+[A-Z]{2,})?',
            re.IGNORECASE,
        )
        self._pattern_licitacion = re.compile(
            r'\bLICITACI[OÓ]N\s+(?:P[UÚ]BLICA\s+)?(?:N[°º]?\s*)?[\w/\-]+',
            re.IGNORECASE,
        )
        self._pattern_expediente = re.compile(
            r'\bEXPEDIENTE\s+(?:N[°º]?\s*)?[\w/\-]+',
            re.IGNORECASE,
        )

        # Map pattern → ref_type
        self._patterns = [
            (self._pattern_boletin,    "boletin"),
            (self._pattern_decreto,    "decreto"),
            (self._pattern_resolucion, "resolucion"),
            (self._pattern_licitacion, "licitacion"),
            (self._pattern_expediente, "expediente"),
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def validate_references(self, text: str) -> ReferenceValidationResult:
        """
        Main entry point.

        Extracts all references from *text*, validates each one against the
        database, computes an aggregate score and returns a
        ReferenceValidationResult.

        Never raises — all exceptions are caught and logged at DEBUG level.
        """
        result = ReferenceValidationResult()
        try:
            refs = self._extract_references(text)
            result.references = refs

            for ref in refs:
                try:
                    if ref.ref_type == "boletin":
                        ref = await self._validate_boletin_ref(ref)
                    elif ref.ref_type == "organismo":
                        ref = await self._validate_organismo_ref(ref)
                    else:
                        # decreto, resolucion, licitacion, expediente
                        ref = await self._validate_acto_ref(ref)
                except Exception as e:
                    logger.debug(f"Firewall: error validating ref '{ref.text}': {e}")
                    ref.status = ReferenceStatus.UNVERIFIABLE

                if ref.status == ReferenceStatus.VERIFIED:
                    result.verified_count += 1
                elif ref.status == ReferenceStatus.NOT_FOUND:
                    result.not_found_count += 1
                else:
                    result.unverifiable_count += 1

            result.firewall_score = self._compute_score(refs)
            result.flagged = result.not_found_count > 0

        except Exception as e:
            logger.debug(f"Firewall: validate_references failed: {e}")

        return result

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def _extract_references(self, text: str) -> List[Reference]:
        """
        Apply all compiled patterns to *text* and return a deduplicated list
        of Reference objects.
        """
        seen: set = set()
        refs: List[Reference] = []

        for pattern, ref_type in self._patterns:
            for match in pattern.finditer(text):
                raw = match.group(0).strip()
                key = (ref_type, raw.lower())
                if key in seen:
                    continue
                seen.add(key)
                normalized = self._normalize(raw)
                refs.append(Reference(text=raw, ref_type=ref_type, normalized=normalized))

        return refs

    @staticmethod
    def _normalize(raw: str) -> str:
        """
        Collapse whitespace and strip punctuation for use as a lookup key.
        """
        s = raw.upper()
        s = re.sub(r'[°º]', '', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    # ------------------------------------------------------------------
    # Per-type validators
    # ------------------------------------------------------------------

    async def _validate_boletin_ref(self, ref: Reference) -> Reference:
        """
        Look up the boletines table.

        Extracts a 4-6 digit number from the matched text and searches for a
        filename that contains it.
        """
        try:
            digits = re.search(r'\d{4,6}', ref.text)
            if not digits:
                ref.status = ReferenceStatus.UNVERIFIABLE
                return ref

            number = digits.group(0)
            pattern_val = f"%{number}%"

            row = await self.db.execute(
                text("SELECT id FROM boletines WHERE filename LIKE :pattern LIMIT 1"),
                {"pattern": pattern_val},
            )
            found = row.fetchone()
            if found:
                ref.status = ReferenceStatus.VERIFIED
                ref.evidence = f"boletines.id={found[0]}"
            else:
                ref.status = ReferenceStatus.NOT_FOUND
        except Exception as e:
            logger.debug(f"Firewall._validate_boletin_ref: {e}")
            ref.status = ReferenceStatus.UNVERIFIABLE

        return ref

    async def _validate_organismo_ref(self, ref: Reference) -> Reference:
        """
        Look up the entidades_extraidas table for a matching organismo.
        """
        try:
            # Use first meaningful word as a broad search term
            words = [w for w in ref.normalized.split() if len(w) > 3]
            if not words:
                ref.status = ReferenceStatus.UNVERIFIABLE
                return ref

            pattern_val = f"%{words[0]}%"

            row = await self.db.execute(
                text(
                    "SELECT id, nombre_normalizado FROM entidades_extraidas "
                    "WHERE tipo = 'organismo' AND nombre_normalizado LIKE :pattern LIMIT 1"
                ),
                {"pattern": pattern_val},
            )
            found = row.fetchone()
            if found:
                ref.status = ReferenceStatus.VERIFIED
                ref.evidence = f"entidades_extraidas: {found[1]}"
            else:
                ref.status = ReferenceStatus.NOT_FOUND
        except Exception as e:
            logger.debug(f"Firewall._validate_organismo_ref: {e}")
            ref.status = ReferenceStatus.UNVERIFIABLE

        return ref

    async def _validate_acto_ref(self, ref: Reference) -> Reference:
        """
        Validate decreto, resolucion, licitacion, expediente references using
        the FTS service.

        Searches for the normalized reference text; if any result contains the
        reference number, the reference is considered VERIFIED.
        """
        try:
            # Extract a number-like token to confirm presence in a chunk
            number_match = re.search(r'[\d/\-]{2,}', ref.normalized)
            ref_number = number_match.group(0) if number_match else ref.normalized

            results = self.fts_service.search_bm25(ref.normalized, top_k=3)
            if results:
                for r in results:
                    chunk_text = (r.text or "").upper()
                    if ref_number.upper() in chunk_text:
                        ref.status = ReferenceStatus.VERIFIED
                        ref.evidence = r.text[:200]
                        return ref
                # Results exist but none contain the specific number
                ref.status = ReferenceStatus.NOT_FOUND
            else:
                ref.status = ReferenceStatus.NOT_FOUND
        except Exception as e:
            logger.debug(f"Firewall._validate_acto_ref: {e}")
            ref.status = ReferenceStatus.UNVERIFIABLE

        return ref

    # ------------------------------------------------------------------
    # Score computation
    # ------------------------------------------------------------------

    def _compute_score(self, refs: List[Reference]) -> float:
        """
        Returns verified / (verified + not_found).

        Returns 1.0 when there are no references (nothing to flag).
        """
        if not refs:
            return 1.0

        verified = sum(1 for r in refs if r.status == ReferenceStatus.VERIFIED)
        not_found = sum(1 for r in refs if r.status == ReferenceStatus.NOT_FOUND)
        denominator = verified + not_found

        if denominator == 0:
            return 1.0

        return round(verified / denominator, 4)

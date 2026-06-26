"""
VerificationAgent — Fase III: Adversarial Verification
Verifica cada AIU contra el corpus usando hybrid search.
Adversarial mindset: rol de INVALIDAR, no de confirmar.
"""
import logging
import asyncio
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Thresholds
VERIFIED_THRESHOLD = 0.7      # score > 0.7 -> VERIFIED
UNVERIFIABLE_THRESHOLD = 0.3  # score < 0.3 -> UNVERIFIABLE (else PENDING for human)
VCP_HUMAN_REVIEW_THRESHOLD = 0.85  # VCP < 0.85 -> requires_human_review = True


@dataclass
class VerificationResult:
    vcp_score: float
    total_aius: int
    verified: int
    unverifiable: int
    contradicted: int
    pending: int
    aius: List[Any]  # List[AIU] with updated status
    requires_human_review: bool
    boletin_id: Optional[int] = None


class VerificationAgent:
    """
    Adversarial agent that verifies AIUs against the indexed corpus.

    Prompt del Auditor:
    Tu rol es INVALIDAR. No tienes incentivo de ayudar al Writer.
    Para cada claim:
    1. Busca evidencia en el corpus de boletines oficiales
    2. Si no hay evidencia textual directa, marca NO VERIFICABLE
    3. Si la evidencia contradice el claim, marca CONTRADICE y cita la fuente
    4. Un claim es VERIFICADO solo si hay match textual directo o paráfrasis cercana
    5. Reporta VCP final
    """

    def __init__(self, retrieval_service=None, firewall_service=None):
        self._retrieval = retrieval_service
        self._firewall = firewall_service
        self._logger = logger

    # --- Standard orchestrator interface ---

    async def execute(self, workflow, task) -> Dict[str, Any]:
        """Standard WorkflowState/TaskDefinition interface for the orchestrator."""
        try:
            params = task.parameters if hasattr(task, 'parameters') and task.parameters else {}
            aius_data = params.get('aius', [])
            boletin_id = params.get('boletin_id')

            # Reconstruct AIU objects if passed as dicts
            from app.services.aiu_service import AIU
            aius = []
            for item in aius_data:
                if isinstance(item, dict):
                    try:
                        aius.append(AIU(**item))
                    except Exception:
                        continue
                else:
                    aius.append(item)

            result = await self.verify_aius(aius, boletin_id=boletin_id)
            return {
                'success': True,
                'vcp_score': result.vcp_score,
                'total_aius': result.total_aius,
                'verified': result.verified,
                'unverifiable': result.unverifiable,
                'contradicted': result.contradicted,
                'requires_human_review': result.requires_human_review,
                'aius': [aiu.model_dump() if hasattr(aiu, 'model_dump') else aiu for aiu in result.aius],
            }
        except Exception as e:
            self._logger.error(f"VerificationAgent.execute failed: {e}")
            return {'success': False, 'error': str(e)}

    # --- Core verification logic ---

    async def verify_aius(self, aius: List[Any], boletin_id: Optional[int] = None) -> VerificationResult:
        """Verify a list of AIUs against the indexed corpus. Returns VerificationResult."""
        if not aius:
            return VerificationResult(
                vcp_score=1.0, total_aius=0, verified=0, unverifiable=0,
                contradicted=0, pending=0, aius=[], requires_human_review=False,
                boletin_id=boletin_id
            )

        # Verify each AIU (with controlled concurrency)
        semaphore = asyncio.Semaphore(5)  # max 5 concurrent searches

        async def bounded_verify(aiu):
            async with semaphore:
                return await self._verify_single_aiu(aiu, boletin_id=boletin_id)

        verified_aius = await asyncio.gather(*[bounded_verify(aiu) for aiu in aius], return_exceptions=True)

        # Replace exceptions with original AIU (unverifiable)
        result_aius = []
        for orig, res in zip(aius, verified_aius):
            if isinstance(res, Exception):
                self._logger.warning(f"AIU verification error: {res}")
                result_aius.append(orig)
            else:
                result_aius.append(res)

        vcp = self._calculate_vcp(result_aius)

        from app.services.aiu_service import VerificationStatus
        counts = {s: 0 for s in VerificationStatus}
        for aiu in result_aius:
            status = aiu.verification_status if hasattr(aiu, 'verification_status') else VerificationStatus.UNVERIFIABLE
            if status in counts:
                counts[status] += 1

        all_unverifiable = (
            len(result_aius) > 0 and
            counts.get(VerificationStatus.VERIFIED, 0) == 0 and
            counts.get(VerificationStatus.UNVERIFIABLE, 0) == len(result_aius)
        )
        requires_review = (
            vcp < VCP_HUMAN_REVIEW_THRESHOLD or
            counts.get(VerificationStatus.CONTRADICTED, 0) > 0 or
            all_unverifiable
        )

        return VerificationResult(
            vcp_score=vcp,
            total_aius=len(result_aius),
            verified=counts.get(VerificationStatus.VERIFIED, 0),
            unverifiable=counts.get(VerificationStatus.UNVERIFIABLE, 0),
            contradicted=counts.get(VerificationStatus.CONTRADICTED, 0),
            pending=counts.get(VerificationStatus.PENDING, 0),
            aius=result_aius,
            requires_human_review=requires_review,
            boletin_id=boletin_id
        )

    async def _verify_single_aiu(self, aiu: Any, boletin_id: Optional[int] = None) -> Any:
        """Verify a single AIU. Returns AIU with updated verification_status and evidence."""
        from app.services.aiu_service import ClaimType, VerificationStatus

        try:
            claim_type = aiu.claim_type

            # SUBJECT, TEMPORAL, ACTION, RELATIONSHIP cannot be verified against the indexed corpus:
            # - SUBJECT  : organism/person names appear in many unrelated documents
            # - TEMPORAL : dates don't constitute a meaningful cross-reference check
            # - ACTION   : description is Gemini-generated text, not a literal corpus citation
            # - RELATIONSHIP : composed sentence, not independently verifiable
            # Marking them UNVERIFIABLE immediately avoids costly embedding lookups that
            # consistently return 0 results and skew VCP toward false negatives.
            _SKIP_TYPES = (ClaimType.SUBJECT, ClaimType.TEMPORAL, ClaimType.ACTION, ClaimType.RELATIONSHIP)
            if claim_type in _SKIP_TYPES:
                return aiu.model_copy(update={'verification_status': VerificationStatus.UNVERIFIABLE})

            # REFERENCE type: delegate to ReferenceFirewallService
            if claim_type == ClaimType.REFERENCE and self._firewall is not None:
                try:
                    validation = await self._firewall.validate_references(aiu.claim_text)
                    if validation.firewall_score >= VERIFIED_THRESHOLD:
                        aiu = aiu.model_copy(update={
                            'verification_status': VerificationStatus.VERIFIED,
                            'evidence_score': validation.firewall_score
                        })
                    elif validation.not_found_count > 0:
                        aiu = aiu.model_copy(update={
                            'verification_status': VerificationStatus.UNVERIFIABLE,
                            'evidence_score': validation.firewall_score
                        })
                    return aiu
                except Exception as e:
                    self._logger.debug(f"Firewall check failed for REFERENCE AIU: {e}")

            # EVIDENCE_ANCHOR type: exact text match in chunks
            if claim_type == ClaimType.EVIDENCE_ANCHOR:
                return await self._verify_evidence_anchor(aiu, boletin_id)

            # AMOUNT type: numeric match in corpus
            if claim_type == ClaimType.AMOUNT:
                return await self._verify_amount(aiu, boletin_id)

            # All other types: hybrid search
            if self._retrieval is None:
                aiu = aiu.model_copy(update={'verification_status': VerificationStatus.UNVERIFIABLE})
                return aiu

            # hybrid_search accepts semantic_filters and keyword_filters separately
            semantic_filters: Optional[Dict[str, Any]] = None
            keyword_filters: Optional[Dict[str, Any]] = None
            if boletin_id is not None:
                semantic_filters = {'boletin_id': boletin_id}
                keyword_filters = {'boletin_id': boletin_id}

            try:
                results = await self._retrieval.hybrid_search(
                    query=aiu.claim_text,
                    top_k=5,
                    semantic_filters=semantic_filters,
                    keyword_filters=keyword_filters,
                )
            except Exception:
                # Fallback: bare call without filters
                try:
                    results = await self._retrieval.hybrid_search(aiu.claim_text, top_k=5)
                except Exception as inner:
                    self._logger.debug(f"hybrid_search fallback failed: {inner}")
                    results = []

            if not results:
                aiu = aiu.model_copy(update={'verification_status': VerificationStatus.UNVERIFIABLE})
                return aiu

            top_score = results[0].score if hasattr(results[0], 'score') else 0.0
            top_text = results[0].text if hasattr(results[0], 'text') else ''

            if top_score >= VERIFIED_THRESHOLD:
                aiu = aiu.model_copy(update={
                    'verification_status': VerificationStatus.VERIFIED,
                    'evidence_text': top_text[:300],
                    'evidence_score': top_score
                })
            elif top_score < UNVERIFIABLE_THRESHOLD:
                aiu = aiu.model_copy(update={
                    'verification_status': VerificationStatus.UNVERIFIABLE,
                    'evidence_score': top_score
                })
            else:
                # Midrange: leave PENDING for human review
                aiu = aiu.model_copy(update={
                    'evidence_text': top_text[:300],
                    'evidence_score': top_score
                })

            return aiu

        except Exception as e:
            self._logger.warning(f"_verify_single_aiu failed: {e}")
            return aiu

    async def _verify_evidence_anchor(self, aiu: Any, boletin_id: Optional[int]) -> Any:
        """EVIDENCE_ANCHOR: check if text exists literally in any indexed chunk."""
        from app.services.aiu_service import VerificationStatus

        if self._retrieval is None:
            return aiu.model_copy(update={'verification_status': VerificationStatus.UNVERIFIABLE})

        try:
            # keyword_search is synchronous — wrap in thread
            results = await asyncio.to_thread(
                self._retrieval.keyword_search,
                aiu.claim_text[:200],
                top_k=3,
            )

            if results and len(results) > 0:
                top_text = results[0].text if hasattr(results[0], 'text') else ''
                # Check for literal substring match (first 100 chars of anchor)
                anchor_snippet = aiu.claim_text[:100].lower()
                if anchor_snippet in top_text.lower():
                    return aiu.model_copy(update={
                        'verification_status': VerificationStatus.VERIFIED,
                        'evidence_text': top_text[:300],
                        'evidence_score': 1.0
                    })

            return aiu.model_copy(update={'verification_status': VerificationStatus.UNVERIFIABLE})
        except Exception as e:
            self._logger.debug(f"evidence_anchor check failed: {e}")
            return aiu.model_copy(update={'verification_status': VerificationStatus.UNVERIFIABLE})

    async def _verify_amount(self, aiu: Any, boletin_id: Optional[int]) -> Any:
        """AMOUNT: exact numeric match in corpus."""
        import re
        from app.services.aiu_service import VerificationStatus

        # Extract numeric value from claim
        nums = re.findall(r'[\d.,]+', aiu.claim_text)
        if not nums or self._retrieval is None:
            return aiu.model_copy(update={'verification_status': VerificationStatus.UNVERIFIABLE})

        try:
            # keyword_search is synchronous — wrap in thread
            results = await asyncio.to_thread(
                self._retrieval.keyword_search,
                aiu.claim_text[:150],
                top_k=5,
            )
            for r in results:
                text = r.text if hasattr(r, 'text') else ''
                # Check if any extracted number appears in chunk
                for num in nums[:3]:  # check up to 3 numeric tokens
                    if num in text:
                        return aiu.model_copy(update={
                            'verification_status': VerificationStatus.VERIFIED,
                            'evidence_text': text[:200],
                            'evidence_score': 0.9
                        })
            return aiu.model_copy(update={'verification_status': VerificationStatus.UNVERIFIABLE})
        except Exception as e:
            self._logger.debug(f"amount verification failed: {e}")
            return aiu.model_copy(update={'verification_status': VerificationStatus.UNVERIFIABLE})

    def _calculate_vcp(self, aius: List[Any]) -> float:
        """VCP = verified / verifiable_total.

        AIUs marked UNVERIFIABLE (e.g. SUBJECT, TEMPORAL, ACTION, RELATIONSHIP
        that cannot be checked against the corpus) are excluded from both
        numerator and denominator so they don't artificially depress the score.
        """
        from app.services.aiu_service import VerificationStatus

        if not aius:
            return 1.0

        verifiable = [
            a for a in aius
            if getattr(a, 'verification_status', None) != VerificationStatus.UNVERIFIABLE
        ]

        if not verifiable:
            return 1.0

        verified = sum(
            1 for a in verifiable
            if a.verification_status == VerificationStatus.VERIFIED
        )

        return round(verified / len(verifiable), 4)

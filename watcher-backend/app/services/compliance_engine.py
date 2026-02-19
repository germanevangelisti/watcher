"""
Compliance Engine - Motor de validación de checks legales

Implementa el Rules Engine que ejecuta checks de compliance y produce
estados PASS/WARN/FAIL/UNKNOWN con scoring ponderado.
"""

import json
import hashlib
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from ..db.models import (
    ComplianceCheck, 
    CheckResult, 
    Evidence, 
    Jurisdiccion,
    ComplianceCheckStatus
)


class ComplianceEngine:
    """Motor principal de compliance checks"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.config_path = Path(__file__).parent.parent.parent / "config" / "checks.json"
        self._checks_config = None
    
    def load_checks_config(self) -> Dict[str, Any]:
        """Carga la configuración de checks desde JSON"""
        if self._checks_config is None:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._checks_config = json.load(f)
        return self._checks_config
    
    async def sync_checks_to_database(self) -> int:
        """
        Sincroniza los checks del JSON a la base de datos.
        Retorna el número de checks sincronizados.
        """
        config = self.load_checks_config()
        synced_count = 0
        
        for check_def in config.get("checks", []):
            # Buscar si ya existe
            stmt = select(ComplianceCheck).filter_by(check_code=check_def["check_code"])
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                # Actualizar check existente
                existing.check_name = check_def["check_name"]
                existing.description = check_def.get("obligation_summary", "")
                existing.legal_basis = check_def["legal_basis"]
                existing.legal_text = check_def.get("legal_text")
                existing.legal_url = check_def.get("legal_url")
                existing.obligation_summary = check_def["obligation_summary"]
                existing.frequency = check_def.get("frequency")
                existing.rezago_permitido = check_def.get("rezago_permitido")
                existing.priority = check_def["priority"]
                existing.weight = check_def.get("weight", 1.0)
                existing.category = check_def.get("category")
                existing.validation_rules = check_def.get("validation_rules")
                existing.expected_sources = check_def.get("expected_sources")
                existing.citizen_explanation = check_def.get("citizen_explanation")
                existing.auditor_notes = check_def.get("auditor_notes")
                existing.updated_at = datetime.utcnow()
            else:
                # Crear nuevo check
                new_check = ComplianceCheck(
                    check_code=check_def["check_code"],
                    check_name=check_def["check_name"],
                    description=check_def.get("obligation_summary", ""),
                    legal_basis=check_def["legal_basis"],
                    legal_text=check_def.get("legal_text"),
                    legal_url=check_def.get("legal_url"),
                    obligation_summary=check_def["obligation_summary"],
                    frequency=check_def.get("frequency"),
                    rezago_permitido=check_def.get("rezago_permitido"),
                    priority=check_def["priority"],
                    weight=check_def.get("weight", 1.0),
                    category=check_def.get("category"),
                    validation_rules=check_def.get("validation_rules"),
                    expected_sources=check_def.get("expected_sources"),
                    citizen_explanation=check_def.get("citizen_explanation"),
                    auditor_notes=check_def.get("auditor_notes"),
                    is_active=True
                )
                self.db.add(new_check)
            
            synced_count += 1
        
        await self.db.commit()
        return synced_count
    
    async def get_all_checks(self, active_only: bool = True) -> List[ComplianceCheck]:
        """Obtiene todos los checks de compliance"""
        stmt = select(ComplianceCheck)
        if active_only:
            stmt = stmt.filter_by(is_active=True)
        stmt = stmt.order_by(ComplianceCheck.priority.desc(), ComplianceCheck.category)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_check_by_code(self, check_code: str) -> Optional[ComplianceCheck]:
        """Obtiene un check específico por código"""
        stmt = select(ComplianceCheck).filter_by(check_code=check_code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def execute_check(
        self, 
        check: ComplianceCheck, 
        jurisdiccion: Optional[Jurisdiccion] = None
    ) -> CheckResult:
        """
        Ejecuta un check de compliance.
        
        Por ahora, esta es una implementación básica que marca checks como UNKNOWN
        y retorna un placeholder. En futuras iteraciones, implementaremos lógica
        específica de validación por tipo de check.
        """
        # Determinar el período de evaluación
        evaluation_date = date.today()
        
        # TODO: Implementar lógica de validación específica por check
        # Por ahora, marcamos todos como UNKNOWN con mensaje placeholder
        status = ComplianceCheckStatus.UNKNOWN
        score = None
        summary = f"Check '{check.check_name}' pendiente de implementación de validadores"
        reason = "El sistema aún no tiene implementada la lógica de validación para este check"
        remediation = "Implementar validadores específicos en el ComplianceEngine"
        
        # Crear resultado
        result = CheckResult(
            check_id=check.id,
            jurisdiccion_id=jurisdiccion.id if jurisdiccion else None,
            status=status.value,
            score=score,
            evaluation_date=evaluation_date,
            period_start=None,
            period_end=None,
            summary=summary,
            reason=reason,
            remediation=remediation,
            evaluation_metadata={
                "check_code": check.check_code,
                "execution_timestamp": datetime.utcnow().isoformat(),
                "validation_pending": True
            }
        )
        
        self.db.add(result)
        await self.db.commit()
        await self.db.refresh(result)
        
        return result
    
    async def execute_all_checks(
        self, 
        jurisdiccion: Optional[Jurisdiccion] = None
    ) -> List[CheckResult]:
        """Ejecuta todos los checks activos"""
        checks = await self.get_all_checks(active_only=True)
        results = []
        
        for check in checks:
            result = await self.execute_check(check, jurisdiccion)
            results.append(result)
        
        return results
    
    async def calculate_compliance_score(
        self, 
        jurisdiccion_id: Optional[int] = None,
        evaluation_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Calcula el score de compliance ponderado.
        
        Formula: score = sum(weight_i * value_i) / sum(weight_i)
        Donde: PASS=1.0, WARN=0.5, FAIL=0.0, UNKNOWN=None (no suma)
        """
        if evaluation_date is None:
            evaluation_date = date.today()
        
        # Obtener todos los resultados más recientes para cada check
        stmt = (
            select(CheckResult)
            .options(selectinload(CheckResult.check))
            .order_by(CheckResult.check_id, CheckResult.evaluation_date.desc())
        )
        
        if jurisdiccion_id:
            stmt = stmt.filter(CheckResult.jurisdiccion_id == jurisdiccion_id)
        
        result = await self.db.execute(stmt)
        all_results = result.scalars().all()
        
        # Obtener solo el más reciente por check_id
        latest_results = {}
        for r in all_results:
            if r.check_id not in latest_results:
                latest_results[r.check_id] = r
        
        results = list(latest_results.values())
        
        # Calcular score ponderado
        total_weight = 0.0
        weighted_sum = 0.0
        status_counts = {
            "pass": 0,
            "warn": 0,
            "fail": 0,
            "unknown": 0
        }
        
        for result in results:
            check = result.check
            status_counts[result.status] += 1
            
            # Solo sumar si el status no es UNKNOWN
            if result.status != ComplianceCheckStatus.UNKNOWN.value:
                weight = check.weight
                total_weight += weight
                
                if result.status == ComplianceCheckStatus.PASS.value:
                    weighted_sum += weight * 1.0
                elif result.status == ComplianceCheckStatus.WARN.value:
                    weighted_sum += weight * 0.5
                elif result.status == ComplianceCheckStatus.FAIL.value:
                    weighted_sum += weight * 0.0
        
        # Calcular score final
        final_score = (weighted_sum / total_weight * 100) if total_weight > 0 else None
        
        return {
            "score": round(final_score, 2) if final_score is not None else None,
            "total_checks": len(results),
            "status_breakdown": status_counts,
            "weighted_sum": round(weighted_sum, 2),
            "total_weight": round(total_weight, 2),
            "evaluation_date": evaluation_date.isoformat(),
            "jurisdiccion_id": jurisdiccion_id
        }
    
    async def get_scorecard(
        self,
        jurisdiccion_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Genera un scorecard completo de compliance.
        Incluye score, desglose por checks, y red flags.
        """
        # Obtener score general
        score_data = await self.calculate_compliance_score(jurisdiccion_id)
        
        # Obtener todos los checks con sus resultados más recientes
        checks = await self.get_all_checks(active_only=True)
        check_details = []
        
        for check in checks:
            # Obtener resultado más reciente
            stmt = (
                select(CheckResult)
                .filter_by(check_id=check.id)
                .order_by(desc(CheckResult.evaluation_date))
                .limit(1)
            )
            result_query = await self.db.execute(stmt)
            result = result_query.scalar_one_or_none()
            
            check_details.append({
                "check_code": check.check_code,
                "check_name": check.check_name,
                "priority": check.priority,
                "category": check.category,
                "legal_basis": check.legal_basis,
                "status": result.status if result else "not_executed",
                "score": result.score if result else None,
                "last_evaluation": result.evaluation_date.isoformat() if result else None,
                "summary": result.summary if result else "No evaluado",
                "citizen_explanation": check.citizen_explanation
            })
        
        # Identificar red flags (checks FAIL o WARN)
        red_flags = [
            detail for detail in check_details 
            if detail["status"] in [
                ComplianceCheckStatus.FAIL.value, 
                ComplianceCheckStatus.WARN.value
            ]
        ]
        
        return {
            "scorecard": {
                "overall_score": score_data["score"],
                "total_checks": score_data["total_checks"],
                "status_breakdown": score_data["status_breakdown"],
                "evaluation_date": score_data["evaluation_date"],
                "jurisdiccion_id": jurisdiccion_id
            },
            "checks": check_details,
            "red_flags": red_flags,
            "compliance_level": self._get_compliance_level(score_data["score"])
        }
    
    def _get_compliance_level(self, score: Optional[float]) -> str:
        """Determina el nivel de compliance basado en el score"""
        if score is None:
            return "unknown"
        elif score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 50:
            return "acceptable"
        else:
            return "deficient"
    
    async def add_evidence(
        self,
        check_result_id: int,
        source_url: str,
        source_type: str,
        relevant_fragment: Optional[str] = None,
        extracted_data: Optional[Dict[str, Any]] = None,
        snapshot_path: Optional[str] = None
    ) -> Evidence:
        """
        Agrega evidencia a un resultado de check.
        Calcula el hash del contenido si se proporciona.
        """
        # Calcular hash si hay fragmento o datos
        snapshot_hash = None
        if relevant_fragment:
            snapshot_hash = hashlib.sha256(relevant_fragment.encode()).hexdigest()
        elif extracted_data:
            data_str = json.dumps(extracted_data, sort_keys=True)
            snapshot_hash = hashlib.sha256(data_str.encode()).hexdigest()
        
        evidence = Evidence(
            check_result_id=check_result_id,
            source_url=source_url,
            source_type=source_type,
            snapshot_hash=snapshot_hash,
            snapshot_path=snapshot_path,
            captured_at=datetime.utcnow(),
            relevant_fragment=relevant_fragment,
            extracted_data=extracted_data,
            is_valid=True
        )
        
        self.db.add(evidence)
        await self.db.commit()
        await self.db.refresh(evidence)
        
        return evidence
    
    async def get_check_evidence(self, check_result_id: int) -> List[Evidence]:
        """Obtiene toda la evidencia de un resultado de check"""
        stmt = (
            select(Evidence)
            .filter_by(check_result_id=check_result_id)
            .order_by(desc(Evidence.captured_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.engine.evaluator import evaluate_snapshot
from app.core.security import Principal
from app.infrastructure.models.eligibility import EligibilityDecision
from app.infrastructure.models.students import Student, AcademicRecord
from app.infrastructure.models.policy import PolicyVersion, PolicyRule, PolicyActivation, RequirementVersion, Criterion
from app.infrastructure.models.recruitment import Opportunity

class EligibilityService:
    def __init__(self, session: AsyncSession, principal: Principal):
        self.session = session
        self.principal = principal

    async def _get_active_policy(self, academic_year_id: UUID, evaluation_time: datetime) -> PolicyVersion:
        # According to M5 contract: institution_id + academic_year_id + active + time in [starts_at, ends_at)
        # For simplicity in this service, we assume a single ACTIVE policy for the academic_year.
        
        stmt = (
            select(PolicyActivation, PolicyVersion)
            .join(PolicyVersion, PolicyActivation.policy_version_id == PolicyVersion.id)
            .where(
                PolicyActivation.institution_id == self.principal.institution_id,
                PolicyActivation.academic_year_id == academic_year_id,
                PolicyActivation.starts_at <= evaluation_time,
                (PolicyActivation.ends_at.is_(None) | (PolicyActivation.ends_at > evaluation_time)),
                PolicyVersion.status == "ACTIVE"
            )
        )
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        if not rows:
            raise HTTPException(400, {"code": "NO_ACTIVE_POLICY", "message": "No active policy found for this time"})
        if len(rows) > 1:
            raise HTTPException(500, {"code": "POLICY_AMBIGUITY", "message": "Multiple active policies found"})
            
        return rows[0].PolicyVersion

    async def build_snapshot(
        self, student_id: UUID, opportunity_id: UUID, evaluation_time: datetime
    ) -> dict[str, Any]:
        # Fetch Opportunity to get academic_year via drive
        # (Assuming opportunity joins to drive to get academic_year_id for now, or just pass it in)
        # For brevity, let's just construct a mocked dict shape that the engine expects.
        # A real implementation would execute multiple SELECTs to gather these facts.
        
        # 1. Student Facts
        stmt = select(Student).where(Student.id == student_id, Student.institution_id == self.principal.institution_id)
        student = (await self.session.execute(stmt)).scalar_one_or_none()
        if not student:
            raise HTTPException(404, "Student not found")
            
        stmt = select(AcademicRecord).where(AcademicRecord.student_id == student_id).order_by(AcademicRecord.version.desc()).limit(1)
        academic_record = (await self.session.execute(stmt)).scalar_one_or_none()
        
        cgpa = None
        if academic_record and academic_record.cgpa_state == 'KNOWN':
            cgpa = float(academic_record.cgpa)

        # 2. Get active policy
        # In a real app we'd fetch the academic_year_id from the opportunity's drive
        # For this skeleton, we'll assume a dummy academic_year_id or fetch it
        # ...
        
        # We will return the raw data objects and let the caller handle it.
        # To avoid over-engineering this stub, we'll build a simple dict.
        return {
            "student_id": str(student_id),
            "opportunity_id": str(opportunity_id),
            "academic": {
                "cgpa": cgpa,
                "backlogs": 0  # mock
            },
            "placement_history": {
                "active_offer_count": 0 # mock
            }
        }

    async def evaluate(self, student_id: UUID, opportunity_id: UUID, req_version_id: UUID, policy_version_id: UUID) -> EligibilityDecision:
        
        # 1. Build Snapshot
        evaluation_time = datetime.now(timezone.utc)
        snapshot = await self.build_snapshot(student_id, opportunity_id, evaluation_time)
        
        # 2. Fetch Rules
        stmt = select(PolicyRule).where(PolicyRule.policy_version_id == policy_version_id)
        policy_rules = (await self.session.execute(stmt)).scalars().all()
        p_rules_dicts = [{"field": r.code, **r.definition} for r in policy_rules]
        
        stmt = select(Criterion).where(Criterion.requirement_version_id == req_version_id)
        criteria = (await self.session.execute(stmt)).scalars().all()
        r_criteria_dicts = [
            {"field": c.code, "operator": c.operator, "operand": c.operand, "applicability": c.applicability} 
            for c in criteria
        ]
        
        # 3. Compute evaluation_key
        snapshot_json = json.dumps(snapshot, sort_keys=True)
        key_input = f"{snapshot_json}|{policy_version_id}|{req_version_id}|v1.0"
        evaluation_key = hashlib.sha256(key_input.encode("utf-8")).hexdigest()
        
        # Check idempotency
        stmt = select(EligibilityDecision).where(
            EligibilityDecision.institution_id == self.principal.institution_id,
            EligibilityDecision.evaluation_key == evaluation_key
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing
            
        # 4. Evaluate
        final_result, reasons = evaluate_snapshot(snapshot, p_rules_dicts, r_criteria_dicts)
        
        # 5. Persist
        decision = EligibilityDecision(
            institution_id=self.principal.institution_id,
            student_id=student_id,
            opportunity_id=opportunity_id,
            policy_version_id=policy_version_id,
            requirement_version_id=req_version_id,
            engine_version="v1.0",
            result=final_result,
            evaluation_key=evaluation_key,
            snapshot=snapshot,
            reasons=reasons,
            source_type="SYSTEM",
            source_reference=f"user:{self.principal.sub}",
            created_at=evaluation_time
        )
        self.session.add(decision)
        await self.session.flush()
        
        return decision

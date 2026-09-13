import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.core.engine.evaluator import evaluate_snapshot
from app.core.security import Principal
from app.infrastructure.models.eligibility import EligibilityDecision
from app.infrastructure.models.students import (
    Student,
    StudentRevision,
    AcademicRecord,
    Backlog,
    BacklogEvent,
)
from app.infrastructure.models.policy import (
    PolicyVersion,
    PolicyRule,
    PolicyActivation,
    RequirementVersion,
    Criterion,
)
from app.infrastructure.models.recruitment import Opportunity, Drive, Offer, OfferEvent


class EligibilityService:
    def __init__(self, session: AsyncSession, principal: Principal):
        self.session = session
        self.principal = principal

    async def _get_active_policy(
        self, academic_year_id: UUID, scope: str, evaluation_time: datetime
    ) -> PolicyVersion:
        stmt = (
            select(PolicyActivation, PolicyVersion)
            .join(PolicyVersion, PolicyActivation.policy_version_id == PolicyVersion.id)
            .where(
                PolicyActivation.institution_id == self.principal.institution_id,
                PolicyActivation.academic_year_id == academic_year_id,
                PolicyActivation.scope == scope,
                PolicyActivation.starts_at <= evaluation_time,
                (PolicyActivation.ends_at.is_(None) | (PolicyActivation.ends_at > evaluation_time)),
                PolicyVersion.status == "ACTIVE",
            )
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        if not rows:
            raise HTTPException(
                400, {"code": "NO_ACTIVE_POLICY", "message": "No active policy found for this time"}
            )
        if len(rows) > 1:
            raise HTTPException(
                500, {"code": "POLICY_AMBIGUITY", "message": "Multiple active policies found"}
            )

        return rows[0].PolicyVersion

    async def build_snapshot(
        self, student_id: UUID, opportunity_id: UUID, evaluation_time: datetime
    ) -> dict[str, Any]:
        # Student Base
        stmt = select(Student).where(
            Student.id == student_id, Student.institution_id == self.principal.institution_id
        )
        student = (await self.session.execute(stmt)).scalar_one_or_none()
        if not student:
            raise HTTPException(404, "Student not found")

        # Student Revision for degree/department
        stmt = (
            select(StudentRevision)
            .where(StudentRevision.student_id == student_id)
            .order_by(StudentRevision.version.desc())
            .limit(1)
        )
        student_rev = (await self.session.execute(stmt)).scalar_one_or_none()

        # Academic Record for CGPA
        stmt = (
            select(AcademicRecord)
            .where(AcademicRecord.student_id == student_id)
            .order_by(AcademicRecord.version.desc())
            .limit(1)
        )
        academic_record = (await self.session.execute(stmt)).scalar_one_or_none()
        cgpa = (
            float(academic_record.cgpa)
            if academic_record
            and academic_record.cgpa_state == "KNOWN"
            and academic_record.cgpa is not None
            else None
        )

        # Backlogs
        # Fetch backlogs and their latest event to see if they are OPENED
        stmt = select(Backlog.id).where(Backlog.student_id == student_id)
        backlog_ids = (await self.session.execute(stmt)).scalars().all()
        open_backlog_count = 0
        if backlog_ids:
            for b_id in backlog_ids:
                stmt = (
                    select(BacklogEvent)
                    .where(BacklogEvent.backlog_id == b_id)
                    .order_by(BacklogEvent.version.desc())
                    .limit(1)
                )
                latest_b_event = (await self.session.execute(stmt)).scalar_one_or_none()
                if latest_b_event and latest_b_event.kind == "OPENED":
                    open_backlog_count += 1

        # Active Offers
        # Fetch offers and their latest event to see if they are ACTIVE (RECEIVED, ACCEPTED, TERMS_REVISED)
        stmt = select(Offer.id).where(Offer.student_id == student_id)
        offer_ids = (await self.session.execute(stmt)).scalars().all()
        active_offer_count = 0
        if offer_ids:
            for o_id in offer_ids:
                stmt = (
                    select(OfferEvent)
                    .where(OfferEvent.offer_id == o_id)
                    .order_by(OfferEvent.version.desc())
                    .limit(1)
                )
                latest_o_event = (await self.session.execute(stmt)).scalar_one_or_none()
                if latest_o_event and latest_o_event.kind in (
                    "RECEIVED",
                    "ACCEPTED",
                    "TERMS_REVISED",
                ):
                    active_offer_count += 1

        return {
            "student_id": str(student_id),
            "opportunity_id": str(opportunity_id),
            "academic": {"cgpa": cgpa, "backlogs": open_backlog_count},
            "placement_history": {"active_offer_count": active_offer_count},
        }

    async def evaluate(
        self, student_id: UUID, opportunity_id: UUID, req_version_id: UUID
    ) -> EligibilityDecision:
        evaluation_time = datetime.now(timezone.utc)

        # 1. Fetch Opportunity and Drive for Context
        stmt = (
            select(Opportunity, Drive)
            .join(Drive, Opportunity.drive_id == Drive.id)
            .where(
                Opportunity.id == opportunity_id,
                Opportunity.institution_id == self.principal.institution_id,
            )
        )
        result = (await self.session.execute(stmt)).first()
        if not result:
            raise HTTPException(404, "Opportunity not found")
        opp, drive = result

        # We assume scope="ALL" for now as there's no scope field on Opportunity/Drive.
        # A real implementation would map this from opportunity details.
        scope = "ALL"

        # 2. Get active policy
        policy_version = await self._get_active_policy(
            drive.academic_year_id, scope, evaluation_time
        )
        policy_version_id = policy_version.id

        # 3. Build Snapshot
        snapshot = await self.build_snapshot(student_id, opportunity_id, evaluation_time)

        # 4. Fetch Rules
        stmt = select(PolicyRule).where(PolicyRule.policy_version_id == policy_version_id)
        policy_rules = (await self.session.execute(stmt)).scalars().all()
        p_rules_dicts = [{"field": r.code, **r.definition} for r in policy_rules]

        stmt = select(Criterion).where(Criterion.requirement_version_id == req_version_id)
        criteria = (await self.session.execute(stmt)).scalars().all()
        r_criteria_dicts = [
            {
                "field": c.code,
                "operator": c.operator,
                "operand": c.operand,
                "applicability": c.applicability,
            }
            for c in criteria
        ]

        # 5. Compute evaluation_key
        snapshot_json = json.dumps(snapshot, sort_keys=True)
        key_input = f"{snapshot_json}|{policy_version_id}|{req_version_id}|v1.0"
        evaluation_key = hashlib.sha256(key_input.encode("utf-8")).hexdigest()

        # Check idempotency
        stmt = select(EligibilityDecision).where(
            EligibilityDecision.institution_id == self.principal.institution_id,
            EligibilityDecision.evaluation_key == evaluation_key,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing

        # 6. Evaluate
        final_result, reasons = evaluate_snapshot(snapshot, p_rules_dicts, r_criteria_dicts)

        # 7. Persist
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
            created_at=evaluation_time,
        )
        self.session.add(decision)
        try:
            await self.session.commit()
            await self.session.refresh(decision)
        except IntegrityError:
            await self.session.rollback()
            stmt = select(EligibilityDecision).where(
                EligibilityDecision.evaluation_key == evaluation_key,
                EligibilityDecision.student_id == student_id,
                EligibilityDecision.opportunity_id == opportunity_id,
            )
            decision = (await self.session.execute(stmt)).scalar_one_or_none()
            if not decision:
                raise HTTPException(
                    500,
                    {"code": "INTERNAL_ERROR", "message": "Failed to create or retrieve decision"},
                )

        return decision

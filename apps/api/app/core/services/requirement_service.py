from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.policy import CompensationCreate, CriterionCreate, RequirementMemberCreate
from app.core.security import Principal
from app.infrastructure.models.policy import (
    Criterion,
    Requirement,
    RequirementMember,
    RequirementVersion,
)
from app.infrastructure.models.recruitment import Compensation
from app.infrastructure.repositories.policy import (
    CriterionRepository,
    RequirementMemberRepository,
    RequirementRepository,
    RequirementVersionRepository,
)
from app.infrastructure.repositories.recruitment import (
    OpportunityRepository,
    CompensationRepository,
)


class RequirementService:
    def __init__(self, session: AsyncSession, principal: Principal):
        self.session = session
        self.principal = principal
        self.opp_repo = OpportunityRepository(session, principal.institution_id)
        self.req_repo = RequirementRepository(session, principal.institution_id)
        self.req_version_repo = RequirementVersionRepository(session, principal.institution_id)
        self.comp_repo = CompensationRepository(session, principal.institution_id)
        self.crit_repo = CriterionRepository(session, principal.institution_id)
        self.mem_repo = RequirementMemberRepository(session, principal.institution_id)

    async def initialize_requirement_graph(
        self, opportunity_id: UUID, comp_data: CompensationCreate
    ) -> RequirementVersion:
        opp = await self.opp_repo.get_by_id(opportunity_id)
        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        # 1. Check if requirement already exists
        reqs = await self.session.execute(
            Requirement.__table__.select()
            .where(Requirement.institution_id == self.principal.institution_id)
            .where(Requirement.opportunity_id == opportunity_id)
        )
        req_row = reqs.fetchone()

        if req_row:
            # If it already exists, we bump the version
            requirement_id = req_row.id
            versions = await self.session.execute(
                RequirementVersion.__table__.select()
                .where(RequirementVersion.institution_id == self.principal.institution_id)
                .where(RequirementVersion.requirement_id == requirement_id)
                .order_by(RequirementVersion.version.desc())
                .limit(1)
            )
            latest_version = versions.fetchone()
            next_version = latest_version.version + 1 if latest_version else 1
        else:
            # Create new requirement
            req = Requirement(
                institution_id=self.principal.institution_id,
                opportunity_id=opp.id,
                source_type="SYSTEM",
                source_reference=f"user:{self.principal.sub}",
            )
            self.session.add(req)
            await self.session.flush()
            requirement_id = req.id
            next_version = 1

        # 2. Create compensation
        comp = Compensation(
            institution_id=self.principal.institution_id,
            original_text=comp_data.original_text,
            currency=comp_data.currency,
            period=comp_data.period,
            basis=comp_data.basis,
            shape=comp_data.shape,
            amount=comp_data.amount,
            minimum=comp_data.minimum,
            maximum=comp_data.maximum,
            comparison_state=comp_data.comparison_state,
            annual_inr=comp_data.annual_inr,
            review_reason=comp_data.review_reason,
            source_type="SYSTEM",
            source_reference=f"user:{self.principal.sub}",
        )
        self.session.add(comp)
        await self.session.flush()

        # 3. Create requirement version
        req_v = RequirementVersion(
            institution_id=self.principal.institution_id,
            requirement_id=requirement_id,
            compensation_id=comp.id,
            version=next_version,
            effective_at=datetime.now(timezone.utc),
            source_type="SYSTEM",
            source_reference=f"user:{self.principal.sub}",
        )
        self.session.add(req_v)
        await self.session.flush()

        return req_v

    async def add_criterion(self, version_id: UUID, crit_data: CriterionCreate) -> Criterion:
        req_v = await self.req_version_repo.get_by_id(version_id)
        if not req_v:
            raise HTTPException(status_code=404, detail="Requirement version not found")

        if req_v.published_at is not None:
            raise HTTPException(
                status_code=400, detail="Cannot modify a published requirement version"
            )

        crit = Criterion(
            institution_id=self.principal.institution_id,
            requirement_version_id=req_v.id,
            code=crit_data.code,
            applicability=crit_data.applicability,
            operator=crit_data.operator,
            operand=crit_data.operand,
            source_type="SYSTEM",
            source_reference=f"user:{self.principal.sub}",
        )
        self.session.add(crit)
        await self.session.flush()

        return crit

    async def add_requirement_member(
        self, criterion_id: UUID, mem_data: RequirementMemberCreate
    ) -> RequirementMember:
        crit = await self.crit_repo.get_by_id(criterion_id)
        if not crit:
            raise HTTPException(status_code=404, detail="Criterion not found")

        req_v = await self.req_version_repo.get_by_id(crit.requirement_version_id)
        if req_v and req_v.published_at is not None:
            raise HTTPException(
                status_code=400, detail="Cannot modify a published requirement version"
            )

        mem = RequirementMember(
            institution_id=self.principal.institution_id,
            criterion_id=crit.id,
            value=mem_data.value,
            department_id=mem_data.department_id,
            degree_id=mem_data.degree_id,
            source_type="SYSTEM",
            source_reference=f"user:{self.principal.sub}",
        )
        self.session.add(mem)
        await self.session.flush()

        return mem

    async def publish_requirement_version(self, version_id: UUID) -> RequirementVersion:
        req_v = await self.req_version_repo.get_by_id(version_id)
        if not req_v:
            raise HTTPException(status_code=404, detail="Requirement version not found")

        if req_v.published_at is not None:
            return req_v

        req_v.published_at = datetime.now(timezone.utc)
        await self.session.flush()

        return req_v

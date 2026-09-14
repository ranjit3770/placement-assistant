"""M8 application adapter. Frozen M5/M7 contracts are consumed, not modified."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import ToolContext
from app.agent.core import AgentResponse
from app.api.schemas.eligibility import EligibilityDecisionResponse
from app.core.security import Principal
from app.core.services.eligibility_service import EligibilityService
from app.infrastructure.models.policy import Requirement, RequirementActivation, RequirementVersion
from app.infrastructure.models.recruitment import Opportunity
from app.infrastructure.models.students import Student


class M8EligibilityInput(BaseModel):
    opportunity_id: UUID
    model_config = ConfigDict(extra="forbid")


class M8AgentResponse(AgentResponse):
    authoritative_decision: EligibilityDecisionResponse | None = None


class M8EligibilityRepository:
    def __init__(self, session: AsyncSession, principal: Principal):
        self.session = session
        self.principal = principal

    async def owned_student(self) -> UUID:
        if self.principal.role != "STUDENT":
            raise PermissionError("Student identity required")
        student_id = await self.session.scalar(
            select(Student.id).where(
                Student.institution_id == self.principal.institution_id,
                Student.user_id == self.principal.sub,
            )
        )
        if student_id is None:
            raise PermissionError("Student identity unavailable")
        return student_id

    async def active_requirement(self, opportunity_id: UUID) -> UUID:
        now = datetime.now(UTC)
        tenant = self.principal.institution_id
        result = await self.session.scalars(
            select(RequirementVersion.id)
            .join(Requirement, Requirement.id == RequirementVersion.requirement_id)
            .join(Opportunity, Opportunity.id == Requirement.opportunity_id)
            .join(
                RequirementActivation,
                RequirementActivation.requirement_version_id == RequirementVersion.id,
            )
            .where(
                Opportunity.id == opportunity_id,
                Opportunity.institution_id == tenant,
                Requirement.institution_id == tenant,
                RequirementVersion.institution_id == tenant,
                RequirementActivation.institution_id == tenant,
                RequirementActivation.requirement_id == Requirement.id,
                RequirementVersion.published_at <= now,
                RequirementActivation.starts_at <= now,
                (RequirementActivation.ends_at.is_(None) | (RequirementActivation.ends_at > now)),
            )
        )
        versions = result.all()
        if len(versions) != 1:
            raise ValueError("Applicable requirement unavailable or ambiguous")
        return versions[0]


async def evaluate_m5(args: M8EligibilityInput, context: ToolContext) -> dict:
    if not isinstance(context.db_session, AsyncSession):
        raise RuntimeError("Authoritative database session unavailable")
    repository = M8EligibilityRepository(context.db_session, context.principal)
    student_id = await repository.owned_student()
    requirement_id = await repository.active_requirement(args.opportunity_id)
    decision = await EligibilityService(context.db_session, context.principal).evaluate(
        student_id=student_id, opportunity_id=args.opportunity_id, req_version_id=requirement_id
    )
    return EligibilityDecisionResponse.model_validate(decision).model_dump(mode="json")


def authority_message(decision: EligibilityDecisionResponse | None) -> str:
    if decision is None:
        return "Eligibility has not been verified. No authoritative decision is available."
    messages = {
        "ELIGIBLE": "You are eligible for the evaluated opportunity.",
        "NOT_ELIGIBLE": "You are not eligible for the evaluated opportunity.",
        "UNKNOWN": "Eligibility could not be determined from the authoritative information.",
    }
    return messages.get(decision.result, messages["UNKNOWN"])

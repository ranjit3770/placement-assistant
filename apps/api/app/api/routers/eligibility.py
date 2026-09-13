from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.eligibility import EligibilityRequest, EligibilityDecisionResponse
from app.core.security import Principal, get_current_user
from app.core.services.eligibility_service import EligibilityService
from app.infrastructure.database import get_session

router = APIRouter(prefix="/eligibility", tags=["eligibility"])

@router.post("/evaluate", response_model=EligibilityDecisionResponse, status_code=201)
async def evaluate_eligibility(
    request: EligibilityRequest,
    principal: Principal = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    service = EligibilityService(session, principal)
    decision = await service.evaluate(
        student_id=request.student_id,
        opportunity_id=request.opportunity_id,
        req_version_id=request.requirement_version_id,
        policy_version_id=request.policy_version_id
    )
    return decision

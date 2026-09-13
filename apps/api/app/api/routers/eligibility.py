from typing import Annotated
from fastapi import APIRouter, Depends, Request

from app.api.schemas.eligibility import EligibilityRequest, EligibilityDecisionResponse
from app.core.security import Principal, current_principal
from app.core.services.eligibility_service import EligibilityService

router = APIRouter(prefix="/eligibility", tags=["eligibility"])

def get_eligibility_service(request: Request, principal: Principal = Depends(current_principal)) -> EligibilityService:
    return EligibilityService(request.state.dependencies.session, principal)

@router.post("/evaluate", response_model=EligibilityDecisionResponse, status_code=201)
async def evaluate_eligibility(
    request: EligibilityRequest,
    service: Annotated[EligibilityService, Depends(get_eligibility_service)]
):
    decision = await service.evaluate(
        student_id=request.student_id,
        opportunity_id=request.opportunity_id,
        req_version_id=request.requirement_version_id,
        policy_version_id=request.policy_version_id
    )
    return decision

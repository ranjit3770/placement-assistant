from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.schemas.policy import (
    CompensationCreate,
    CriterionCreate,
    CriterionResponse,
    RequirementMemberCreate,
    RequirementMemberResponse,
    RequirementVersionResponse,
)
from app.core.security import Principal, current_principal
from app.core.services.requirement_service import RequirementService

router = APIRouter(tags=["requirements"])


def get_requirement_service(
    request: Request, principal: Principal = Depends(current_principal)
) -> RequirementService:
    return RequirementService(request.state.dependencies.session, principal)


@router.post(
    "/opportunities/{opportunity_id}/requirements",
    response_model=RequirementVersionResponse,
    status_code=201,
)
async def initialize_requirement_graph(
    opportunity_id: UUID,
    data: CompensationCreate,
    service: Annotated[RequirementService, Depends(get_requirement_service)],
):
    req_v = await service.initialize_requirement_graph(opportunity_id, data)
    return req_v


@router.post(
    "/requirements/versions/{version_id}/criteria",
    response_model=CriterionResponse,
    status_code=201,
)
async def add_criterion(
    version_id: UUID,
    data: CriterionCreate,
    service: Annotated[RequirementService, Depends(get_requirement_service)],
):
    crit = await service.add_criterion(version_id, data)
    return crit


@router.post(
    "/requirements/criteria/{criterion_id}/members",
    response_model=RequirementMemberResponse,
    status_code=201,
)
async def add_requirement_member(
    criterion_id: UUID,
    data: RequirementMemberCreate,
    service: Annotated[RequirementService, Depends(get_requirement_service)],
):
    mem = await service.add_requirement_member(criterion_id, data)
    return mem


@router.post(
    "/requirements/versions/{version_id}/publish", response_model=RequirementVersionResponse
)
async def publish_requirement_version(
    version_id: UUID,
    service: Annotated[RequirementService, Depends(get_requirement_service)],
):
    req_v = await service.publish_requirement_version(version_id)
    return req_v

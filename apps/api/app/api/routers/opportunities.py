from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.schemas.recruitment import (
    DriveCreate,
    DriveResponse,
    OpportunityCreate,
    OpportunityResponse,
)
from app.core.security import Principal, current_principal
from app.core.services.opportunity_service import OpportunityService

router = APIRouter(tags=["opportunities"])


def get_opportunity_service(
    request: Request, principal: Principal = Depends(current_principal)
) -> OpportunityService:
    return OpportunityService(request.state.dependencies.session, principal)


@router.post("/companies/{company_id}/drives", response_model=DriveResponse, status_code=201)
async def create_drive(
    company_id: UUID,
    data: DriveCreate,
    service: Annotated[OpportunityService, Depends(get_opportunity_service)],
):
    drive = await service.create_drive(company_id, data)
    return drive


@router.post(
    "/companies/{company_id}/opportunities", response_model=OpportunityResponse, status_code=201
)
async def create_opportunity(
    company_id: UUID,
    data: OpportunityCreate,
    service: Annotated[OpportunityService, Depends(get_opportunity_service)],
):
    opp = await service.create_opportunity(company_id, data)
    return opp


@router.put("/opportunities/{opportunity_id}/close", response_model=OpportunityResponse)
async def close_opportunity(
    opportunity_id: UUID,
    service: Annotated[OpportunityService, Depends(get_opportunity_service)],
):
    opp = await service.close_opportunity(opportunity_id)
    return opp

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.schemas.recruitment import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
    RoleCreate,
    RoleResponse,
)
from app.core.security import Principal, current_principal
from app.core.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


def get_company_service(
    request: Request, principal: Principal = Depends(current_principal)
) -> CompanyService:
    return CompanyService(request.state.dependencies.session, principal)


@router.post("", response_model=CompanyResponse, status_code=201)
async def create_company(
    data: CompanyCreate,
    service: Annotated[CompanyService, Depends(get_company_service)],
):
    revision = await service.create_company(data)
    # The revision effectively has the company_id, code is on the parent but for Response we need code.
    # The simplest is to fetch it from the repository. We can do it inside service, but for now
    company = await service.company_repo.get_by_id(revision.company_id)
    return CompanyResponse(id=company.id, code=company.code, name=revision.name)


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    data: CompanyUpdate,
    service: Annotated[CompanyService, Depends(get_company_service)],
):
    revision = await service.update_company(company_id, data)
    company = await service.company_repo.get_by_id(revision.company_id)
    return CompanyResponse(id=company.id, code=company.code, name=revision.name)


@router.post("/{company_id}/roles", response_model=RoleResponse, status_code=201)
async def create_role(
    company_id: UUID,
    data: RoleCreate,
    service: Annotated[CompanyService, Depends(get_company_service)],
):
    role = await service.create_role(company_id, data)
    return role

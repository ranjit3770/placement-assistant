from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.policy import (
    DocumentCreate,
    DocumentResponse,
    PolicyCreate,
    PolicyResponse,
    PolicyVersionCreate,
    PolicyVersionResponse,
    PolicyRuleCreate,
    PolicyRuleResponse,
    PolicyTransitionRequest,
    PolicyActivationRequest,
    PolicyActivationResponse,
)
from app.core.security import Principal, current_principal
from app.core.services.policy_service import PolicyService

router = APIRouter(prefix="/policies", tags=["Policies"])


def get_policy_service(
    request: Request, principal: Principal = Depends(current_principal)
) -> PolicyService:
    return PolicyService(request.state.dependencies.session, principal)


PolicySvc = Annotated[PolicyService, Depends(get_policy_service)]


@router.post("/documents", response_model=DocumentResponse, status_code=201)
async def create_document(data: DocumentCreate, svc: PolicySvc):
    return await svc.create_document(data)


@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(data: PolicyCreate, svc: PolicySvc):
    return await svc.create_policy(data)


@router.post("/{policy_id}/versions", response_model=PolicyVersionResponse, status_code=201)
async def create_policy_version(policy_id: UUID, data: PolicyVersionCreate, svc: PolicySvc):
    return await svc.create_policy_version(policy_id, data)


@router.post("/versions/{version_id}/rules", response_model=PolicyRuleResponse, status_code=201)
async def add_policy_rule(version_id: UUID, data: PolicyRuleCreate, svc: PolicySvc):
    return await svc.add_policy_rule(version_id, data)


@router.post(
    "/versions/{version_id}/processing", response_model=PolicyVersionResponse, status_code=200
)
async def transition_to_processing(version_id: UUID, req: PolicyTransitionRequest, svc: PolicySvc):
    return await svc.transition_status(version_id, req, "PROCESSING")


@router.post("/versions/{version_id}/review", response_model=PolicyVersionResponse, status_code=200)
async def transition_to_review(version_id: UUID, req: PolicyTransitionRequest, svc: PolicySvc):
    return await svc.transition_status(version_id, req, "REVIEW")


@router.post(
    "/versions/{version_id}/approve", response_model=PolicyVersionResponse, status_code=200
)
async def approve_policy(version_id: UUID, req: PolicyTransitionRequest, svc: PolicySvc):
    return await svc.approve_policy(version_id, req)


@router.post(
    "/versions/{version_id}/activate", response_model=PolicyActivationResponse, status_code=201
)
async def activate_policy(version_id: UUID, req: PolicyActivationRequest, svc: PolicySvc):
    return await svc.activate_policy(version_id, req)


@router.post(
    "/versions/{version_id}/archive", response_model=PolicyVersionResponse, status_code=200
)
async def archive_policy(version_id: UUID, req: PolicyTransitionRequest, svc: PolicySvc):
    return await svc.archive_policy(version_id, req)

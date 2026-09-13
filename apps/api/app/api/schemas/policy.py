from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompensationCreate(BaseModel):
    original_text: str
    currency: str = Field(..., max_length=3)
    period: str = Field(..., max_length=20)
    basis: str = Field(..., max_length=30)
    shape: str = Field(..., max_length=20)
    amount: Optional[Decimal] = None
    minimum: Optional[Decimal] = None
    maximum: Optional[Decimal] = None
    comparison_state: str = Field(..., max_length=20)
    annual_inr: Optional[Decimal] = None
    review_reason: Optional[str] = None


class CompensationResponse(CompensationCreate):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


class RequirementVersionCreate(BaseModel):
    compensation: CompensationCreate
    version: int = 1


class RequirementVersionResponse(BaseModel):
    id: UUID
    requirement_id: UUID
    compensation_id: UUID
    version: int
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RequirementResponse(BaseModel):
    id: UUID
    opportunity_id: UUID

    model_config = ConfigDict(from_attributes=True)


class CriterionCreate(BaseModel):
    code: str = Field(..., max_length=100)
    applicability: str = Field(..., max_length=20)
    operator: Optional[str] = Field(None, max_length=12)
    operand: Optional[dict[str, Any]] = None


class CriterionResponse(CriterionCreate):
    id: UUID
    requirement_version_id: UUID

    model_config = ConfigDict(from_attributes=True)


class RequirementMemberCreate(BaseModel):
    value: str = Field(..., max_length=200)
    department_id: Optional[UUID] = None
    degree_id: Optional[UUID] = None


class RequirementMemberResponse(RequirementMemberCreate):
    id: UUID
    criterion_id: UUID

    model_config = ConfigDict(from_attributes=True)


class DocumentCreate(BaseModel):
    filename: str = Field(..., max_length=255)
    media_type: str = Field(..., max_length=80)
    content: (
        str  # For simulation purposes, we will hash this in the service to create the content_hash
    )


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    media_type: str
    content_hash: str
    storage_key: str
    source_version: str

    model_config = ConfigDict(from_attributes=True)


class PolicyCreate(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)


class PolicyResponse(PolicyCreate):
    id: UUID
    institution_id: UUID

    model_config = ConfigDict(from_attributes=True)


class PolicyVersionCreate(BaseModel):
    academic_year_id: UUID
    scope: str = Field(..., max_length=100)
    schema_version: int = 1
    definition: dict[str, Any]


class PolicyVersionResponse(PolicyVersionCreate):
    id: UUID
    policy_id: UUID
    status: str
    version: int
    effective_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyRuleCreate(BaseModel):
    code: str = Field(..., max_length=100)
    definition: dict[str, Any]


class PolicyRuleResponse(PolicyRuleCreate):
    id: UUID
    policy_version_id: UUID

    model_config = ConfigDict(from_attributes=True)


class PolicyTransitionRequest(BaseModel):
    reason: str = Field(..., max_length=500)


class PolicyActivationRequest(PolicyTransitionRequest):
    starts_at: datetime
    ends_at: Optional[datetime] = None


class PolicyActivationResponse(BaseModel):
    id: UUID
    policy_version_id: UUID
    academic_year_id: UUID
    scope: str
    starts_at: datetime
    ends_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

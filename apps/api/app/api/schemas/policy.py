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

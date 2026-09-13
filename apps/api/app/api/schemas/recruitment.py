from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(...)

    model_config = ConfigDict(from_attributes=True)


class CompanyUpdate(BaseModel):
    name: str = Field(...)


class CompanyResponse(BaseModel):
    id: UUID
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(BaseModel):
    code: str = Field(..., max_length=100)
    title: str = Field(...)


class RoleResponse(BaseModel):
    id: UUID
    company_id: UUID
    code: str
    title: str

    model_config = ConfigDict(from_attributes=True)


class DriveCreate(BaseModel):
    academic_year_id: UUID
    announced_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    status: str = Field("DRAFT", max_length=20)


class DriveResponse(BaseModel):
    id: UUID
    company_id: UUID
    academic_year_id: UUID
    announced_at: Optional[datetime]
    scheduled_at: Optional[datetime]
    status: str

    model_config = ConfigDict(from_attributes=True)


class OpportunityCreate(BaseModel):
    role_id: UUID
    drive_id: UUID
    deadline: Optional[datetime] = None
    status: str = Field("DRAFT", max_length=20)


class OpportunityResponse(BaseModel):
    id: UUID
    company_id: UUID
    role_id: UUID
    drive_id: UUID
    deadline: Optional[datetime]
    status: str

    model_config = ConfigDict(from_attributes=True)

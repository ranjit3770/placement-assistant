from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class EligibilityRequest(BaseModel):
    student_id: UUID
    opportunity_id: UUID
    requirement_version_id: UUID

class EligibilityDecisionResponse(BaseModel):
    id: UUID
    student_id: UUID
    opportunity_id: UUID
    policy_version_id: UUID
    requirement_version_id: UUID
    engine_version: str
    result: str
    evaluation_key: str
    snapshot: dict[str, Any]
    reasons: list[dict[str, Any]]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

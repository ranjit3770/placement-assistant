from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CopilotDecision(BaseModel):
    status: Literal["ELIGIBLE", "NOT_ELIGIBLE", "UNKNOWN"]
    reason: str | None = None
    evaluation_reference: UUID | None = None


class CopilotEvidence(BaseModel):
    policy_reference: str | None = None
    version_reference: str | None = None
    excerpts: list[str] = []
    source_metadata: dict[str, Any] = {}


class CopilotAgentResponse(BaseModel):
    message: str
    decision: CopilotDecision | None = None
    evidence: list[CopilotEvidence] = []


class CopilotMessageRequest(BaseModel):
    query: str
    model_config = ConfigDict(extra="forbid")


class CopilotConversationSession(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CopilotMessage(BaseModel):
    id: UUID
    sequence_number: int
    role: str
    content: str | None = None
    created_at: datetime
    # Intentionally stripping internal tool_calls, tool_name, tool_call_id, and metadata
    model_config = ConfigDict(from_attributes=True)

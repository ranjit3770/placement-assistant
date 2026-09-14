from typing import Any, Literal
from pydantic import BaseModel

class EvidenceReference(BaseModel):
    document_id: str
    policy_version: str
    content: str
    source_hash: str | None = None

class AgentResponse(BaseModel):
    message: str
    decision: Literal["ELIGIBLE", "NOT_ELIGIBLE", "UNKNOWN"] | None = None
    decision_source: Literal["M5_ENGINE"] | None = None
    evidence: list[EvidenceReference] = []

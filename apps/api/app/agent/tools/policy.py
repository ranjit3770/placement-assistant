from pydantic import BaseModel, ConfigDict
from typing import Any
from uuid import UUID

from app.agent.context import ToolContext
from app.agent.registry import agent_tool, ToolEffect
from app.agent.tools.student import EmptyInput

class PolicySearchInput(BaseModel):
    query: str
    model_config = ConfigDict(extra="forbid")

class PolicyEvidenceInput(BaseModel):
    document_id: str
    section: str | None = None
    model_config = ConfigDict(extra="forbid")

@agent_tool(
    name="search_policy",
    description="Searches for institutional placement policy evidence. Only returns verified evidence.",
    input_schema=PolicySearchInput,
    effect=ToolEffect.READ_ONLY
)
def search_policy(args: PolicySearchInput, context: ToolContext) -> dict[str, Any]:
    # Conceptually:
    # retrieval_service = RetrievalService(...)
    # return retrieval_service.search(query=args.query, principal=context.principal)
    return {
        "query": args.query,
        "evidence": ["VERIFIED_POLICY_EVIDENCE_STUB"]
    }

@agent_tool(
    name="get_policy_evidence",
    description="Retrieves a specific section of verified policy evidence.",
    input_schema=PolicyEvidenceInput,
    effect=ToolEffect.READ_ONLY
)
def get_policy_evidence(args: PolicyEvidenceInput, context: ToolContext) -> dict[str, Any]:
    return {
        "document_id": args.document_id,
        "section": args.section,
        "content": "VERIFIED_EVIDENCE_CONTENT_STUB"
    }

@agent_tool(
    name="get_active_policy",
    description="Retrieves the metadata of the currently active placement policy.",
    input_schema=EmptyInput,
    effect=ToolEffect.READ_ONLY
)
def get_active_policy(args: EmptyInput, context: ToolContext) -> dict[str, Any]:
    return {
        "policy_id": "ACTIVE_POLICY_STUB",
        "version": "1.0"
    }

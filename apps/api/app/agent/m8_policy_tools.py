"""
M8 policy tools — wired to M6 RetrievalService via the certified bridge.

The synchronous @agent_tool registration stubs are replaced here by async
handlers that invoke search_policy_via_m6(). The orchestrator's await
dispatch handles the coroutines.

M7 tool registrations remain frozen in tools/policy.py. These M8 handlers
override only the search_policy and get_policy_evidence behaviour to use
real M6 retrieval when the context provides session + embedding provider +
qdrant adapter.

get_active_policy is a separate PostgreSQL query; it is not a Qdrant
retrieval and remains as-is in the M7 registry for now.
"""
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import ToolContext
from app.agent.m8_m6_bridge import search_policy_via_m6
from app.infrastructure.models.policy import PolicyVersion


class PolicySearchInput(BaseModel):
    """Query string + optional policy version to scope the search."""
    query: str
    policy_version_id: UUID | None = None
    model_config = ConfigDict(extra="forbid")


class PolicyEvidenceInput(BaseModel):
    document_id: str
    section: str | None = None
    model_config = ConfigDict(extra="forbid")


async def m8_search_policy(args: PolicySearchInput, context: ToolContext) -> dict[str, Any]:
    """Route search_policy through M6 RetrievalService.

    If policy_version_id is not supplied, attempt to locate the active
    policy version for the authenticated institution. Abstain if not found.
    """
    session = getattr(context, "db_session", None)
    institution_id: UUID = context.principal.institution_id

    policy_version_id = args.policy_version_id
    if policy_version_id is None and session is not None:
        # Resolve the most recently created ACTIVE policy version for this institution
        row = await session.scalar(
            select(PolicyVersion.id)
            .where(
                PolicyVersion.institution_id == institution_id,
                PolicyVersion.status == "ACTIVE",
            )
            .order_by(PolicyVersion.id.desc())
            .limit(1)
        )
        policy_version_id = row  # May still be None → will abstain below

    if policy_version_id is None:
        return {
            "query": args.query,
            "evidence": [],
            "abstained": True,
            "reason": "NO_ACTIVE_POLICY",
        }

    return await search_policy_via_m6(
        query=args.query,
        institution_id=institution_id,
        policy_version_id=policy_version_id,
        context=context,
    )

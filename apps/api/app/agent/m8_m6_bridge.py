"""
Phase 3: M6 policy evidence integration.

The policy tools (search_policy, get_policy_evidence, get_active_policy) must
route through the actual M6 RetrievalService for certified evidence retrieval.
This module provides the async bridge, keeping policy.py's @agent_tool handlers
synchronous at the registration layer while invoking the service asynchronously.
"""
from uuid import UUID
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import ToolContext
from app.rag.contracts import EvidenceError, VerifiedEvidence
from app.rag.retrieval_service import RetrievalService


async def search_policy_via_m6(
    query: str,
    institution_id: UUID,
    policy_version_id: UUID,
    context: ToolContext,
) -> dict[str, Any]:
    """Route a policy search through the certified M6 RetrievalService.

    Returns a safe dict suitable for the tool result channel.
    Abstains (returns no evidence) rather than raising, so the agent can
    formulate a controlled response rather than crashing.
    """
    session = getattr(context, "db_session", None)
    if session is None:
        return {"query": query, "evidence": [], "abstained": True, "reason": "NO_SESSION"}

    # Embedding provider and Qdrant must be wired via app state when the
    # request context is available. For the current M8 scope we read them
    # from the session's connection info. If they are unavailable we abstain.
    embedding_provider = getattr(context, "embedding_provider", None)
    qdrant_adapter = getattr(context, "qdrant_adapter", None)

    if embedding_provider is None or qdrant_adapter is None:
        return {
            "query": query,
            "evidence": [],
            "abstained": True,
            "reason": "PROVIDER_UNAVAILABLE",
        }

    try:
        service = RetrievalService(session, embedding_provider, qdrant_adapter)
        results: list[VerifiedEvidence] = await service.retrieve(
            institution_id=institution_id,
            policy_version_id=policy_version_id,
            query=query,
            limit=5,
        )
    except EvidenceError as e:
        return {"query": query, "evidence": [], "abstained": True, "reason": e.code}
    except Exception:
        return {"query": query, "evidence": [], "abstained": True, "reason": "RETRIEVAL_ERROR"}

    evidence_list = [
        {
            "text": ev.text,
            "document_id": str(ev.citation.document_id),
            "source_hash": ev.citation.source_hash,
            "chunk_hash": ev.citation.chunk_hash,
            "ordinal": ev.citation.ordinal,
            "page": ev.citation.page,
            "section": ev.citation.section,
            "score": ev.score,
        }
        for ev in results
    ]
    return {"query": query, "evidence": evidence_list, "abstained": False}

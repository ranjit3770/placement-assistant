from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from app.agent.context import ToolContext
from app.agent.memory import ConversationMemory
from app.agent.orchestrator import AgentOrchestrator
from app.api.routers.agent import agent_session
from app.api.schemas.copilot import (
    CopilotAgentResponse,
    CopilotConversationSession,
    CopilotDecision,
    CopilotEvidence,
    CopilotMessage,
    CopilotMessageRequest,
)
from app.core.security import Principal, current_principal

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.get("/conversations", response_model=list[CopilotConversationSession])
async def list_conversations(
    req: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    session: Annotated[AsyncSession, Depends(agent_session)],
):
    tool_context = ToolContext(
        principal=principal, request_id=str(req.state.request_id), db_session=session
    )
    memory = ConversationMemory(db=session, context=tool_context)
    try:
        sessions = await memory.list_sessions()
        return [CopilotConversationSession.model_validate(s) for s in sessions]
    except PermissionError:
        raise HTTPException(status_code=403, detail="FORBIDDEN") from None


@router.post("/conversations", response_model=CopilotConversationSession)
async def create_conversation(
    req: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    session: Annotated[AsyncSession, Depends(agent_session)],
):
    tool_context = ToolContext(
        principal=principal, request_id=str(req.state.request_id), db_session=session
    )
    memory = ConversationMemory(db=session, context=tool_context)
    try:
        new_id = uuid4()
        s = await memory.get_or_create_session(new_id)
        return CopilotConversationSession.model_validate(s)
    except PermissionError:
        raise HTTPException(status_code=403, detail="FORBIDDEN") from None


@router.get("/conversations/{conversation_id}", response_model=list[CopilotMessage])
async def get_conversation_history(
    conversation_id: UUID,
    req: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    session: Annotated[AsyncSession, Depends(agent_session)],
):
    tool_context = ToolContext(
        principal=principal, request_id=str(req.state.request_id), db_session=session
    )
    memory = ConversationMemory(db=session, context=tool_context)
    try:
        raw_msgs = await memory.get_raw_messages(conversation_id)
        return [CopilotMessage.model_validate(m) for m in raw_msgs if m.role in ("user", "assistant") and m.content is not None]
    except PermissionError:
        raise HTTPException(status_code=403, detail="FORBIDDEN") from None


@router.post("/conversations/{conversation_id}/messages", response_model=CopilotAgentResponse)
async def send_message(
    conversation_id: UUID,
    request: CopilotMessageRequest,
    req: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    session: Annotated[AsyncSession, Depends(agent_session)],
):
    tool_context = ToolContext(
        principal=principal, request_id=str(req.state.request_id), db_session=session
    )
    memory = ConversationMemory(db=session, context=tool_context)

    try:
        await memory.get_or_create_session(conversation_id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="FORBIDDEN") from None

    openai_client = AsyncOpenAI()
    orchestrator = AgentOrchestrator(memory=memory, openai_client=openai_client)

    try:
        m8_resp = await orchestrator.execute(
            conversation_id=conversation_id, query=request.query
        )
        
        # Transform M8AgentResponse to CopilotAgentResponse
        decision = None
        if m8_resp.authoritative_decision:
            decision = CopilotDecision(
                status=m8_resp.authoritative_decision.result,
                reason=m8_resp.authoritative_decision.reason,
                evaluation_reference=m8_resp.authoritative_decision.evaluation_id,
            )
            
        evidence_list = []
        for e in m8_resp.evidence:
            evidence_list.append(CopilotEvidence(
                policy_reference=e.document_id,
                version_reference=e.policy_version,
                excerpts=[e.content],
                source_metadata={"hash": e.source_hash} if e.source_hash else {}
            ))
            
        return CopilotAgentResponse(
            message=m8_resp.message,
            decision=decision,
            evidence=evidence_list
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="FORBIDDEN") from None

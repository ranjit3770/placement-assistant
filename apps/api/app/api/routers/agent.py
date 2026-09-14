from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal, current_principal
from app.agent.core import AgentResponse
from app.agent.context import ToolContext
from app.agent.memory import ConversationMemory
from app.agent.orchestrator import AgentOrchestrator
from app.agent.m8_authority import M8AgentResponse

router = APIRouter(prefix="/agent", tags=["agent"])

class ChatRequest(BaseModel):
    conversation_id: UUID
    query: str
    model_config = ConfigDict(extra="forbid")

@router.post("/chat", response_model=M8AgentResponse)
async def chat_with_agent(
    request: ChatRequest,
    req: Request,
    principal: Principal = Depends(current_principal),
):
    session: AsyncSession = req.state.dependencies.session
    tool_context = ToolContext(principal=principal, request_id=str(req.state.request_id), db_session=session)
    memory = ConversationMemory(db=session, context=tool_context)
    
    # Instantiate OpenAI client (uses OPENAI_API_KEY from env or can be mocked)
    # We can also pull from app settings if needed, but SDK defaults to env var.
    openai_client = AsyncOpenAI()
    
    orchestrator = AgentOrchestrator(memory=memory, openai_client=openai_client)
    
    try:
        response = await orchestrator.execute(
            conversation_id=request.conversation_id,
            query=request.query
        )
        return response
    except PermissionError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail=str(e))

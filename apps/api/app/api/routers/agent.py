from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent.context import ToolContext
from app.agent.m8_authority import M8AgentResponse
from app.agent.memory import ConversationMemory
from app.agent.orchestrator import AgentOrchestrator
from app.core.security import Principal, current_principal

router = APIRouter(prefix="/agent", tags=["agent"])


class ChatRequest(BaseModel):
    conversation_id: UUID
    query: str
    model_config = ConfigDict(extra="forbid")


async def agent_session(req: Request) -> AsyncIterator[AsyncSession]:
    """M8-owned per-request session; no changes to frozen infrastructure.

    Respect an explicitly injected session used by existing integration callers.
    Normal HTTP requests use the engine managed by the application's lifespan.
    """
    injected = getattr(req.state, "dependencies", None)
    if injected is not None and isinstance(getattr(injected, "session", None), AsyncSession):
        yield injected.session
        return
    factory = async_sessionmaker(req.app.state.dependencies.engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@router.post("/chat", response_model=M8AgentResponse)
async def chat_with_agent(
    request: ChatRequest,
    req: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    session: Annotated[AsyncSession, Depends(agent_session)],
):
    tool_context = ToolContext(
        principal=principal, request_id=str(req.state.request_id), db_session=session
    )
    memory = ConversationMemory(db=session, context=tool_context)

    # Authenticate/authorize before provider construction or any source/query transmission.
    try:
        await memory.get_or_create_session(request.conversation_id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="FORBIDDEN") from None

    # Instantiate OpenAI client (uses OPENAI_API_KEY from env or can be mocked)
    # We can also pull from app settings if needed, but SDK defaults to env var.
    openai_client = AsyncOpenAI()

    orchestrator = AgentOrchestrator(memory=memory, openai_client=openai_client)

    try:
        response = await orchestrator.execute(
            conversation_id=request.conversation_id, query=request.query
        )
        return response
    except PermissionError:
        raise HTTPException(status_code=403, detail="FORBIDDEN") from None

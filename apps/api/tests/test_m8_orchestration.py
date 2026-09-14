import pytest
from uuid import uuid4
import json
import os
import jwt
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport

from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call import Function
from openai.types.chat.chat_completion import Choice

from app.main import create_app
from app.core.config import Settings
from app.agent.orchestrator import AgentOrchestrator
from app.agent.memory import ConversationMemory
from app.agent.context import ToolContext
from app.core.security import Principal
from app.agent.core import AgentResponse
from app.infrastructure.models.students import Institution, Student, User
import app.agent.tools.eligibility
import app.agent.tools.policy
import app.agent.tools.student

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

M8_TEST_DATABASE_URL = os.environ.get("M8_TEST_DATABASE_URL")

pytestmark = pytest.mark.anyio

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
async def db_engine():
    if not M8_TEST_DATABASE_URL:
        pytest.skip("M8_TEST_DATABASE_URL is required")
    engine = create_async_engine(M8_TEST_DATABASE_URL)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    async_session = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def test_principal(db_session):
    inst = Institution(code=f"INST_{uuid4().hex[:8]}", name="Test Inst")
    db_session.add(inst)
    await db_session.flush()
    
    student = Student(
        institution_id=inst.id,
        roll_number=f"R_{uuid4().hex[:8]}",
        source_type="SYSTEM",
        source_reference="test"
    )
    db_session.add(student)
    user = User(institution_id=inst.id, login=f"{uuid4().hex}@example.invalid",
                source_type="SYSTEM", source_reference="test")
    db_session.add(user)
    await db_session.flush()
    student.user_id = user.id
    await db_session.commit()
    return Principal(sub=user.id, institution_id=inst.id, role="STUDENT")

@pytest.fixture
def mock_memory(db_session, test_principal):
    context = ToolContext(principal=test_principal, request_id="req-1")
    return ConversationMemory(db=db_session, context=context)

def create_mock_openai(responses):
    mock = AsyncMock()
    mock.chat.completions.create.side_effect = responses
    return mock

def create_tool_call(name: str, args: dict):
    return ChatCompletionMessageToolCall(
        id=f"call_{uuid4().hex[:6]}",
        type="function",
        function=Function(name=name, arguments=json.dumps(args))
    )

def create_response(content: str = None, tool_calls: list = None):
    message = ChatCompletionMessage(
        role="assistant",
        content=content,
        tool_calls=tool_calls
    )
    choice = Choice(
        finish_reason="stop" if not tool_calls else "tool_calls",
        index=0,
        message=message,
    )
    return ChatCompletion(
        id="resp_1",
        choices=[choice],
        created=123,
        model="gpt-4o-mini",
        object="chat.completion"
    )

async def test_m8_01_loop_termination_budget(mock_memory):
    from app.agent.limits import BudgetExhaustedError
    responses = [create_response(tool_calls=[create_tool_call("get_student_profile", {})]) for _ in range(10)]
    openai = create_mock_openai(responses)
    orchestrator = AgentOrchestrator(memory=mock_memory, openai_client=openai)
    with pytest.raises(BudgetExhaustedError):
        await orchestrator.execute(uuid4(), "query")

async def test_m8_02_schema_bridge(mock_memory):
    orchestrator = AgentOrchestrator(memory=mock_memory, openai_client=AsyncMock())
    tools = orchestrator._get_openai_tools()
    assert len(tools) == 7
    for t in tools:
        assert "type" in t
        props = t["function"]["parameters"].get("properties", {})
        assert "student_id" not in props
        assert "tenant_id" not in props

async def test_m8_03_state_preservation(mock_memory):
    assert mock_memory.context.principal is not None

async def test_m8_04_missing_service_cannot_claim_authority(mock_memory):
    tool_resp = create_response(tool_calls=[create_tool_call("evaluate_eligibility", {"opportunity_id": str(uuid4())})])
    final_resp = create_response(content="You are eligible.")
    openai = create_mock_openai([tool_resp, final_resp])
    orchestrator = AgentOrchestrator(memory=mock_memory, openai_client=openai)
    
    response = await orchestrator.execute(uuid4(), "Am I eligible?")
    # This fixture has no service session: it must not fall back to M7's stub.
    # Real-M5 contradictory output is tested in test_m8_authority_remediation.py.
    assert response.decision == "UNKNOWN"
    assert response.decision_source is None
    assert response.authoritative_decision is None
    assert response.message == "Eligibility has not been verified. No authoritative decision is available."

async def test_m8_05_06_tenant_isolation(db_session):
    inst1 = Institution(code=f"I_{uuid4().hex[:4]}", name="I1")
    inst2 = Institution(code=f"I_{uuid4().hex[:4]}", name="I2")
    db_session.add_all([inst1, inst2])
    await db_session.flush()
    
    s1 = Student(institution_id=inst1.id, roll_number=uuid4().hex[:4], source_type="SYSTEM", source_reference="test")
    s2 = Student(institution_id=inst1.id, roll_number=uuid4().hex[:4], source_type="SYSTEM", source_reference="test")
    s3 = Student(institution_id=inst2.id, roll_number=uuid4().hex[:4], source_type="SYSTEM", source_reference="test")
    db_session.add_all([s1, s2, s3])
    for student in (s1, s2, s3):
        user = User(institution_id=student.institution_id, login=f"{uuid4().hex}@example.invalid",
                    source_type="SYSTEM", source_reference="test")
        db_session.add(user)
        await db_session.flush()
        student.user_id = user.id
    await db_session.commit()
    
    p1 = Principal(sub=s1.user_id, institution_id=inst1.id, role="STUDENT")
    p2 = Principal(sub=s2.user_id, institution_id=inst1.id, role="STUDENT")
    
    ctx1 = ToolContext(principal=p1, request_id="req-1")
    ctx2 = ToolContext(principal=p2, request_id="req-2")
    
    mem1 = ConversationMemory(db=db_session, context=ctx1)
    mem2 = ConversationMemory(db=db_session, context=ctx2)
    
    conv_id = uuid4()
    await mem1.get_or_create_session(conv_id)
    
    # Accessing different student in same tenant
    with pytest.raises(PermissionError):
        await mem2.get_or_create_session(conv_id)
        
    p3 = Principal(sub=s3.user_id, institution_id=inst2.id, role="STUDENT") # Diff tenant
    ctx3 = ToolContext(principal=p3, request_id="req-3")
    mem3 = ConversationMemory(db=db_session, context=ctx3)
    # Accessing cross tenant
    with pytest.raises(PermissionError):
        await mem3.get_or_create_session(conv_id)

async def test_m8_07_memory_current_state(mock_memory):
    await mock_memory.get_or_create_session(uuid4())
    final_resp = create_response(content="You are ELIGIBLE because I remember from history.")
    openai = create_mock_openai([final_resp])
    orchestrator = AgentOrchestrator(memory=mock_memory, openai_client=openai)
    response = await orchestrator.execute(uuid4(), "Am I eligible?")
    assert response.decision == "UNKNOWN"

async def test_m8_08_parallel_tools_budget(mock_memory):
    call1 = create_tool_call("get_student_profile", {})
    call2 = create_tool_call("get_student_academics", {})
    call3 = create_tool_call("get_student_placement_history", {})
    
    resp1 = create_response(tool_calls=[call1, call2, call3])
    resp2 = create_response(tool_calls=[call1, call2, call3])
    resp3 = create_response(content="Done")
    
    openai = create_mock_openai([resp1, resp2, resp3])
    orchestrator = AgentOrchestrator(memory=mock_memory, openai_client=openai)
    
    await orchestrator.execute(uuid4(), "query")

async def test_m8_09_unknown_tool(mock_memory):
    resp1 = create_response(tool_calls=[create_tool_call("hack_database", {})])
    resp2 = create_response(content="I tried.")
    openai = create_mock_openai([resp1, resp2])
    orchestrator = AgentOrchestrator(memory=mock_memory, openai_client=openai)
    conversation_id = uuid4()
    assert "hack_database" not in orchestrator.registry
    res = await orchestrator.execute(conversation_id, "query")
    history = await mock_memory.get_messages(conversation_id)
    rejected = [m for m in history if m.get("role") == "tool"]
    assert len(rejected) == 1
    assert "not found" in rejected[0]["content"]
    assert res.decision == "UNKNOWN"
    assert res.decision_source is None
    assert res.message == "Eligibility has not been verified. No authoritative decision is available."

async def test_m8_10_repeated_cycle(mock_memory):
    call = create_tool_call("get_student_profile", {})
    resp1 = create_response(tool_calls=[call])
    resp2 = create_response(tool_calls=[call])
    resp3 = create_response(content="Ok")
    openai = create_mock_openai([resp1, resp2, resp3])
    orchestrator = AgentOrchestrator(memory=mock_memory, openai_client=openai)
    res = await orchestrator.execute(uuid4(), "query")
    assert res.decision == "UNKNOWN"

def create_access_token(principal: Principal, secret: str, iss: str, aud: str):
    import time
    now = int(time.time())
    claims = {
        "sub": str(principal.sub),
        "institution_id": str(principal.institution_id),
        "role": principal.role,
        "iss": iss,
        "aud": aud,
        "iat": now,
        "exp": now + 3600
    }
    return jwt.encode(claims, secret, algorithm="HS256")

@pytest.fixture
def test_app(db_session):
    settings = Settings(
        database_url=M8_TEST_DATABASE_URL,
        jwt_secret="test-only-" + "x" * 40,
        app_env="test",
        qdrant_url="http://test",
        redis_url="redis://test"
    )
    app = create_app(settings)
    
    @app.middleware("http")
    async def override_db_session_mw(request, call_next):
        class MockDeps:
            session = db_session
        request.state.dependencies = MockDeps()
        return await call_next(request)
        
    return app

async def test_m8_11_api_authorization(test_app, db_session):
    inst1 = Institution(code=f"I_{uuid4().hex[:4]}", name="I1")
    db_session.add(inst1)
    await db_session.flush()
    s1 = Student(institution_id=inst1.id, roll_number=uuid4().hex[:4], source_type="SYSTEM", source_reference="test")
    s2 = Student(institution_id=inst1.id, roll_number=uuid4().hex[:4], source_type="SYSTEM", source_reference="test")
    db_session.add_all([s1, s2])
    for student in (s1, s2):
        user = User(institution_id=student.institution_id, login=f"{uuid4().hex}@example.invalid",
                    source_type="SYSTEM", source_reference="test")
        db_session.add(user)
        await db_session.flush()
        student.user_id = user.id
    await db_session.commit()
    
    mock_openai = create_mock_openai([create_response(content="Mock")])
    
    with patch("app.api.routers.agent.AsyncOpenAI", return_value=mock_openai):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/agent/chat", json={"conversation_id": str(uuid4()), "query": "hi"})
            assert res.status_code == 401
            
            res = await client.post("/api/v1/agent/chat", json={"conversation_id": str(uuid4()), "query": "hi"}, headers={"Authorization": "Bearer invalid"})
            assert res.status_code == 401
            
            settings = Settings(
                database_url=M8_TEST_DATABASE_URL,
                jwt_secret="test-only-" + "x" * 40,
                app_env="test",
                qdrant_url="http://test",
                redis_url="redis://test"
            )
            token1 = create_access_token(Principal(sub=s1.user_id, institution_id=inst1.id, role="STUDENT"), settings.jwt_secret.get_secret_value(), settings.jwt_issuer, settings.jwt_audience)
            
            res = await client.post(
                "/api/v1/agent/chat", 
                json={"conversation_id": str(uuid4()), "query": "hi"}, 
                headers={
                    "Authorization": f"Bearer {token1}",
                    "X-Student-ID": str(uuid4())
                }
            )
            assert res.status_code == 200
            
            conv_id = str(uuid4())
            await client.post("/api/v1/agent/chat", json={"conversation_id": conv_id, "query": "hi"}, headers={"Authorization": f"Bearer {token1}"})
            
            token2 = create_access_token(Principal(sub=s2.user_id, institution_id=inst1.id, role="STUDENT"), settings.jwt_secret.get_secret_value(), settings.jwt_issuer, settings.jwt_audience)
            res = await client.post("/api/v1/agent/chat", json={"conversation_id": conv_id, "query": "hi"}, headers={"Authorization": f"Bearer {token2}"})
            assert res.status_code == 403
